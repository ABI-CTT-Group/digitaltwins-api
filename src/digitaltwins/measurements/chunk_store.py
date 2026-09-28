"""Chunk store for resumable dataset uploads.

Backs ``/datasets/uploads``: an ``upload_session`` row is created first
(``status=receiving``) and the source bytes stream in as parts that land under
``<staging>/upload_<upload_id>/``. At finalize the parts are assembled and
handed to SPARC validation. Ported from the portal backend's
``measurement_chunk_store``; the protocol is unchanged.

Layout under the per-upload root::

    <staging>/upload_<upload_id>/
      .meta.json                      # manifest + per-rel received part indices
      parts/<rel_path>/<000000..>     # one file per received part, zero-padded
      data/<rel_path>                 # assembled output (folder mode)
      source.zip                      # assembled output (zip mode)

Concurrency: part PUTs for one upload run in parallel (the frontend fans out a
handful at a time). Part *bytes* go to distinct files so they never contend;
only the read-modify-write of ``.meta.json`` is serialised, under a
per-upload lock.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Intra-file chunk size clients split on. Surfaced in the session-create
# response so a single source of truth drives both sides. Default 8 MiB;
# operators can override via env without a rebuild.
PART_SIZE = int(os.getenv("UPLOAD_PART_SIZE_BYTES", str(8 * 1024 * 1024)))

# Folder-mode manifest file-count ceiling — guards against a pathological drop
# (e.g. a 500k-file directory) exhausting fds / bloating .meta.json.
MANIFEST_MAX_FILES = int(os.getenv("UPLOAD_MANIFEST_MAX_FILES", "100000"))

_META_NAME = ".meta.json"

# Per-upload locks for serialising .meta.json updates. Guarded by a global
# lock so the dict itself is safe to grow under concurrent first-touch.
_locks_guard = threading.Lock()
_meta_locks: Dict[str, threading.Lock] = {}


def _lock_for(upload_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _meta_locks.get(upload_id)
        if lock is None:
            lock = threading.Lock()
            _meta_locks[upload_id] = lock
        return lock


def _safe_rel(rel_path: str) -> PurePosixPath:
    """Normalise a manifest rel_path and reject traversal / absolute paths.

    Manifest paths are POSIX-style (forward slashes) regardless of host OS.
    """
    p = PurePosixPath(rel_path)
    if p.is_absolute() or any(part in ("..", "") for part in p.parts) or not p.parts:
        raise ValueError(f"Unsafe rel_path: {rel_path!r}")
    return p


class ChunkStoreError(ValueError):
    """Raised for client-correctable chunk-store faults (bad part, size mismatch,
    unknown rel_path). The router maps these to 400."""


class ChunkStore:
    """Filesystem-backed chunk store rooted at ``tmp_root``.

    One instance per process is fine (it is stateless beyond ``tmp_root``).
    """

    def __init__(self, tmp_root: Path):
        self.tmp_root = Path(tmp_root)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    # -- paths --------------------------------------------------------------
    def upload_dir(self, upload_id: str) -> Path:
        return self.tmp_root / f"upload_{upload_id}"

    def _meta_path(self, upload_id: str) -> Path:
        return self.upload_dir(upload_id) / _META_NAME

    def _parts_dir(self, upload_id: str, rel: PurePosixPath) -> Path:
        return self.upload_dir(upload_id) / "parts" / Path(*rel.parts)

    # -- meta read/write (caller holds the lock) ----------------------------
    def _read_meta(self, upload_id: str) -> Dict[str, Any]:
        meta_path = self._meta_path(upload_id)
        if not meta_path.exists():
            raise ChunkStoreError(f"No active upload {upload_id}")
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_meta(self, upload_id: str, meta: Dict[str, Any]) -> None:
        meta_path = self._meta_path(upload_id)
        tmp = meta_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        os.replace(tmp, meta_path)  # atomic swap so a crash can't leave half-meta

    # -- public API ---------------------------------------------------------
    def init(
        self,
        upload_id: str,
        source_kind: str,
        manifest: List[Dict[str, Any]],
    ) -> None:
        """Create the upload root + ``.meta.json`` for a new chunked upload.

        ``manifest`` is a list of ``{rel_path, size, parts}``. For zip mode it
        holds a single ``source.zip`` entry; for folder mode one entry per file.
        Raises ChunkStoreError on bad input (mirrors the 400 surface).
        """
        if source_kind not in ("folder", "zip"):
            raise ChunkStoreError(f"Unknown source_kind: {source_kind!r}")
        if not manifest:
            raise ChunkStoreError("Manifest is empty.")
        if len(manifest) > MANIFEST_MAX_FILES:
            raise ChunkStoreError(
                f"Manifest has {len(manifest)} files; exceeds the "
                f"{MANIFEST_MAX_FILES} limit."
            )

        norm: List[Dict[str, Any]] = []
        for entry in manifest:
            rel = _safe_rel(str(entry["rel_path"]))
            size = int(entry["size"])
            parts = int(entry["parts"])
            if size < 0 or parts < 1:
                raise ChunkStoreError(f"Bad manifest entry for {rel}: size={size} parts={parts}")
            norm.append({"rel_path": str(rel), "size": size, "parts": parts})

        updir = self.upload_dir(upload_id)
        if updir.exists():
            raise ChunkStoreError(f"Upload dir already exists for {upload_id}")
        updir.mkdir(parents=True)

        meta = {
            "source_kind": source_kind,
            "manifest": norm,
            "received": {e["rel_path"]: [] for e in norm},
        }
        with _lock_for(upload_id):
            self._write_meta(upload_id, meta)
        logger.info(
            f"Chunk upload init: upload={upload_id} kind={source_kind} "
            f"files={len(norm)}"
        )

    def source_kind(self, upload_id: str) -> str:
        with _lock_for(upload_id):
            return self._read_meta(upload_id)["source_kind"]

    def write_part(
        self,
        upload_id: str,
        rel_path: str,
        part_no: int,
        of: int,
        data: bytes,
    ) -> int:
        """Persist one part and record it. Returns bytes received for this rel so far.

        Idempotent: re-writing an already-received part (concurrent / retried
        PUT) overwrites the bytes and leaves the received set unchanged. Parts
        may arrive out of order. The byte is written to a ``.tmp`` sibling and
        atomically renamed so a half-written part is never counted.
        """
        rel = _safe_rel(rel_path)
        with _lock_for(upload_id):
            meta = self._read_meta(upload_id)
            entry = next((e for e in meta["manifest"] if e["rel_path"] == str(rel)), None)
            if entry is None:
                raise ChunkStoreError(f"rel_path not in manifest: {rel}")
            if of != entry["parts"]:
                raise ChunkStoreError(
                    f"Part count mismatch for {rel}: client says {of}, manifest says {entry['parts']}"
                )
            if not (0 <= part_no < of):
                raise ChunkStoreError(f"part_no {part_no} out of range [0,{of}) for {rel}")

            parts_dir = self._parts_dir(upload_id, rel)
            parts_dir.mkdir(parents=True, exist_ok=True)
            part_path = parts_dir / f"{part_no:06d}"
            tmp = part_path.with_name(part_path.name + ".tmp")
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, part_path)

            received: List[int] = meta["received"].setdefault(str(rel), [])
            if part_no not in received:
                received.append(part_no)
                received.sort()
            self._write_meta(upload_id, meta)

            return sum(p.stat().st_size for p in parts_dir.iterdir() if p.is_file())

    def status(self, upload_id: str) -> Dict[str, Any]:
        """Manifest + per-rel received parts/bytes + overall completeness.

        Drives resume: the client diffs its localStorage ``sentParts`` against
        ``received`` and re-sends only the gaps.
        """
        with _lock_for(upload_id):
            meta = self._read_meta(upload_id)
            files = []
            complete_all = True
            for e in meta["manifest"]:
                rel = e["rel_path"]
                got = sorted(meta["received"].get(rel, []))
                parts_dir = self._parts_dir(upload_id, _safe_rel(rel))
                bytes_got = (
                    sum(p.stat().st_size for p in parts_dir.iterdir() if p.is_file())
                    if parts_dir.exists()
                    else 0
                )
                done = len(got) == e["parts"]
                complete_all = complete_all and done
                files.append(
                    {
                        "rel_path": rel,
                        "size": e["size"],
                        "parts": e["parts"],
                        "received_parts": got,
                        "bytes": bytes_got,
                        "complete": done,
                    }
                )
            return {
                "source_kind": meta["source_kind"],
                "files": files,
                "complete": complete_all,
            }

    def is_complete(self, upload_id: str) -> bool:
        with _lock_for(upload_id):
            meta = self._read_meta(upload_id)
            for e in meta["manifest"]:
                if len(meta["received"].get(e["rel_path"], [])) != e["parts"]:
                    return False
            return True

    def assemble(self, upload_id: str) -> Path:
        """Concatenate every rel's parts in order, verifying declared sizes.

        Returns the assembled artefact:
          - folder mode → the ``data/`` dir (a SPARC staging tree)
          - zip mode    → the ``source.zip`` file

        Raises ChunkStoreError if any rel is incomplete or its assembled size
        does not match the manifest (corrupt / dropped part).
        """
        with _lock_for(upload_id):
            meta = self._read_meta(upload_id)
            kind = meta["source_kind"]
            updir = self.upload_dir(upload_id)

            if kind == "zip":
                entry = meta["manifest"][0]
                out_path = updir / "source.zip"
                self._concat_rel(upload_id, entry, out_path)
                return out_path

            data_dir = updir / "data"
            for entry in meta["manifest"]:
                rel = _safe_rel(entry["rel_path"])
                out_path = data_dir / Path(*rel.parts)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                self._concat_rel(upload_id, entry, out_path)
            return data_dir

    def _concat_rel(self, upload_id: str, entry: Dict[str, Any], out_path: Path) -> None:
        rel = _safe_rel(entry["rel_path"])
        parts_dir = self._parts_dir(upload_id, rel)
        written = 0
        with open(out_path, "wb") as out:
            for n in range(entry["parts"]):
                part_path = parts_dir / f"{n:06d}"
                if not part_path.exists():
                    raise ChunkStoreError(f"Missing part {n} for {rel}; upload incomplete.")
                with open(part_path, "rb") as p:
                    while True:
                        buf = p.read(1024 * 1024)
                        if not buf:
                            break
                        out.write(buf)
                        written += len(buf)
        if written != entry["size"]:
            raise ChunkStoreError(
                f"Assembled size mismatch for {rel}: got {written}, expected {entry['size']}."
            )

    def cleanup(self, upload_id: str) -> None:
        updir = self.upload_dir(upload_id)
        if updir.exists():
            shutil.rmtree(updir)
        with _locks_guard:
            _meta_locks.pop(upload_id, None)
