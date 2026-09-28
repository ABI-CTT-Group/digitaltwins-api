"""Auto-classifier for SPARC measurement sample folders.

Given a ``sample`` directory under ``primary/<patient>/<sample>/`` the
classifier inspects file extensions and returns a structured hint telling
the prefill stage which FHIR resource family the sample maps to:

  - ImagingStudy ←  all-.dcm  |  single-.nrrd  |  single-.nii  |  single-.nii.gz
  - Observation  ←  all-.txt  (value = first .txt content, 64 KiB cap)
  - DocumentReference ← everything else (mixed extensions / .obj / .pdf / .csv)
  - None ← empty folder (caller filters; surfaced as ``skipped_samples`` in /tree)

Rules deliberately mirror ``fhir_cda.utils.check_first_file_extension``
semantics ("first / homogeneous file determines type") so the classifier
never contradicts what the fhir-cda annotator will later do with the same
files. The ``modality_hint`` field is informational — the frontend uses it
to render the ImagingStudy form's modality chip.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Truncate Observation valueString prefills to avoid bloating the /tree
# response with multi-MB text payloads. PLAN risks table calls this out.
_TXT_SIZE_LIMIT = 64 * 1024

# Marker appended when a .txt sample is too large to inline. The frontend
# strips this prefix for display but keeps it so the round-trip is explicit.
_TRUNCATED_MARKER = "[TRUNCATED: file exceeds 64KB inline limit]"


@dataclass
class ClassifyResult:
    """Structured prefill hint for one sample folder.

    ``kind`` is one of: ``"ImagingStudy"`` / ``"Observation"`` / ``"DocumentReference"``.
    Empty folders return ``None`` instead of a result (see ``classify_sample``).
    """
    kind: str
    files: List[str] = field(default_factory=list)
    # ImagingStudy hint: "dcm" / "nrrd" / "nii" / "nii.gz".
    modality_hint: Optional[str] = None
    # Observation hint: prefilled valueString (possibly truncated).
    value_string: Optional[str] = None
    value_truncated: bool = False


def _is_nii_gz(path: Path) -> bool:
    """Path.suffix returns '.gz' for foo.nii.gz, so we look at the compound."""
    return path.name.lower().endswith(".nii.gz")


def _is_bare_nii(path: Path) -> bool:
    return path.suffix.lower() == ".nii" and not _is_nii_gz(path)


def _read_txt_value(path: Path) -> tuple[str, bool]:
    """Read up to ``_TXT_SIZE_LIMIT`` bytes; flag truncation if file is larger."""
    try:
        size = path.stat().st_size
    except OSError:
        return ("", False)

    if size > _TXT_SIZE_LIMIT:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                head = fh.read(_TXT_SIZE_LIMIT)
            return (f"{_TRUNCATED_MARKER}\n{head}", True)
        except OSError:
            return (_TRUNCATED_MARKER, True)

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return (fh.read(), False)
    except OSError:
        return ("", False)


def classify_sample(sample_dir: Path) -> Optional[ClassifyResult]:
    """Classify a single sample directory.

    Returns ``None`` for an empty folder (no files at all). Subdirectories
    are ignored — SPARC sample folders are flat by convention.
    """
    if not sample_dir.exists() or not sample_dir.is_dir():
        return None

    files = sorted([p for p in sample_dir.iterdir() if p.is_file()])
    if not files:
        return None

    file_names = [p.name for p in files]
    suffixes = [p.suffix.lower() for p in files]

    # ImagingStudy: all .dcm
    if all(s == ".dcm" for s in suffixes):
        return ClassifyResult(kind="ImagingStudy", files=file_names, modality_hint="dcm")

    # ImagingStudy: single .nrrd
    if len(files) == 1 and suffixes[0] == ".nrrd":
        return ClassifyResult(kind="ImagingStudy", files=file_names, modality_hint="nrrd")

    # ImagingStudy: single .nii.gz (must check before bare .nii branch since
    # .nii.gz also has Path.suffix == ".gz", not ".nii"; we match by name).
    if len(files) == 1 and _is_nii_gz(files[0]):
        return ClassifyResult(kind="ImagingStudy", files=file_names, modality_hint="nii.gz")

    # ImagingStudy: single bare .nii
    if len(files) == 1 and _is_bare_nii(files[0]):
        return ClassifyResult(kind="ImagingStudy", files=file_names, modality_hint="nii")

    # Observation: all .txt (use first file's content as valueString prefill)
    if all(s == ".txt" for s in suffixes):
        value_string, truncated = _read_txt_value(files[0])
        return ClassifyResult(
            kind="Observation",
            files=file_names,
            value_string=value_string,
            value_truncated=truncated,
        )

    # Fallback: DocumentReference for everything else (mixed / obj / pdf / csv / ...).
    return ClassifyResult(kind="DocumentReference", files=file_names)
