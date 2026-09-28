"""HTTP client for resumable dataset uploads to digitaltwins-api (``/datasets/uploads``).

    client = UploadClient.login("https://<platform>/digitaltwins-api", "<username>", "<password>")
    session = client.upload_dataset("path/to/dataset", category="measurements", fhir="auto")
    session["dataset_uuid"], session["fhir_status"]

``login`` exchanges the credentials for a Keycloak token once; every request
after that uses ``Authorization: Bearer`` (Basic auth would do a Keycloak
password grant per request). If an upload is interrupted, ``resume`` sends
only the parts the server has not received.
"""
import math
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests


class UploadError(RuntimeError):
    """The server rejected the upload or its commit / FHIR push failed."""


class UploadClient:
    def __init__(self, base_url: str, token: str, session=None, poll_interval: float = 2.0,
                 timeout: Optional[float] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.session = session or requests.Session()
        self.poll_interval = poll_interval
        self.timeout = timeout  # seconds to wait for commit / FHIR; None = no limit
        self.last_upload_id: Optional[str] = None  # set once a session exists; pass to resume()

    @classmethod
    def login(cls, base_url: str, username: str, password: str, session=None, **kwargs) -> "UploadClient":
        session = session or requests.Session()
        r = session.post(f"{base_url.rstrip('/')}/login", auth=(username, password))
        r.raise_for_status()
        return cls(base_url, r.json()["access_token"], session=session, **kwargs)

    # ── Public API ─────────────────────────────────────────────────────

    def upload_dataset(
        self,
        path,
        category: str = "measurements",
        name: Optional[str] = None,
        description: Optional[str] = None,
        fhir: Optional[str] = None,
        fhir_descriptions: Optional[Dict[str, Any]] = None,
        wait_for_fhir: bool = True,
    ) -> Dict[str, Any]:
        """Upload a dataset folder or ``.zip`` and wait until it is committed.

        ``fhir="auto"`` auto-annotates and pushes FHIR; ``fhir_descriptions``
        supplies the annotation (keyed by folder name; UUIDs are assigned by the
        server). Returns the final session, plus ``fhir_status`` when FHIR was
        requested and ``wait_for_fhir`` is set.
        """
        path = Path(path)
        part_size = self._request("get", "/datasets/uploads/config")["max_part_size"]
        files = list(self._files(path))
        body = {
            "name": name or (path.stem if path.is_file() else path.name),
            "description": description,
            "category": category,
            "source_kind": "zip" if path.is_file() else "folder",
            "manifest": [
                {"rel_path": rel, "size": local.stat().st_size, "parts": max(1, math.ceil(local.stat().st_size / part_size))}
                for rel, local in files
            ],
            "fhir": fhir or "none",
        }
        if fhir_descriptions is not None:
            body["fhir_descriptions"] = fhir_descriptions
        created = self._request("post", "/datasets/uploads", json=body)
        self.last_upload_id = created["upload_id"]
        return self._send_and_finish(created["upload_id"], path, created["max_part_size"],
                                     fhir_requested=bool(fhir or fhir_descriptions), wait_for_fhir=wait_for_fhir)

    def resume(self, upload_id: str, path, wait_for_fhir: bool = True) -> Dict[str, Any]:
        """Continue an interrupted upload of ``path``: send missing parts, finalize, wait."""
        session = self._request("get", f"/datasets/uploads/{upload_id}")
        if session["status"] != "receiving":
            return self._wait(upload_id, session["fhir_mode"] != "none", wait_for_fhir)
        part_size = self._request("get", "/datasets/uploads/config")["max_part_size"]
        return self._send_and_finish(upload_id, Path(path), part_size,
                                     fhir_requested=session["fhir_mode"] != "none", wait_for_fhir=wait_for_fhir)

    # ── Internals ──────────────────────────────────────────────────────

    def _request(self, method: str, path: str, expect=(200, 202), **kwargs) -> Dict[str, Any]:
        headers = {**self.headers, **kwargs.pop("headers", {})}
        r = getattr(self.session, method)(f"{self.base_url}{path}", headers=headers, **kwargs)
        if r.status_code not in expect:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise UploadError(f"{method.upper()} {path} -> {r.status_code}: {detail}")
        return r.json()

    @staticmethod
    def _files(path: Path) -> Iterator[Tuple[str, Path]]:
        """``(rel_path, local_path)`` pairs, rel paths prefixed with the folder name."""
        if path.is_file():
            yield "source.zip", path
            return
        for local in sorted(p for p in path.rglob("*") if p.is_file()):
            yield f"{path.name}/{local.relative_to(path).as_posix()}", local

    def _send_and_finish(self, upload_id: str, path: Path, part_size: int,
                         fhir_requested: bool, wait_for_fhir: bool) -> Dict[str, Any]:
        status = self._request("get", f"/datasets/uploads/{upload_id}")["upload"]
        received: Dict[str, List[int]] = {f["rel_path"]: f["received_parts"] for f in status["files"]}
        parts_of = {f["rel_path"]: f["parts"] for f in status["files"]}
        for rel, local in self._files(path):
            missing = [n for n in range(parts_of[rel]) if n not in set(received.get(rel, []))]
            if not missing:
                continue
            with open(local, "rb") as fh:
                for n in missing:
                    fh.seek(n * part_size)
                    self._request(
                        "put", f"/datasets/uploads/{upload_id}/parts/{rel}",
                        params={"n": n, "of": parts_of[rel]}, data=fh.read(part_size),
                        headers={"Content-Type": "application/octet-stream"},
                    )
        self._request("post", f"/datasets/uploads/{upload_id}/finalize")
        return self._wait(upload_id, fhir_requested, wait_for_fhir)

    def _poll(self, fetch, done):
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        while True:
            value = fetch()
            if done(value):
                return value
            if deadline is not None and time.monotonic() > deadline:
                raise UploadError("Timed out waiting for the server")
            time.sleep(self.poll_interval)

    def _wait(self, upload_id: str, fhir_requested: bool, wait_for_fhir: bool) -> Dict[str, Any]:
        session = self._poll(
            lambda: self._request("get", f"/datasets/uploads/{upload_id}"),
            lambda s: s["status"] in ("completed", "failed", "staged"),
        )
        if session["status"] == "failed":
            raise UploadError(f"Commit failed: {session['failure_message']}")
        if session["status"] == "completed" and fhir_requested and wait_for_fhir:
            dataset = self._poll(
                lambda: self._request("get", f"/datasets/{session['dataset_uuid']}")["dataset"],
                lambda d: d["fhir_status"] in ("completed", "failed"),
            )
            session["fhir_status"] = dataset["fhir_status"]
            if dataset["fhir_status"] == "failed":
                raise UploadError(f"FHIR push failed: {dataset['fhir_failure_message']}")
        return session
