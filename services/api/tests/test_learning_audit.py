"""Synthetic inventory rehearsals do not certify content or runtime quality."""

import json
import sys

import pytest
from m7_support import lesson_pack
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform
from test_skill_packs import action, administrators, headers

from socrat.learning.audit import planning_audit
from socrat.learning.content import coverage_audit
from socrat.models import SkillPackHead, SkillPackVersion
from socrat.skillpacks import cli
from socrat.skillpacks.schema import SkillPack


def stocked_pack():
    payload = lesson_pack().model_dump()
    # Enough independent families for twelve scheduled days plus repair reservations.
    originals = [
        x for x in payload["exercises"] if x["id"] in {"a_runtime_probe", "b_second_topic"}
    ]
    for item in originals:
        for index in range(24):
            key = f"{item['id']}_bank_{index:02}"
            payload["exercises"].append({**item, "id": key, "family_id": key})
    return SkillPack.model_validate(payload)


def gaps(audit, **criteria):
    return [
        gap
        for cell in audit["cells"]
        for scenario in cell["scenarios"]
        if all(scenario[key] == value for key, value in criteria.items())
        for gap in scenario["gaps"]
    ]


def test_static_coverage_is_not_planner_horizon_coverage():
    pack = lesson_pack()
    assert coverage_audit(pack)["ready"]
    audit = planning_audit(pack)
    assert not audit["ready"]
    assert len(audit["cells"]) == 9
    assert audit["horizon_days"] == 14
    assert audit["runtime_availability"] == "assumed_declared_variants"
    failures = gaps(audit, profile="ready", weekdays=[0, 1, 2, 3, 4, 5])
    assert any(x["code"] == "planner_content_gap" for x in failures)
    assert any("exposure_limit" in x.get("rejection_codes", []) for x in failures)
    assert audit == planning_audit(pack)
    assert pack.digest() == audit["pack_digest"]


def test_sufficient_safe_inventory_rehearses_nine_cells_without_mutation():
    pack = stocked_pack()
    before = pack.canonical_json()
    audit = planning_audit(pack)
    assert audit["ready"], audit
    assert all(len(x["scenarios"]) >= 20 for x in audit["cells"])
    assert pack.canonical_json() == before
    rendered = json.dumps(audit)
    for private in (
        "Synthetic loop invariant.",
        "Synthetic O(n) analysis.",
        "reference_solution",
        "starter_code",
        "response",
        "Which value is 1 + 2?",
    ):
        assert private not in rendered


def test_selected_lessons_must_cover_the_actual_block_concepts():
    payload = stocked_pack().model_dump()
    root, child = lesson_pack().topological_order()
    # Static coverage has all lessons; select a root+child exercise after readiness.
    item = next(x for x in payload["exercises"] if x["id"] == "a_runtime_probe")
    item["concept_ids"] = [root, child]
    payload["structural_repairs"] = []
    payload["learning_lessons"] = [
        x for x in payload["learning_lessons"] if root not in x["concept_ids"]
    ]
    audit = planning_audit(SkillPack.model_validate(payload))
    assert any(x["code"] == "selected_lesson_unavailable" for x in gaps(audit))


def test_verified_profile_respects_packs_stronger_prerequisite_thresholds():
    payload = stocked_pack().model_dump()
    for edge in payload["edges"]:
        edge["minimum_mastery"] = 1
    audit = planning_audit(SkillPack.model_validate(payload))
    assert audit["ready"], audit


def test_audit_exposes_text_practice_that_cannot_verify_implementation():
    payload = stocked_pack().model_dump()
    item = next(x for x in payload["exercises"] if x["id"] == "a_runtime_probe")
    item.update(modality="text", evidence_mode="trace", variants=[], tests=[])
    payload["structural_repairs"] = []
    audit = planning_audit(SkillPack.model_validate(payload))
    assert any(x["code"] == "unverified_text_practice" for x in gaps(audit))


def test_cli_emits_replayable_report_and_failure_exit(tmp_path, monkeypatch, capsys):
    path = tmp_path / "pack.json"
    for pack, expected in ((lesson_pack(), 1), (stocked_pack(), 0)):
        path.write_text(pack.canonical_json(), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["skillpacks", "learning-plan-audit", str(path)])
        assert cli.main() == expected
        report = json.loads(capsys.readouterr().out)
        assert report == planning_audit(pack)


def test_missing_launch_cells_remain_explicit():
    payload = lesson_pack().model_dump()
    payload["tracks"] = [x for x in payload["tracks"] if x["id"] != "competitive"]
    payload["goals"] = [x for x in payload["goals"] if x["track_id"] != "competitive"]
    payload["learning_lessons"] = [
        x for x in payload["learning_lessons"] if x["track"] != "competitive"
    ]
    payload["diagnostics"] = [x for x in payload["diagnostics"] if x["track"] != "competitive"]
    audit = planning_audit(SkillPack.model_validate(payload))
    missing = [x for x in audit["cells"] if x["track"] == "competitive"]
    assert len(missing) == 3
    assert all(not x["ready"] and not x["scenarios"] for x in missing)
    assert all(x["inventory_gaps"] == [dict(code="missing_cell")] for x in missing)


@pytest.mark.parametrize("stocked", [False, True])
def test_launch_publication_requires_planner_coverage_and_keeps_failed_release_staged(
    platform, stocked
):
    app, client = platform
    administrators(app)
    payload = (stocked_pack() if stocked else lesson_pack()).model_dump(mode="json")
    payload["purpose"] = "launch"
    auth = headers(client, "author")
    created = client.post("/api/v1/admin/skill-packs", headers=auth, json=payload)
    assert created.status_code == 201, created.text
    path = f"/api/v1/admin/skill-packs/{payload['key']}/versions/{payload['version']}/learning-plan-audit"
    report = client.get(path)
    assert report.status_code == 200, report.text
    assert report.json()["ready"] == stocked
    assert client.get(path.replace(payload["version"], "99.0.0")).status_code == 404
    auth = headers(client, "reviewer")
    for stage in ("technical_review", "learning_review", "language_verified", "staged"):
        response = action(
            client,
            payload,
            stage,
            auth,
            payload["languages"] if stage == "language_verified" else [],
        )
        assert response.status_code == 200, response.text
    response = action(client, payload, "publish", auth)
    assert response.status_code == (200 if stocked else 422), response.text
    if not stocked:
        assert response.json()["error"]["code"] == "learning_plan_coverage_incomplete"
    with Session(app.state.engine) as db:
        record = db.get(SkillPackVersion, created.json()["id"])
        assert record.status == ("released" if stocked else "staged")
        assert db.get(SkillPackHead, payload["key"]).active_id == (record.id if stocked else None)
    login(client, "ordinary-learner")
    assert client.get(path).status_code == 403


def test_admin_planner_audit_requires_authentication(platform):
    app, client = platform
    assert (
        client.get("/api/v1/admin/skill-packs/dsa/versions/1.0.0/learning-plan-audit").status_code
        == 401
    )
