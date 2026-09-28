"""Auto-annotation tree for a SPARC measurements dataset on disk.

Ported from the portal backend's ``GET /api/measurement/{id}/tree``. Walks
``primary/<subject>/<sample>/``, classifies each sample and returns prefilled
fhir-cda descriptions (camelCase) for the annotation UI or inline ``fhir=auto``.

UUID fields are left empty: the server stamps them from ``dataset_mapping`` at
commit (see ``pipeline.stamp_uuids``). Every resource carries a top-level
``samplePath`` (``"<subject>/<sample>"``), which is the key used for stamping.
"""
import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List

from .classifier import _TRUNCATED_MARKER, ClassifyResult, classify_sample
from .fhir_adapter import NiiCompatibleImagingStudy
from .validation import sampleless_subjects

logger = logging.getLogger(__name__)


def _observation(classify: ClassifyResult, sample_path: str) -> Dict[str, Any]:
    """Prefilled Observation. Best-effort numeric detection so a simple
    measurement (e.g. ``28.5`` in ``height.txt``) lands as Quantity."""
    raw = classify.value_string or ""
    # Strip the truncation banner before attempting the numeric check so that
    # an oversize file with leading numeric content still gets categorised.
    detect_target = raw
    if raw.startswith(_TRUNCATED_MARKER):
        detect_target = raw[len(_TRUNCATED_MARKER):].strip()
    detect_target = detect_target.strip()

    value_type = "String"
    value: Any = raw
    try:
        as_num = float(detect_target.splitlines()[0]) if detect_target else None
        if as_num is not None:
            value_type = "Quantity"
            value = as_num
    except (ValueError, IndexError):
        pass

    return {
        "resourceType": "Observation",
        "uuid": "",
        "samplePath": sample_path,
        "value": value,
        "valueType": value_type,
        "code": "",
        "codeSystem": "http://loinc.org",
        "unit": "",
        "display": "",
        "_auto": {
            "samplePath": sample_path,
            "sourceFile": classify.files[0] if classify.files else "",
            "truncated": classify.value_truncated,
        },
    }


def _imaging_study(classify: ClassifyResult, sample_path: str, sample_dir: Path) -> Dict[str, Any]:
    """Prefilled ImagingStudy. fhir-cda's pydicom reader pulls the real
    ``SeriesInstanceUID`` and ``BodyPartExamined`` out of the first DICOM;
    NRRD / NII samples fall through to the default shape."""
    series_payload: Dict[str, Any] = {
        "uid": None,
        "endpointUrl": "",
        "endpointUuid": "",
        "name": sample_dir.name,
        "numberOfInstances": len(classify.files),
        "bodySite": None,
        "instances": [],
    }

    try:
        study = NiiCompatibleImagingStudy(
            uuid="",
            sample_details=[{"uuid": "", "path": sample_dir}],
            endpoint_url="",
            description=classify.modality_hint or "",
        )
        if study.series:
            real = study.series[0].get()
            series_payload["uid"] = real.get("uid") or None
            n = real.get("numberOfInstances")
            if isinstance(n, int) and n > 0:
                series_payload["numberOfInstances"] = n
            body_site = real.get("bodySite")
            if isinstance(body_site, dict) and body_site:
                series_payload["bodySite"] = body_site
    except Exception as e:
        # _read_sam already swallows pydicom errors; this catches the
        # constructor raising on e.g. mixed extensions.
        logger.warning(f"Could not extract ImagingStudy metadata from {sample_dir}: {e}")

    return {
        "resourceType": "ImagingStudy",
        "uuid": "",
        "samplePath": sample_path,
        "endpointUrl": "",
        "description": classify.modality_hint or "",
        "display": "",
        "series": [series_payload],
        "_auto": {
            "samplePath": sample_path,
            "modality": classify.modality_hint or "",
        },
    }


def _document_reference(classify: ClassifyResult, sample_path: str, sample_dir: Path) -> Dict[str, Any]:
    """Prefilled DocumentReference: one attachment per file, with a mime guess."""
    attachments: List[Dict[str, Any]] = []
    for fname in classify.files:
        fpath = sample_dir / fname
        attachments.append(
            {
                "url": "",
                "contentType": mimetypes.guess_type(fname)[0] or "application/octet-stream",
                "title": fname,
                "size": fpath.stat().st_size if fpath.exists() else 0,
            }
        )
    return {
        "resourceType": "DocumentReference",
        "uuid": "",
        "samplePath": sample_path,
        "description": "",
        "display": "",
        "attachments": attachments,
        "_auto": {
            "samplePath": sample_path,
            "files": list(classify.files),
        },
    }


def build_tree(dataset_root: Path, dataset_name: str) -> Dict[str, Any]:
    """Return ``{tree, descriptions, skipped_samples, warnings}`` for a dataset.

    - ``tree``: subject/sample/file view for the header card
    - ``descriptions``: prefilled fhir-cda descriptions, UUIDs empty
    - ``skipped_samples``: empty / un-classifiable sample paths
    - ``warnings``: subject folders with no sample folders (cannot be
      registered, so they get no FHIR Patient)
    """
    primary = Path(dataset_root) / "primary"
    descriptions: Dict[str, Any] = {"dataset": {"uuid": "", "name": dataset_name}, "patients": []}
    tree: Dict[str, Any] = {"name": dataset_name, "type": "dataset", "children": []}
    skipped_samples: List[str] = []

    for patient_dir in sorted(p for p in primary.iterdir() if p.is_dir()):
        patient_name = patient_dir.name
        sample_dirs = sorted(s for s in patient_dir.iterdir() if s.is_dir())
        if not sample_dirs:
            continue  # reported by sampleless_subjects()

        patient_entry: Dict[str, Any] = {
            "uuid": "",
            "name": patient_name,
            "observations": [],
            "imagingStudy": [],
            "documentReference": [],
        }
        patient_node: Dict[str, Any] = {"name": patient_name, "type": "patient", "children": []}

        for sample_dir in sample_dirs:
            sample_path = f"{patient_name}/{sample_dir.name}"
            classify = classify_sample(sample_dir)
            patient_node["children"].append(
                {
                    "name": sample_dir.name,
                    "type": "sample",
                    "fileCount": sum(1 for f in sample_dir.iterdir() if f.is_file()),
                    "kind": classify.kind if classify else None,
                }
            )

            if classify is None:
                skipped_samples.append(sample_path)
            elif classify.kind == "Observation":
                patient_entry["observations"].append(_observation(classify, sample_path))
            elif classify.kind == "ImagingStudy":
                patient_entry["imagingStudy"].append(_imaging_study(classify, sample_path, sample_dir))
            else:
                patient_entry["documentReference"].append(
                    _document_reference(classify, sample_path, sample_dir)
                )

        descriptions["patients"].append(patient_entry)
        tree["children"].append(patient_node)

    return {
        "tree": tree,
        "descriptions": descriptions,
        "skipped_samples": skipped_samples,
        "warnings": sampleless_subjects(dataset_root),
    }
