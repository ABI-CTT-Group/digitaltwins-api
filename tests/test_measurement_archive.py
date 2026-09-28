"""Archive extraction safety + dataset-root resolution (digitaltwins.measurements.validation)."""
import zipfile

import pytest

from digitaltwins.measurements.validation import extract_uploaded_archive, resolve_project_root


def _zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_extracts_into_a_fresh_staging_dir(tmp_path):
    archive = _zip(tmp_path / "a.zip", {"ds/primary/sub-1/sam-1/x.txt": "1"})

    staging = extract_uploaded_archive(tmp_path, archive)

    assert staging.parent == tmp_path
    assert (staging / "ds/primary/sub-1/sam-1/x.txt").read_text() == "1"


def test_rejects_entries_escaping_the_target(tmp_path):
    archive = _zip(tmp_path / "evil.zip", {"../outside.txt": "x"})

    with pytest.raises(ValueError, match="escapes"):
        extract_uploaded_archive(tmp_path / "stage", archive)
    assert not (tmp_path / "outside.txt").exists()


def test_rejects_archives_over_the_size_limit(tmp_path):
    archive = _zip(tmp_path / "big.zip", {"a.bin": b"0" * 2048})

    with pytest.raises(ValueError, match="too large"):
        extract_uploaded_archive(tmp_path, archive, max_total_bytes=1024)


def test_keeps_dataset_folders_named_like_build_output(tmp_path):
    # Plugin archives filter build/, dist/ ... but those are legitimate dataset folder names.
    archive = _zip(tmp_path / "a.zip", {"primary/sub-1/build/x.dcm": "d", "__MACOSX/._x": "junk"})

    staging = extract_uploaded_archive(tmp_path, archive)

    assert (staging / "primary/sub-1/build/x.dcm").exists()
    assert not (staging / "__MACOSX").exists()


def test_resolve_project_root_strips_single_wrapper_dirs(tmp_path):
    root = tmp_path / "outer" / "inner"
    (root / "primary").mkdir(parents=True)
    (root / "dataset_description.xlsx").write_bytes(b"")
    (tmp_path / "__MACOSX").mkdir()

    assert resolve_project_root(tmp_path) == root
