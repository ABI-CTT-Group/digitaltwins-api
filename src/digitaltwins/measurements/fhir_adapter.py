"""Subclasses that bridge two gaps in the upstream ``fhir_cda`` library
for the measurements upload flow.

Both subclasses are deliberately tiny — we want every difference vs upstream
in one place so a future patch / library upgrade is a 5-minute diff. The
intent is to file these upstream eventually; until then they live here.

Filename override
-----------------
``MeasurementAnnotator`` hard-codes its category to ``"measurements"``, and
the abstract base writes ``<root>/<category>.json`` on save. The portal
standardises on ``fhir.json`` so workflows / processes / measurements all
emit the same filename. ``MeasurementsFhirAnnotator`` flips that one
attribute.

Bare ``.nii`` support
---------------------
``ImagingStudyMeasurement._read_sam`` only globs ``*.nii.gz``; a sample
folder containing a bare ``test.nii`` is silently dropped. The portal's
classifier treats both as ImagingStudy, so the annotator must too.
``NiiCompatibleImagingStudy`` extends the glob and falls through to the
upstream implementation for DCM/NRRD/NII.GZ cases unchanged.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fhir_cda.annotator.measurement_annotator import MeasurementAnnotator
from fhir_cda.ehr import ImagingStudyMeasurement, ObservationMeasurement
from fhir_cda.ehr.elements import ImagingStudySeries

logger = logging.getLogger(__name__)


class SafeObservationMeasurement(ObservationMeasurement):
    """Null-safe ``get()`` for value-less Observations.

    Upstream ``ObservationMeasurement.set()`` explicitly allows ``value=None``
    (an Observation the user left blank), but ``ObservationMeasurement.get()``
    calls ``self.value.get()`` unconditionally → ``AttributeError: 'NoneType'
    object has no attribute 'get'``. Since ``save()`` /
    ``_convert_elements_to_descriptions`` invokes ``get()`` on every stored
    measurement, a single blank Observation crashes the whole fhir.json build
    (both the submit pipeline and the dry-run preview).

    Upstream's ``get()`` already drops None values via its trailing dict
    comprehension, so the only change needed is to not dereference a None
    value in the first place.
    """

    def get(self):
        measurement = {
            "resourceType": "Observation",
            "uuid": self.uuid,
            "value": self.value.get() if self.value is not None else None,
            "code": self.code,
            "codeSystem": self.code_system,
            "unit": self.unit,
            "display": self.display if isinstance(self.display, str) else "",
        }
        return {k: v for k, v in measurement.items() if v is not None}


class MeasurementsFhirAnnotator(MeasurementAnnotator):
    """Override upstream's hardcoded ``measurements.json`` to write ``fhir.json``.

    In default mode this is trivial: set ``_category = "fhir"`` after the
    base class has used the "measurements" category for its own analysis,
    so ``save()`` ends up at ``fhir.json``.

    The submit pipeline (``app.services.measurement_service``) only ever
    instantiates this in default mode. We did originally support update mode
    too (via a rename dance), but:
      1. upstream fhir-cda 1.2.5 has a bug in
         ``DocumentReferenceMeasurement().set(item)`` — the no-arg
         constructor rejects ``attachments=None``, so update-mode load
         crashes whenever the prior measurements.json had any
         DocumentReference entries.
      2. Our descriptions tree always lives in the DB; we never need to
         re-hydrate it from disk, so update mode added no value either way.
    The ``mode`` parameter is therefore accepted but ignored — kept for
    upstream API parity in case external callers pass it.
    """

    def __init__(self, dataset_path, mode: str = "default"):
        # We accept ``mode`` for API parity but always run the upstream
        # default branch — see class docstring for why.
        super().__init__(dataset_path, "default")
        # Flip the category so save() writes fhir.json from this point on.
        self._category = "fhir"


class NiiCompatibleImagingStudy(ImagingStudyMeasurement):
    """Extend upstream's ``_read_sam`` to recognise bare ``*.nii`` files.

    Upstream globs ``*.nii.gz`` only, so a sample folder containing
    ``something.nii`` is treated as empty and the series is dropped. The
    portal's classifier accepts both extensions as ImagingStudy candidates,
    so this subclass keeps them consistent.

    Behaviour:
      - Pure DCM / NRRD / NII.GZ sample → delegate to super() unchanged.
      - Pure bare .nii sample → build an ImagingStudySeries with the same
        shape upstream uses for NRRD (uid=None, no instances, count = number of nii).
      - Mixed (e.g. dcm + nii) → raise ValueError, same posture as upstream.
    """

    def _read_sam(self, sam):
        try:
            sample_path: Path = sam["path"]
            dcm_files = list(sample_path.glob("*.dcm"))
            nrrd_files = list(sample_path.glob("*.nrrd"))
            niigz_files = list(sample_path.glob("*.nii.gz"))
            # Exclude *.nii.gz from the bare-nii bucket — Path.glob("*.nii")
            # already matches .nii but not .nii.gz, so this is belt + braces.
            nii_files = [
                p for p in sample_path.glob("*.nii") if not p.name.endswith(".nii.gz")
            ]

            buckets = [
                bucket
                for bucket in (dcm_files, nrrd_files, niigz_files, nii_files)
                if bucket
            ]
            if not buckets:
                return None
            if len(buckets) > 1:
                raise ValueError(
                    "dataset format error: mixed imaging types in sample folder "
                    f"{sample_path.name} (found combinations of dcm/nrrd/nii/nii.gz)."
                )

            # Anything upstream already handles? Delegate.
            if dcm_files or nrrd_files or niigz_files:
                return super()._read_sam(sam)

            # Pure bare-.nii branch — same shape as upstream's nrrd/nii.gz output.
            return ImagingStudySeries(
                uid=None,
                endpoint_url="",
                endpoint_uuid=sam["uuid"],
                name=sample_path.name,
                number_of_instances=len(nii_files),
                instances=[],
            )
        except Exception as e:
            # Mirror upstream's swallow-and-log posture so the calling
            # _generate_imaging_study loop can move on to other samples.
            logger.warning(f"Error reading {sam}: {e}")
            return None
