"""Safe archive extraction and SPARC structure validation for dataset uploads.

Ported from the portal backend's ``builder_utils``. Unlike the plugin-archive
extractor it came from, no ``build/``, ``dist/``, ... filtering is applied:
those are legitimate dataset folder names. Only macOS ``__MACOSX/`` metadata
is skipped.
"""
import shutil
import uuid
import zipfile
from pathlib import Path

_SKIPPED_TOP_LEVEL = "__MACOSX"


def extract_uploaded_archive(
    tmp_dir: Path,
    archive_path: Path,
    max_total_bytes: int = 5 * 1024 * 1024 * 1024,
) -> Path:
    """Extract a user-uploaded zip into a fresh staging directory under tmp_dir.

    Safety:
    - zip-slip: every resolved entry path must remain inside the target
    - zip-bomb: sum of declared uncompressed sizes must not exceed max_total_bytes

    Returns the staging directory Path.
    """
    target = Path(tmp_dir) / f"upload_{uuid.uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=False)
    target_resolved = target.resolve()

    with zipfile.ZipFile(archive_path) as zf:
        infos = zf.infolist()
        total = sum(info.file_size for info in infos if not info.is_dir())
        if total > max_total_bytes:
            shutil.rmtree(target, ignore_errors=True)
            raise ValueError(
                f"Archive too large after extraction ({total} bytes > {max_total_bytes} bytes limit)"
            )

        for info in infos:
            name = info.filename
            if not name or name.endswith("/"):
                continue
            if name.split("/")[0] == _SKIPPED_TOP_LEVEL:
                continue

            dest = (target / name).resolve()
            try:
                dest.relative_to(target_resolved)
            except ValueError:
                shutil.rmtree(target, ignore_errors=True)
                raise ValueError(f"Unsafe archive entry escapes target: {name}")

            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)

    return target


def resolve_project_root(staging_dir: Path) -> Path:
    """Walk down through single-wrapper directories until we hit the real dataset root.

    A "wrapper" is a directory whose only contents are exactly one subdirectory
    and no files (``__MACOSX`` ignored), e.g. ``MyDataset/...`` inside a zip.
    Bounded to 20 iterations to defend against pathological structures.
    """
    current = Path(staging_dir)
    for _ in range(20):
        children = [c for c in current.iterdir() if c.name != _SKIPPED_TOP_LEVEL]
        dirs = [c for c in children if c.is_dir()]
        files = [c for c in children if c.is_file()]
        if len(dirs) == 1 and not files:
            current = dirs[0]
        else:
            break
    return current


def sampleless_subjects(dataset_root: Path) -> list[str]:
    """Warnings for ``primary/<subject>`` folders with no sample folders.

    Such subjects cannot be registered (``dataset_mapping`` is keyed by sample),
    so they get no UUID and no FHIR Patient.
    """
    primary = Path(dataset_root) / "primary"
    return [
        f"primary/{subject.name} has no sample folders; it cannot be registered"
        for subject in sorted(p for p in primary.iterdir() if p.is_dir())
        if not any(s.is_dir() for s in subject.iterdir())
    ]


def validate_sparc_structure(staging: Path) -> tuple[bool, str]:
    """Strict structural check for a SPARC measurements dataset.

    A valid SPARC dataset (post-resolve_project_root) MUST contain:
      - ``dataset_description.xlsx`` OR ``dataset_description.json`` at root
      - a ``primary/`` subdirectory
      - at least one patient subdirectory under ``primary/``

    ``subjects.xlsx`` / ``samples.xlsx`` are optional: missing subject/sample
    rows are derived from the ``primary/`` folders at commit time.

    Returns (ok, message). On failure, message is a human-readable string
    suitable for surfacing in a 400 response. On success, message is empty.
    """
    if not staging.exists() or not staging.is_dir():
        return (False, f"Staging directory not found: {staging}")

    root = resolve_project_root(staging)

    has_xlsx = (root / "dataset_description.xlsx").exists()
    has_json = (root / "dataset_description.json").exists()
    if not (has_xlsx or has_json):
        return (
            False,
            "Missing dataset_description.xlsx (or .json) at the dataset root. "
            "Expected a SPARC measurements dataset structure.",
        )

    primary = root / "primary"
    if not primary.exists() or not primary.is_dir():
        return (
            False,
            "Missing primary/ subdirectory at the dataset root. "
            "SPARC measurements datasets must have primary/<patient>/<sample>/ folders.",
        )

    patient_dirs = [p for p in primary.iterdir() if p.is_dir()]
    if not patient_dirs:
        return (
            False,
            "primary/ contains no patient subdirectories. "
            "Expected at least one sub-XXX folder.",
        )

    return (True, "")
