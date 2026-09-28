"""Auto-annotation tree + fhir.json build on the real SPARC DICOM fixture.

Exercises the ported classifier, tree builder, fhir-cda adapter and
apply_descriptions end to end, without any network service.
"""
import shutil
from pathlib import Path

import pytest

from digitaltwins.measurements.fhir_service import build_fhir_json
from digitaltwins.measurements.tree import build_tree

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"


@pytest.fixture
def dataset(tmp_path):
    ds = tmp_path / "example"
    shutil.copytree(FIXTURE, ds)
    return ds


def test_tree_classifies_every_dicom_sample_as_imaging_study(dataset):
    result = build_tree(dataset, "example")

    assert result["skipped_samples"] == []
    assert result["warnings"] == []
    patients = result["descriptions"]["patients"]
    assert [p["name"] for p in patients] == ["sub-1", "sub-2"]
    for p in patients:
        studies = p["imagingStudy"]
        assert [s["samplePath"] for s in studies] == [f"{p['name']}/sam-1", f"{p['name']}/sam-2"]
        # DICOM headers were probed for the real SeriesInstanceUID.
        assert all(s["series"][0]["uid"] for s in studies)
        assert all(s["series"][0]["numberOfInstances"] == 4 for s in studies)


def test_tree_uuids_are_left_for_the_server_to_stamp(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]

    assert descriptions["dataset"] == {"uuid": "", "name": "example"}
    for p in descriptions["patients"]:
        assert p["uuid"] == ""
        for s in p["imagingStudy"]:
            assert s["uuid"] == "" and s["series"][0]["endpointUuid"] == ""


def test_tree_warns_about_subjects_without_sample_folders(dataset):
    (dataset / "primary" / "sub-3").mkdir()

    result = build_tree(dataset, "example")

    assert result["warnings"] == ["primary/sub-3 has no sample folders; it cannot be registered"]
    assert [p["name"] for p in result["descriptions"]["patients"]] == ["sub-1", "sub-2"]


def test_build_fhir_json_applies_stamped_descriptions(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]
    descriptions["dataset"]["uuid"] = "d-uuid"
    for p in descriptions["patients"]:
        p["uuid"] = f"{p['name']}-uuid"
        for s in p["imagingStudy"]:
            s["uuid"] = f"{s['samplePath']}-uuid"
            s["series"][0]["endpointUuid"] = f"{s['samplePath']}-endpoint"

    fhir = build_fhir_json(dataset, descriptions)

    assert fhir["dataset"]["uuid"] == "d-uuid"
    assert [(p["name"], p["uuid"]) for p in fhir["patients"]] == [("sub-1", "sub-1-uuid"), ("sub-2", "sub-2-uuid")]
    study = fhir["patients"][0]["imagingStudy"][0]
    assert study["uuid"] == "sub-1/sam-1-uuid"
    assert study["series"][0]["endpointUuid"] == "sub-1/sam-1-endpoint"
    assert study["series"][0]["uid"]
    assert not (dataset / "fhir.json").exists()  # never written into the dataset
