"""Removing a measurement dataset's FHIR resources (delete and re-push cleanup).

digitaltwins-on-fhir tags only the Compositions with the dataset UUID; Patients
carry the subject UUID and the other resources derived identifiers, so cleanup
walks references from those roots rather than searching one identifier.
"""
import asyncio

from conftest import FakeHapi
from digitaltwins.measurements.fhir_service import HapiRest, delete_dataset_fhir_resources

GRAPH = {"Composition": 2, "Consent": 2, "Endpoint": 8, "ImagingStudy": 4,
         "Observation": 1, "Patient": 2, "ResearchSubject": 2}


def _push(hapi, dataset, subjects=("s1", "s2")):
    hapi.add_measurements_description({"dataset": {"uuid": dataset}, "patients": [
        {"uuid": s, "imagingStudy": [{"uuid": f"{s}-img1"}, {"uuid": f"{s}-img2"}],
         "observations": [{"uuid": f"{s}-obs"}] if s == subjects[0] else []}
        for s in subjects]})
    asyncio.run(hapi.generate_resources())


def test_removes_the_whole_graph_of_one_dataset_only():
    hapi = FakeHapi()
    _push(hapi, "d1", ("s1", "s2"))
    _push(hapi, "d2", ("t1", "t2"))
    assert hapi.types() == {k: 2 * v for k, v in GRAPH.items()}

    removed = delete_dataset_fhir_resources("d1", ["s1", "s2"], hapi)

    assert removed == GRAPH
    assert hapi.types() == GRAPH  # d2 untouched


def test_finds_the_graph_from_patients_when_the_composition_is_gone():
    hapi = FakeHapi()
    _push(hapi, "d1")
    for ref in [r for r in hapi.store if r.startswith("Composition/")]:
        hapi.delete(ref)

    removed = delete_dataset_fhir_resources("d1", ["s1", "s2"], hapi)

    assert removed == {k: v for k, v in GRAPH.items() if k != "Composition"}
    assert hapi.store == {}


def test_never_follows_references_to_shared_resource_types():
    hapi = FakeHapi()
    _push(hapi, "d1")
    hapi.store["Practitioner/99"] = {"resourceType": "Practitioner", "id": "99", "identifier": [{"value": "doc"}]}
    for ref, r in hapi.store.items():
        if ref.startswith("Patient/"):
            r["generalPractitioner"] = [{"reference": "Practitioner/99"}]

    delete_dataset_fhir_resources("d1", ["s1", "s2"], hapi)

    assert list(hapi.store) == ["Practitioner/99"]


def test_nothing_to_remove_is_a_noop():
    assert delete_dataset_fhir_resources("d1", ["s1"], FakeHapi()) == {}


class _Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _Session:
    def __init__(self, pages):
        self.pages, self.requests = list(pages), []

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append((url, params, headers))
        return _Response(self.pages.pop(0))


def test_rest_search_bypasses_the_search_cache_and_follows_pages():
    session = _Session([
        {"entry": [{"resource": {"id": "1"}}], "link": [{"relation": "next", "url": "http://h/fhir?page=2"}]},
        {"entry": [{"resource": {"id": "2"}}], "link": []},
    ])

    found = HapiRest("http://h/fhir/", session=session).search("Patient", identifier="s1")

    assert [r["id"] for r in found] == ["1", "2"]
    assert session.requests[0][:2] == ("http://h/fhir/Patient", {"identifier": "s1", "_count": 200})
    assert all(h["Cache-Control"] == "no-cache" for _, _, h in session.requests)
