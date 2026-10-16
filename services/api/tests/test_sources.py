"""Source registry and the license gate for adapted content (Content Master Plan §2, App. A)."""

import pytest
from catalog_support import basics
from test_learner_api import client  # noqa: F401

from socrat.catalog import sources
from socrat.catalog.registry import CatalogError, build
from socrat.catalog.schema import Course

TIH = dict(
    source_id="tech-interview-handbook",
    title="Algorithms study cheatsheet",
    author="Yangshun Tay",
    url="https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/",
    license_spdx="MIT",
    license_url="https://github.com/yangshun/tech-interview-handbook/blob/main/LICENSE",
    retrieved_at="2026-10-16",
    content_sha256="0" * 64,
)


def adapted(**overrides) -> dict:
    return {"origin": "adapted", "authors_adapted_from": [{**TIH, **overrides}]}


def course_with(provenance: dict) -> Course:
    payload = basics().model_dump(mode="json")
    payload["concepts"][0]["provenance"] = provenance
    return Course.model_validate(payload)


def test_repository_registry_loads_and_unverified_licenses_stay_unverified():
    registry = sources.load_registry()
    assert registry.get("tech-interview-handbook").license_status == "verified"
    for unverified in ("thealgorithms", "erickson-algorithms", "kactl", "python-for-everybody"):
        assert registry.get(unverified).license_status == "unverified"


def test_non_commercial_and_no_derivative_sources_are_link_only():
    registry = sources.load_registry()
    for entry in registry.sources:
        if entry.license_class in {"non-commercial", "no-derivatives", "all-rights-reserved"}:
            assert entry.action == "link-only", entry.id


def test_gate_accepts_adaptation_from_a_verified_permissive_source():
    registry = sources.load_registry()
    sources.check_catalog(build([course_with(adapted())]), registry)


def test_gate_rejects_adaptation_from_an_unverified_source():
    registry = sources.load_registry()
    record = adapted(source_id="thealgorithms", license_spdx="MIT")
    with pytest.raises(CatalogError, match="thealgorithms.*unverified"):
        sources.check_catalog(build([course_with(record)]), registry)


def test_gate_rejects_adaptation_from_a_link_only_source():
    registry = sources.load_registry()
    record = adapted(source_id="usaco-guide", license_spdx="CC-BY-NC-SA-4.0")
    with pytest.raises(CatalogError, match="usaco-guide.*link-only"):
        sources.check_catalog(build([course_with(record)]), registry)


def test_gate_rejects_unknown_sources_and_mismatched_licenses():
    registry = sources.load_registry()
    with pytest.raises(CatalogError, match="unknown source"):
        sources.check_catalog(build([course_with(adapted(source_id="made-up"))]), registry)
    with pytest.raises(CatalogError, match="license CC0-1.0 does not match"):
        sources.check_catalog(build([course_with(adapted(license_spdx="CC0-1.0"))]), registry)


def test_registry_rejects_an_adaptable_non_commercial_entry():
    entry = dict(
        id="nc-book",
        name="Some NC book",
        url="https://example.org/",
        content="Book",
        license="CC-BY-NC-4.0",
        license_class="non-commercial",
        license_status="verified",
        action="adapt",
    )
    with pytest.raises(ValueError, match="must be link-only"):
        sources.SourceRegistry.model_validate({"version": 1, "sources": [entry]})


def test_registry_rejects_duplicate_ids():
    entry = dict(
        id="dup",
        name="Dup",
        url="https://example.org/",
        content="x",
        license="MIT",
        license_class="permissive",
        license_status="unverified",
        action="verify",
    )
    with pytest.raises(ValueError, match="duplicate source id"):
        sources.SourceRegistry.model_validate({"version": 1, "sources": [entry, entry]})


def write_tree(root, course: Course) -> None:
    """A minimal on-disk content tree (courses/, atoms/, sources/) for load()."""
    import shutil

    import yaml

    data = course.model_dump(mode="json", exclude_none=True)
    folder = root / "courses" / course.id
    (folder / "concepts").mkdir(parents=True)
    (folder / "problems").mkdir()
    for item in data.pop("concepts"):
        (folder / "concepts" / f"{item['id']}.yaml").write_text(yaml.safe_dump(item), "utf-8")
    for item in data.pop("problems"):
        item.pop("tests", None)
        (folder / "problems" / f"{item['id']}.yaml").write_text(yaml.safe_dump(item), "utf-8")
    (folder / "course.yaml").write_text(yaml.safe_dump(data), "utf-8")
    (root / "atoms").mkdir()
    (root / "sources").mkdir()
    shutil.copy(sources.REGISTRY_PATH, root / "sources" / "registry.yaml")


def test_loading_content_runs_the_license_gate(tmp_path):
    from socrat.catalog.registry import load

    write_tree(tmp_path, course_with(adapted()))
    assert load(tmp_path / "courses", tests_root=None).concepts

    blocked = tmp_path / "blocked"
    write_tree(blocked, course_with(adapted(source_id="thealgorithms")))
    with pytest.raises(CatalogError, match="license gate: .*thealgorithms is unverified"):
        load(blocked / "courses", tests_root=None)


def test_attribution_endpoint_is_public_and_built_from_the_registry(client):  # noqa: F811
    response = client.get("/api/v1/attribution")
    assert response.status_code == 200
    body = response.json()
    by_id = {s["id"]: s for s in body["sources"]}
    assert by_id["usaco-guide"]["use"] == "Linked only; not copied or adapted"
    assert by_id["tech-interview-handbook"]["license_status"] == "verified"
    assert by_id["kactl"]["use"] == "Not used until its license is verified"
    # No shipped content is adapted yet, so nothing is listed as adapted.
    assert body["adapted"] == []
