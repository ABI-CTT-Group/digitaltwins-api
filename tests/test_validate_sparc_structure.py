"""Tests for ``digitaltwins.measurements.validation.validate_sparc_structure``."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


from digitaltwins.measurements.validation import validate_sparc_structure


class ValidateSparcStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_valid_xlsx(self) -> Path:
        (self.root / "dataset_description.xlsx").write_bytes(b"")
        primary = self.root / "primary"
        primary.mkdir()
        (primary / "sub-001").mkdir()
        return self.root

    def test_valid_dataset_with_xlsx(self) -> None:
        self._make_valid_xlsx()
        ok, msg = validate_sparc_structure(self.root)
        self.assertTrue(ok, msg)
        self.assertEqual(msg, "")

    def test_valid_dataset_with_json(self) -> None:
        (self.root / "dataset_description.json").write_text("{}")
        (self.root / "primary").mkdir()
        (self.root / "primary" / "sub-001").mkdir()
        ok, msg = validate_sparc_structure(self.root)
        self.assertTrue(ok, msg)

    def test_missing_dataset_description_fails(self) -> None:
        (self.root / "primary").mkdir()
        (self.root / "primary" / "sub-001").mkdir()
        ok, msg = validate_sparc_structure(self.root)
        self.assertFalse(ok)
        self.assertIn("dataset_description", msg)

    def test_missing_primary_fails(self) -> None:
        (self.root / "dataset_description.xlsx").write_bytes(b"")
        ok, msg = validate_sparc_structure(self.root)
        self.assertFalse(ok)
        self.assertIn("primary/", msg)

    def test_empty_primary_fails(self) -> None:
        (self.root / "dataset_description.xlsx").write_bytes(b"")
        (self.root / "primary").mkdir()
        ok, msg = validate_sparc_structure(self.root)
        self.assertFalse(ok)
        self.assertIn("patient", msg.lower())

    def test_nested_wrapper_directory_is_unwrapped(self) -> None:
        # Outer wrapper (single subdir) is stripped by resolve_project_root.
        outer = self.root / "wrap"
        outer.mkdir()
        (outer / "dataset_description.xlsx").write_bytes(b"")
        primary = outer / "primary"
        primary.mkdir()
        (primary / "sub-001").mkdir()
        ok, msg = validate_sparc_structure(self.root)
        self.assertTrue(ok, msg)


if __name__ == "__main__":
    unittest.main()
