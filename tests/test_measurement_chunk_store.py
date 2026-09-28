"""Unit tests for ``digitaltwins.measurements.chunk_store.ChunkStore``.

Covers the edge cases that make chunked upload tricky: out-of-order arrival,
duplicate/concurrent parts, unknown rel_path, size mismatch at assemble,
path-traversal rejection, the manifest file-count cap, and both folder/zip
assembly paths.
"""
from __future__ import annotations

import math
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path


from digitaltwins.measurements.chunk_store import (
    ChunkStoreError,
    ChunkStore,
)


def _split(data: bytes, part_size: int) -> list[bytes]:
    return [data[i : i + part_size] for i in range(0, len(data), part_size)] or [b""]


def _manifest_entry(rel: str, data: bytes, part_size: int) -> dict:
    return {"rel_path": rel, "size": len(data), "parts": max(1, math.ceil(len(data) / part_size))}


class ChunkStoreTests(unittest.TestCase):
    PART = 4  # tiny part size so a few bytes exercise multi-part logic

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ChunkStore(Path(self._tmp.name))
        self.mid = "m-test"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- init validation ----------------------------------------------------
    def test_init_rejects_unknown_source_kind(self):
        with self.assertRaises(ChunkStoreError):
            self.store.init(self.mid, "tarball", [{"rel_path": "a", "size": 1, "parts": 1}])

    def test_init_rejects_empty_manifest(self):
        with self.assertRaises(ChunkStoreError):
            self.store.init(self.mid, "folder", [])

    def test_init_rejects_manifest_over_cap(self):
        from digitaltwins.measurements import chunk_store as mod

        original = mod.MANIFEST_MAX_FILES
        mod.MANIFEST_MAX_FILES = 2
        try:
            big = [{"rel_path": f"f{i}", "size": 1, "parts": 1} for i in range(3)]
            with self.assertRaises(ChunkStoreError):
                self.store.init(self.mid, "folder", big)
        finally:
            mod.MANIFEST_MAX_FILES = original

    def test_init_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            self.store.init(self.mid, "folder", [{"rel_path": "../escape", "size": 1, "parts": 1}])

    # -- write_part ---------------------------------------------------------
    def test_out_of_order_parts_assemble_correctly(self):
        data = b"abcdefghij"  # 10 bytes -> 3 parts at PART=4
        parts = _split(data, self.PART)
        self.store.init(self.mid, "folder", [_manifest_entry("root/a.bin", data, self.PART)])
        # Feed parts 2, 0, 1 (out of order)
        for n in (2, 0, 1):
            self.store.write_part(self.mid, "root/a.bin", n, len(parts), parts[n])
        self.assertTrue(self.store.is_complete(self.mid))
        data_dir = self.store.assemble(self.mid)
        self.assertEqual((data_dir / "root" / "a.bin").read_bytes(), data)

    def test_duplicate_part_is_idempotent(self):
        data = b"abcdefgh"  # 2 parts
        parts = _split(data, self.PART)
        self.store.init(self.mid, "folder", [_manifest_entry("a.bin", data, self.PART)])
        self.store.write_part(self.mid, "a.bin", 0, 2, parts[0])
        self.store.write_part(self.mid, "a.bin", 0, 2, parts[0])  # duplicate
        status = self.store.status(self.mid)
        self.assertEqual(status["files"][0]["received_parts"], [0])
        self.assertFalse(self.store.is_complete(self.mid))

    def test_concurrent_parts_all_recorded(self):
        data = bytes(range(256)) * 8  # 2048 bytes -> many parts at PART=4
        parts = _split(data, self.PART)
        self.store.init(self.mid, "folder", [_manifest_entry("a.bin", data, self.PART)])

        def put(n: int):
            self.store.write_part(self.mid, "a.bin", n, len(parts), parts[n])

        threads = [threading.Thread(target=put, args=(n,)) for n in range(len(parts))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(self.store.is_complete(self.mid))
        data_dir = self.store.assemble(self.mid)
        self.assertEqual((data_dir / "a.bin").read_bytes(), data)

    def test_unknown_rel_path_rejected(self):
        self.store.init(self.mid, "folder", [{"rel_path": "a.bin", "size": 4, "parts": 1}])
        with self.assertRaises(ChunkStoreError):
            self.store.write_part(self.mid, "ghost.bin", 0, 1, b"data")

    def test_part_count_mismatch_rejected(self):
        self.store.init(self.mid, "folder", [{"rel_path": "a.bin", "size": 4, "parts": 1}])
        with self.assertRaises(ChunkStoreError):
            self.store.write_part(self.mid, "a.bin", 0, 5, b"data")  # of != manifest parts

    def test_part_no_out_of_range_rejected(self):
        self.store.init(self.mid, "folder", [{"rel_path": "a.bin", "size": 8, "parts": 2}])
        with self.assertRaises(ChunkStoreError):
            self.store.write_part(self.mid, "a.bin", 2, 2, b"data")  # part_no >= of

    # -- assemble -----------------------------------------------------------
    def test_size_mismatch_detected_at_assemble(self):
        # Manifest declares 8 bytes but we only ever send 4.
        self.store.init(self.mid, "folder", [{"rel_path": "a.bin", "size": 8, "parts": 1}])
        self.store.write_part(self.mid, "a.bin", 0, 1, b"abcd")  # 4 bytes, not 8
        with self.assertRaises(ChunkStoreError):
            self.store.assemble(self.mid)

    def test_assemble_missing_part_raises(self):
        data = b"abcdefgh"
        parts = _split(data, self.PART)
        self.store.init(self.mid, "folder", [_manifest_entry("a.bin", data, self.PART)])
        self.store.write_part(self.mid, "a.bin", 0, 2, parts[0])  # part 1 never sent
        with self.assertRaises(ChunkStoreError):
            self.store.assemble(self.mid)

    def test_folder_assemble_multi_file(self):
        f1, f2 = b"hello world", b"second file body"
        manifest = [
            _manifest_entry("ds/primary/a.txt", f1, self.PART),
            _manifest_entry("ds/primary/b.txt", f2, self.PART),
        ]
        self.store.init(self.mid, "folder", manifest)
        for rel, blob in (("ds/primary/a.txt", f1), ("ds/primary/b.txt", f2)):
            parts = _split(blob, self.PART)
            for n, p in enumerate(parts):
                self.store.write_part(self.mid, rel, n, len(parts), p)
        data_dir = self.store.assemble(self.mid)
        self.assertEqual((data_dir / "ds" / "primary" / "a.txt").read_bytes(), f1)
        self.assertEqual((data_dir / "ds" / "primary" / "b.txt").read_bytes(), f2)

    def test_zip_assemble_returns_valid_zip(self):
        # Build a real zip in memory, chunk it, reassemble, confirm it opens.
        buf = Path(self._tmp.name) / "z_src_test.zip"
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("inner/file.txt", "payload")
        raw = buf.read_bytes()
        buf.unlink()
        self.store.init(self.mid, "zip", [_manifest_entry("source.zip", raw, self.PART)])
        parts = _split(raw, self.PART)
        for n, p in enumerate(parts):
            self.store.write_part(self.mid, "source.zip", n, len(parts), p)
        zip_path = self.store.assemble(self.mid)
        self.assertEqual(zip_path.name, "source.zip")
        with zipfile.ZipFile(zip_path) as zf:
            self.assertEqual(zf.read("inner/file.txt"), b"payload")

    # -- status / resume ----------------------------------------------------
    def test_status_reports_partial_progress(self):
        data = b"abcdefghijkl"  # 3 parts at PART=4
        parts = _split(data, self.PART)
        self.store.init(self.mid, "folder", [_manifest_entry("a.bin", data, self.PART)])
        self.store.write_part(self.mid, "a.bin", 0, 3, parts[0])
        status = self.store.status(self.mid)
        f = status["files"][0]
        self.assertEqual(f["received_parts"], [0])
        self.assertEqual(f["bytes"], len(parts[0]))
        self.assertFalse(f["complete"])
        self.assertFalse(status["complete"])

    # -- cleanup ------------------------------------------------------------
    def test_cleanup_removes_upload_dir(self):
        self.store.init(self.mid, "folder", [{"rel_path": "a.bin", "size": 4, "parts": 1}])
        self.assertTrue(self.store.upload_dir(self.mid).exists())
        self.store.cleanup(self.mid)
        self.assertFalse(self.store.upload_dir(self.mid).exists())

    def test_operations_on_missing_upload_raise(self):
        with self.assertRaises(ChunkStoreError):
            self.store.status("nonexistent")


if __name__ == "__main__":
    unittest.main()
