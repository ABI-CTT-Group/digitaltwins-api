"""Build fhir.json for a measurements dataset and push it to HAPI FHIR.

Ported from the portal backend's ``measurement_service``. ``descriptions`` are
fhir-cda's camelCase shape (``resourceType``, ``codeSystem``, ``imagingStudy``,
...); the API never case-converts them, so no camelize step is needed here.
"""
import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from fhir_cda.ehr import DocumentReferenceMeasurement
from fhir_cda.ehr.elements import DocumentAttachment, ObservationValue, Quantity

from .fhir_adapter import MeasurementsFhirAnnotator, NiiCompatibleImagingStudy, SafeObservationMeasurement

logger = logging.getLogger(__name__)


def _build_observation_value(desc: Dict[str, Any]) -> Optional[ObservationValue]:
    """Map the flat ``value`` + ``valueType`` into fhir-cda's nested
    ObservationValue shape. Returns None if no value is set."""
    value_type = desc.get("valueType") or ""
    value = desc.get("value")
    if value in (None, ""):
        return None

    if value_type == "Quantity":
        try:
            numeric = float(value) if not isinstance(value, (int, float)) else value
        except (TypeError, ValueError):
            # Soft-degrade: treat unparseable numerics as String values so the
            # build doesn't blow up on a single bad row.
            return ObservationValue(value_string=str(value))
        unit = desc.get("unit") or None
        return ObservationValue(
            value_quantity=Quantity(value=numeric, unit=unit if isinstance(unit, str) else None)
        )

    return ObservationValue(value_string=str(value))


def _build_observation_measurement(desc: Dict[str, Any]) -> SafeObservationMeasurement:
    return SafeObservationMeasurement(
        value=_build_observation_value(desc),
        code=desc.get("code") or "",
        code_system=desc.get("codeSystem") or "http://loinc.org",
        unit=desc.get("unit") or None,
        display=desc.get("display") or None,
        uuid=desc.get("uuid") or "",
    )


def _build_imaging_study_measurement(
    desc: Dict[str, Any], dataset_path: Path, patient_name: str
) -> Optional[NiiCompatibleImagingStudy]:
    """Construct a NiiCompatibleImagingStudy from a description entry.

    The samples MUST exist on disk under ``<dataset>/primary/<patient>/<series.name>/``;
    the constructor walks them to populate series metadata. Returns None when
    no series resolves on disk.
    """
    sample_details: List[Dict[str, Any]] = []
    for s in desc.get("series") or []:
        sample_path = dataset_path / "primary" / patient_name / (s.get("name") or "")
        if not sample_path.is_dir():
            logger.warning(f"ImagingStudy sample path missing on disk: {sample_path}; skipping series.")
            continue
        sample_details.append({"uuid": s.get("endpointUuid") or "", "path": sample_path})

    if not sample_details:
        return None

    study = NiiCompatibleImagingStudy(
        uuid=desc.get("uuid") or "",
        sample_details=sample_details,
        endpoint_url=desc.get("endpointUrl") or "",
        description=desc.get("description") or "",
    )
    # fhir-cda always builds series with endpoint_url="", dropping the
    # per-series URLs from the descriptions; restore them by sample name.
    series_urls = {s.get("name"): s.get("endpointUrl") for s in desc.get("series") or []}
    for series in study.series:
        if series_urls.get(series.name):
            series.endpoint_url = series_urls[series.name]
    return study


def _build_document_reference_measurement(desc: Dict[str, Any]) -> DocumentReferenceMeasurement:
    attachments = [
        DocumentAttachment(
            title=a.get("title") or "",
            url=a.get("url") or "",
            content_type=a.get("contentType") or "",
        )
        for a in desc.get("attachments") or []
    ]
    return DocumentReferenceMeasurement(
        attachments=attachments,
        uuid=desc.get("uuid") or "",
        description=desc.get("description") or None,
    )


def apply_descriptions(
    annotator: MeasurementsFhirAnnotator,
    descriptions: Dict[str, Any],
    dataset_path: Path,
) -> None:
    """Replay a descriptions tree onto a fresh annotator (mutates it in place)."""
    dataset = descriptions.get("dataset") or {}
    if dataset.get("uuid"):
        annotator.update_dataset("uuid", dataset["uuid"])
    if dataset.get("name"):
        annotator.update_dataset("name", dataset["name"])

    for patient in descriptions.get("patients") or []:
        patient_name = patient.get("name") or ""
        if not patient_name:
            continue
        try:
            if patient.get("uuid"):
                annotator.update_patient(patient_name, "uuid", patient["uuid"])
        except ValueError as e:
            # The patient isn't a folder under primary/; skip the stray entry.
            logger.warning(f"Skipping unknown patient {patient_name}: {e}")
            continue

        for ob_desc in patient.get("observations") or []:
            try:
                annotator.add_measurements([patient_name], [_build_observation_measurement(ob_desc)])
            except ValueError as e:
                logger.warning(f"Skipping observation for {patient_name}: {e}")

        for img_desc in patient.get("imagingStudy") or []:
            img = _build_imaging_study_measurement(img_desc, dataset_path, patient_name)
            if img is None:
                continue
            try:
                annotator.add_measurements([patient_name], [img])
            except ValueError as e:
                logger.warning(f"Skipping imaging study for {patient_name}: {e}")

        for doc_desc in patient.get("documentReference") or []:
            try:
                annotator.add_measurements([patient_name], [_build_document_reference_measurement(doc_desc)])
            except ValueError as e:
                logger.warning(f"Skipping document reference for {patient_name}: {e}")


def build_fhir_json(dataset_path: Path, descriptions: Dict[str, Any]) -> Dict[str, Any]:
    """Build the fhir.json content for ``descriptions``.

    Nothing is written into the dataset: a staged dataset is uploaded to MinIO
    as-is at commit, so a stray fhir.json there would be published with it.
    """
    dataset_path = Path(dataset_path)
    annotator = MeasurementsFhirAnnotator(dataset_path)
    apply_descriptions(annotator, descriptions, dataset_path)
    with tempfile.TemporaryDirectory() as out:
        annotator.save(out)
        with open(Path(out) / "fhir.json", "r", encoding="utf-8") as f:
            return json.load(f)


# ---------------------------------------------------------------------------
# Endpoint URLs + HAPI FHIR push / delete
# ---------------------------------------------------------------------------

_adapter = None


def _fhir_base_url() -> str:
    """``FHIR_ENDPOINT`` as a URL. Container-to-container hop: hapi-fhir serves
    plain HTTP, so a bare ``host:port/fhir`` gets ``http://``; an explicit
    scheme is honoured."""
    endpoint = os.getenv("FHIR_ENDPOINT", "localhost:8080/fhir").strip()
    return endpoint if endpoint.startswith(("http://", "https://")) else f"http://{endpoint}"


def get_fhir_adapter():
    """Process-wide digitaltwins-on-fhir Adapter (used to push)."""
    global _adapter
    if _adapter is None:
        from digitaltwins_on_fhir.core import Adapter

        _adapter = Adapter(_fhir_base_url())
    return _adapter


class HapiRest:
    """Minimal synchronous FHIR REST client for cleanup.

    Searches send ``Cache-Control: no-cache``: HAPI otherwise reuses a cached
    result of the same search (60 s by default), e.g. the empty one from the
    pre-push cleanup, and a delete right after a push would find nothing.
    """

    _HEADERS = {"Cache-Control": "no-cache", "Accept": "application/fhir+json"}

    def __init__(self, base_url: str, session=None, timeout: float = 30):
        self.base = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def search(self, resource_type: str, **params) -> List[Dict[str, Any]]:
        url, query, found = f"{self.base}/{resource_type}", {**params, "_count": 200}, []
        while url:
            r = self.session.get(url, params=query, headers=self._HEADERS, timeout=self.timeout)
            r.raise_for_status()
            bundle = r.json()
            found += [e["resource"] for e in bundle.get("entry", [])]
            url = next((l["url"] for l in bundle.get("link", []) if l.get("relation") == "next"), None)
            query = None  # the next link carries the paging state
        return found

    def read(self, reference: str) -> Optional[Dict[str, Any]]:
        r = self.session.get(f"{self.base}/{reference}", headers=self._HEADERS, timeout=self.timeout)
        if r.status_code in (404, 410):
            return None
        r.raise_for_status()
        return r.json()

    def delete(self, reference: str) -> None:
        r = self.session.delete(f"{self.base}/{reference}", timeout=self.timeout)
        if r.status_code not in (404, 410):
            r.raise_for_status()


def get_fhir_rest() -> HapiRest:
    return HapiRest(_fhir_base_url())


# Resource types digitaltwins-on-fhir creates for a measurements dataset, in a
# safe delete order: every type only references types after it (Composition →
# ResearchSubject → Consent → Patient; ImagingStudy → Endpoint), so HAPI's
# referential-integrity check never blocks a delete.
_DATASET_TYPES = ("Composition", "ResearchSubject", "Consent", "Observation",
                  "DocumentReference", "ImagingStudy", "Endpoint", "Patient")
# Resources that point at a Patient, found by reverse search when the graph is
# only partly there (e.g. its Composition was already deleted).
_PATIENT_REFERRERS = (("ResearchSubject", "individual"), ("Consent", "patient"), ("ImagingStudy", "subject"),
                      ("Observation", "subject"), ("DocumentReference", "subject"))


def _references(obj) -> Iterable[str]:
    if isinstance(obj, dict):
        if isinstance(obj.get("reference"), str):
            yield "/".join(obj["reference"].split("/")[:2])  # drop any /_history/n
        for value in obj.values():
            yield from _references(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _references(value)


def delete_dataset_fhir_resources(dataset_uuid: str, subject_uuids: Iterable[str], fhir) -> Dict[str, int]:
    """Delete every FHIR resource of a measurements dataset; return per-type counts.

    digitaltwins-on-fhir tags only the Compositions with the dataset UUID;
    Patients carry the subject UUID and the rest derived identifiers. So the
    graph is collected from those roots by following references (restricted to
    the dataset types, so shared resources such as Practitioners are never
    touched) and deleted referrers first.
    """
    found: Dict[str, Dict[str, Any]] = {}
    queue: List[str] = []

    def add(resources):
        for resource in resources:
            ref = f"{resource['resourceType']}/{resource['id']}"
            if ref not in found:
                found[ref] = resource
                queue.append(ref)

    add(fhir.search("Composition", identifier=dataset_uuid))
    for subject_uuid in subject_uuids:
        add(fhir.search("Patient", identifier=subject_uuid))
    while queue:
        ref = queue.pop()
        if ref.startswith("Patient/"):
            for resource_type, param in _PATIENT_REFERRERS:
                add(fhir.search(resource_type, **{param: ref}))
        for target in _references(found[ref]):
            if target.split("/")[0] in _DATASET_TYPES and target not in found:
                resource = fhir.read(target)
                if resource:
                    add([resource])

    removed: Dict[str, int] = {}
    for resource_type in _DATASET_TYPES:
        for ref in [r for r in found if r.startswith(resource_type + "/")]:
            fhir.delete(ref)
            removed[resource_type] = removed.get(resource_type, 0) + 1
    return removed


def compute_endpoint_urls(descriptions: Dict[str, Any], dataset_uuid: str, public_base: str) -> Dict[str, Any]:
    """Return a copy of ``descriptions`` whose endpoint / attachment URLs point at
    ``GET <public_base>/datasets/<uuid>/files/primary/...`` (Bearer token required)."""
    out = copy.deepcopy(descriptions)
    base = f"{public_base.rstrip('/')}/datasets/{dataset_uuid}/files/primary"
    for patient in out.get("patients") or []:
        patient_name = patient.get("name") or ""
        for img in patient.get("imagingStudy") or []:
            # Study-level endpoint is the patient folder; series-level the sample folder.
            img["endpointUrl"] = f"{base}/{patient_name}"
            for series in img.get("series") or []:
                series["endpointUrl"] = f"{base}/{patient_name}/{series.get('name') or ''}"
        for doc in patient.get("documentReference") or []:
            sample_path = doc.get("samplePath") or (doc.get("_auto") or {}).get("samplePath") or patient_name
            for attach in doc.get("attachments") or []:
                if attach.get("title"):
                    attach["url"] = f"{base}/{sample_path}/{attach['title']}"
    return out


async def push_to_hapi_fhir(fhir_json: Dict[str, Any], adapter) -> None:
    client = adapter.digital_twin().measurements()
    client.add_measurements_description(fhir_json)
    await client.generate_resources()
