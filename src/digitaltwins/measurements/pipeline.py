"""Commit a validated measurements dataset and stamp platform UUIDs into its annotation.

UUID fields in FHIR descriptions are server-owned. Entries are matched by
patient ``name`` (the ``primary/<subject>`` folder) and resource ``samplePath``
(``"<subject>/<sample>"``), then stamped from ``dataset_mapping``:

  dataset.uuid          ← dataset_uuid
  patient.uuid          ← subject_uuid
  resource.uuid         ← sample_uuid
  series.endpointUuid   ← uuid5(sample_uuid, "endpoint")

A resource without a ``samplePath`` (added by hand, not from a sample folder)
is subject-level: ``uuid5(subject_uuid, "<key>:<n>")``, n counting that
patient's subject-level resources of the same key in order.
"""
import copy
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from psycopg2.extras import Json

from ..core.connection import Connection
from ..core.downloader import Downloader
from ..core.uploader import Uploader
from ..minio.uploader import Uploader as MinioUploader
from .staging import dataset_dir, staging_root

_RESOURCE_KEYS = ("observations", "imagingStudy", "documentReference")

# (subject_id, sample_id) -> (subject_uuid, sample_uuid)
Mapping = Dict[Tuple[str, str], Tuple[str, str]]


@dataclass
class CommitResult:
    dataset_uuid: str
    descriptions: Optional[Dict[str, Any]]  # stamped, or None when none were given


def _resources(patient: Dict[str, Any]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    for key in _RESOURCE_KEYS:
        for resource in patient.get(key) or []:
            yield key, resource


def _sample_path(resource: Dict[str, Any]) -> str:
    return resource.get("samplePath") or (resource.get("_auto") or {}).get("samplePath") or ""


def check_descriptions_match(descriptions: Dict[str, Any], dataset_root: Path) -> None:
    """Raise ValueError unless every patient / samplePath / series names a folder under primary/."""
    primary = Path(dataset_root) / "primary"
    for patient in descriptions.get("patients") or []:
        name = patient.get("name") or ""
        subject_dir = primary / name
        if not name or not subject_dir.is_dir() or not any(p.is_dir() for p in subject_dir.iterdir()):
            raise ValueError(f"Patient {name!r} does not match a primary/<subject> folder with samples")
        for key, resource in _resources(patient):
            sample_path = _sample_path(resource)
            if not sample_path and key != "imagingStudy":
                continue  # subject-level resource; ImagingStudy always reads a sample folder
            if sample_path.split("/")[0] != name or not (primary / sample_path).is_dir():
                raise ValueError(
                    f"{key} samplePath {sample_path!r} under patient {name!r} has no primary/ folder"
                )
            for series in resource.get("series") or []:
                if not (subject_dir / (series.get("name") or "")).is_dir():
                    raise ValueError(f"Series {series.get('name')!r} under patient {name!r} has no folder")


def fetch_mapping(conn, dataset_uuid: str) -> Mapping:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT subject_id, sample_id, subject_uuid, sample_uuid FROM dataset_mapping "
            "WHERE dataset_uuid = %s",
            (dataset_uuid,),
        )
        return {(sub, sam): (str(subj_uuid), str(samp_uuid)) for sub, sam, subj_uuid, samp_uuid in cur.fetchall()}


def stamp_uuids(descriptions: Dict[str, Any], dataset_uuid: str, mapping: Mapping) -> Dict[str, Any]:
    """Return a copy of ``descriptions`` with every UUID field set from the platform."""
    subjects = {sub: subject_uuid for (sub, _), (subject_uuid, _) in mapping.items()}
    out = copy.deepcopy(descriptions)
    out.setdefault("dataset", {})["uuid"] = dataset_uuid

    for patient in out.get("patients") or []:
        name = patient.get("name") or ""
        if name not in subjects:
            raise ValueError(f"Patient {name!r} is not a registered subject of dataset {dataset_uuid}")
        patient["uuid"] = subjects[name]

        subject_level = {key: 0 for key in _RESOURCE_KEYS}
        for key, resource in _resources(patient):
            sample_path = _sample_path(resource)
            if not sample_path and key != "imagingStudy":
                resource["uuid"] = str(uuid.uuid5(uuid.UUID(subjects[name]), f"{key}:{subject_level[key]}"))
                subject_level[key] += 1
                continue
            pair = tuple(sample_path.split("/", 1))
            if pair not in mapping or pair[0] != name:
                raise ValueError(f"{key} samplePath {sample_path!r} is not a registered sample")
            resource["uuid"] = mapping[pair][1]
            for series in resource.get("series") or []:
                series_pair = (name, series.get("name") or "")
                if series_pair not in mapping:
                    raise ValueError(f"Series {series_pair[1]!r} under {name!r} is not a registered sample")
                series["endpointUuid"] = str(uuid.uuid5(uuid.UUID(mapping[series_pair][1]), "endpoint"))
    return out


def save_annotation(conn, dataset_uuid: str, descriptions: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dataset_fhir_annotation (dataset_uuid, descriptions) VALUES (%s, %s) "
            "ON CONFLICT (dataset_uuid) DO UPDATE "
            "SET descriptions = EXCLUDED.descriptions, updated_at = now()",
            (dataset_uuid, Json(descriptions)),
        )
    conn.commit()


def commit_dataset(
    dataset_root: Path,
    category: str,
    descriptions: Optional[Dict[str, Any]] = None,
    dataset_name: Optional[str] = None,
) -> CommitResult:
    """Register the dataset in Postgres + MinIO (one unit), then store its stamped annotation.

    ``descriptions`` must already have passed :func:`check_descriptions_match`
    against ``dataset_root``; every folder pair is then registered, so stamping
    cannot miss.
    """
    dataset_uuid = Uploader().upload_dataset(
        str(dataset_root), category=category, derive_from_primary=True, dataset_name=dataset_name
    )
    if descriptions is None:
        return CommitResult(dataset_uuid, None)

    conn, _ = Connection().connect()
    try:
        stamped = stamp_uuids(descriptions, dataset_uuid, fetch_mapping(conn, dataset_uuid))
        save_annotation(conn, dataset_uuid, stamped)
    finally:
        conn.close()
    return CommitResult(dataset_uuid, stamped)


def load_annotation(conn, dataset_uuid: str) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute("SELECT descriptions FROM dataset_fhir_annotation WHERE dataset_uuid = %s", (dataset_uuid,))
        row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def get_dataset_row(conn, dataset_uuid: str) -> Optional[Dict[str, Any]]:
    """``{dataset_name, category, fhir_status}`` or None (also for a malformed UUID)."""
    try:
        uuid.UUID(str(dataset_uuid))
    except ValueError:
        return None
    with conn.cursor() as cur:
        cur.execute(
            "SELECT dataset_name, category, fhir_status FROM dataset WHERE dataset_uuid = %s", (dataset_uuid,)
        )
        row = cur.fetchone()
    conn.commit()
    return dict(zip(("dataset_name", "category", "fhir_status"), row)) if row else None


def local_dataset(conn, dataset_uuid: str) -> Path:
    """The dataset's files on local disk: the upload's staged copy if still cached,
    else a fresh download from MinIO under ``<staging>/downloads/<uuid>/``."""
    with conn.cursor() as cur:
        cur.execute("SELECT upload_id FROM upload_session WHERE dataset_uuid = %s", (dataset_uuid,))
        row = cur.fetchone()
    conn.commit()
    if row and dataset_dir(row[0]).is_dir():
        return dataset_dir(row[0])
    downloads = staging_root() / "downloads"
    root = downloads / str(dataset_uuid)
    if not root.is_dir():
        Downloader().download_dataset(str(dataset_uuid), save_dir=str(downloads))
    return root


def store_fhir_json(category: str, dataset_uuid: str, fhir_json: Dict[str, Any]) -> None:
    """Write the pushed bundle to ``<category>/<dataset_uuid>/fhir.json`` (overwriting)."""
    MinioUploader().s3_client.put_object(
        Bucket=category,
        Key=f"{dataset_uuid}/fhir.json",
        Body=json.dumps(fhir_json, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
