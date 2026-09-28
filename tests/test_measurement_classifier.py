"""Tests for ``digitaltwins.measurements.classifier.classify_sample``.

Covers the six rules from the PLAN classification table plus the truncation
behaviour for oversize .txt files.

Run from the digitaltwins-api root:
    python -m pytest tests/test_measurement_classifier.py -q
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


from digitaltwins.measurements.classifier import (
    _TRUNCATED_MARKER,
    _TXT_SIZE_LIMIT,
    classify_sample,
)


class ClassifySampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make(self, files: list[str]) -> Path:
        sam = self.root / "sam"
        sam.mkdir()
        for name in files:
            (sam / name).write_bytes(b"0")
        return sam

    def test_all_dcm_is_imaging_study(self) -> None:
        sam = self._make(["1-01.dcm", "1-02.dcm", "1-03.dcm"])
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "ImagingStudy")
        self.assertEqual(result.modality_hint, "dcm")
        self.assertEqual(len(result.files), 3)

    def test_single_nrrd_is_imaging_study(self) -> None:
        sam = self._make(["scan.nrrd"])
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "ImagingStudy")
        self.assertEqual(result.modality_hint, "nrrd")

    def test_single_nii_is_imaging_study(self) -> None:
        sam = self._make(["scan.nii"])
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "ImagingStudy")
        self.assertEqual(result.modality_hint, "nii")

    def test_single_nii_gz_is_imaging_study(self) -> None:
        sam = self._make(["scan.nii.gz"])
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "ImagingStudy")
        self.assertEqual(result.modality_hint, "nii.gz")

    def test_all_txt_is_observation_with_value(self) -> None:
        # classify_sample uses sorted order; "a-value.txt" sorts before
        # "b-extra.txt" so the prefilled valueString is the first one.
        sam = self.root / "sam"
        sam.mkdir()
        (sam / "a-value.txt").write_text("28.5")
        (sam / "b-extra.txt").write_text("ignored")
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "Observation")
        self.assertEqual(result.value_string, "28.5")
        self.assertFalse(result.value_truncated)

    def test_single_txt_observation(self) -> None:
        sam = self._make([])
        # _make leaves empty dir if list empty; recreate with single file
        (sam / "value.txt").write_text("42")
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "Observation")
        self.assertEqual(result.value_string, "42")

    def test_oversize_txt_is_truncated_observation(self) -> None:
        sam = self.root / "sam"
        sam.mkdir()
        big = "x" * (_TXT_SIZE_LIMIT + 10)
        (sam / "value.txt").write_text(big)
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "Observation")
        self.assertTrue(result.value_truncated)
        assert result.value_string is not None
        self.assertIn(_TRUNCATED_MARKER, result.value_string)

    def test_mixed_extensions_falls_back_to_document_reference(self) -> None:
        sam = self._make(["surface.obj", "summary.pdf", "data.csv"])
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "DocumentReference")
        self.assertEqual(len(result.files), 3)

    def test_pure_obj_is_document_reference(self) -> None:
        sam = self._make(["a.obj", "b.obj"])
        result = classify_sample(sam)
        assert result is not None
        self.assertEqual(result.kind, "DocumentReference")

    def test_empty_folder_returns_none(self) -> None:
        sam = self.root / "sam"
        sam.mkdir()
        self.assertIsNone(classify_sample(sam))

    def test_missing_folder_returns_none(self) -> None:
        self.assertIsNone(classify_sample(self.root / "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
