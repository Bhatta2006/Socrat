import itertools
import json
from pathlib import Path

import pytest
from m7_support import lesson_pack
from pydantic import ValidationError
from sqlalchemy.orm import Session
from test_execution import claim, queue, result
from test_foundation import platform as platform
from test_learning_sessions import act, begin
from test_skill_packs import action, administrators, headers

from socrat.learning.content import coverage_audit
from socrat.models import SkillPackVersion
from socrat.skillpacks.schema import SkillPack


@pytest.mark.parametrize(
    "track,language",
    list(
        itertools.product(
            ["foundations", "interview", "competitive"],
            ["python", "cpp", "java"],
        )
    ),
)
def test_reviewed_lessons_and_private_objective_checks(platform, monkeypatch, track, language):
    monkeypatch.setattr("m6_support.code_pack", lesson_pack)
    app, client, auth, worker, goal, session = begin(platform, monkeypatch, track, language)
    before = client.get("/api/v1/learner-state/evidence").json()["total"]
    block = session["blocks"][0]
    assert block["content"]["objective_check"]["kind"] == "choice"
    assert "answer" not in block["content"]["objective_check"]
    assert "response" not in str(block["content"])
    assert all("objective_check" not in x["content"] for x in session["blocks"][1:])
    assert act(client, auth, session, answer="invented").status_code == 422
    response = act(client, auth, session, answer="four")
    assert response.status_code == 200, response.text
    assert response.json()["blocks"][0]["check_result"]["score"] == 0
    assert act(client, auth, session, answer="four").json() == response.json()
    session = response.json()
    block = next(x for x in session["blocks"] if x["status"] == "available")
    assert any(f"{language} semantics" in x for x in block["content"]["explanations"])
    if track == "interview":
        assert "Synthetic pattern recognition." in block["content"]["explanations"]
        assert "Synthetic loop invariant." in block["content"]["explanations"]
    session = act(client, auth, session).json()
    assert (
        language
        in next(x for x in session["blocks"] if x["status"] == "available")["content"]["examples"][
            0
        ]
    )
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == before


@pytest.mark.parametrize(
    "corruption",
    [
        "qualitative",
        "unknown_concept",
        "missing_pattern",
        "protected_repair",
        "same_family",
        "missing_version",
    ],
)
def test_learning_content_contract_fails_closed(corruption):
    payload = lesson_pack().model_dump()
    if corruption == "qualitative":
        payload["learning_lessons"][0]["exit_check"]["response"] = dict(kind="human_rubric")
    elif corruption == "unknown_concept":
        payload["learning_lessons"][0]["concept_ids"] = ["missing"]
    elif corruption == "missing_pattern":
        next(x for x in payload["learning_lessons"] if x["track"] == "interview")["correctness"] = (
            None
        )
    elif corruption == "protected_repair":
        payload["structural_repairs"][0]["variant_id"] = next(
            x["id"] for x in payload["exercises"] if x["inventory"] == "assessment"
        )
    elif corruption == "same_family":
        payload["structural_repairs"][0]["variant_id"] = "a_runtime_probe"
    else:
        payload["session_content_version"] = None
    with pytest.raises(ValidationError):
        SkillPack.model_validate(payload)


def test_coverage_audit_reports_nine_cells_and_publication_blocks_gaps(platform):
    pack = lesson_pack()
    audit = coverage_audit(pack)
    assert len(audit["cells"]) == 9
    assert audit["ready"], audit
    payload = pack.model_dump()
    payload["purpose"] = "launch"
    payload["learning_lessons"] = [
        x for x in payload["learning_lessons"] if x["language"] != "java"
    ]
    app, client = platform
    administrators(app)
    auth = headers(client, "author")
    created = client.post("/api/v1/admin/skill-packs", headers=auth, json=payload)
    assert created.status_code == 201, created.text
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
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "learning_content_coverage_incomplete"
    with Session(app.state.engine) as db:
        assert db.get(SkillPackVersion, created.json()["id"]).status == "staged"


def test_legacy_pack_digest_unchanged_by_empty_m7_fields():
    from socrat.learnerstate.policy import digest

    payload = json.loads(Path("contracts/fixtures/skill-packs/dsa-1.0.0.json").read_text())
    pack = SkillPack.model_validate(payload)
    canonical = json.loads(pack.canonical_json())
    assert "session_content_version" not in canonical
    assert "learning_lessons" not in canonical
    assert "structural_repairs" not in canonical
    legacy = pack.model_dump(mode="json")
    for key in (
        "session_content_version",
        "learning_lessons",
        "structural_repairs",
        "competitive_penalty",
        "diagnostics",
        "misconception_taxonomy",
    ):
        legacy.pop(key)
    for template in legacy["goals"]:
        template.pop("released_targets")
    assert pack.digest() == digest(legacy)


def test_objective_exit_is_exact_and_reflection_has_no_mastery_effect(platform, monkeypatch):
    monkeypatch.setattr("m6_support.code_pack", lesson_pack)
    app, client, auth, worker, goal, session = begin(platform, monkeypatch)
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    session = act(client, auth, session, answer="three").json()
    session = act(client, auth, session).json()
    session = act(client, auth, session, answer="trace").json()
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    assert queue(client, auth, attempt).status_code == 200
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    session = act(client, auth, session, run_id=job.manifest.job_id).json()
    check = next(x for x in session["blocks"] if x["status"] == "available")["content"][
        "objective_check"
    ]
    assert check["kind"] == "trace" and "answer" not in check
    assert act(client, auth, session, answer="4").status_code == 422
    response = act(client, auth, session, answer="04", reflection="none")
    assert response.status_code == 200, response.text
    assert response.json()["blocks"][-1]["check_result"]["score"] == 0
    assert response.json()["status"] == "completed"
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial + 1


def test_structural_review_mapping_controls_competitive_repairs():
    from test_competitive_sets import planned

    pack = lesson_pack()
    blocks = planned(pack)["days"][0]["blocks"]
    practice = [x for x in blocks if x["mode"] == "independent"]
    assert all(x.get("repair_review") == "reviewed_structural_variant" for x in practice)
    payload = pack.model_dump()
    payload["structural_repairs"] = []
    blocks = planned(SkillPack.model_validate(payload))["days"][0]["blocks"]
    assert all(x.get("repair_exercise_id") is None for x in blocks if x["mode"] == "independent")
    audit = coverage_audit(SkillPack.model_validate(payload))
    assert any(
        x["code"] == "missing_structural_repair" for cell in audit["cells"] for x in cell["gaps"]
    )


@pytest.mark.parametrize("operational_failure", [False, True])
def test_pinned_practice_penalty_ignores_operational_failures_and_upsolve(
    platform, monkeypatch, operational_failure
):
    from test_timed_learning import prepared

    monkeypatch.setattr("m6_support.code_pack", lesson_pack)
    app, client, auth, worker, goal, session, clock = prepared(
        platform, monkeypatch, ready_all=True
    )
    session = act(client, auth, session, answer="three").json()
    session = act(client, auth, session).json()
    session = act(client, auth, session, answer="trace").json()
    session = act(client, auth, session, "start_timed").json()
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    assert queue(client, auth, attempt).status_code == 200
    job = claim(client, worker)
    signed = result(job, failed=operational_failure, status="wrong_answer")
    response = client.post("/api/v1/execution/worker/result", headers=worker, json=signed)
    assert response.status_code == 200, response.text
    refreshed = client.get(f"/api/v1/goals/{goal['id']}/learning-session").json()["session"]
    assert refreshed["competitive_result"]["wrong_submissions"] == int(not operational_failure)
    assert refreshed["competitive_result"]["penalty_seconds"] == (0 if operational_failure else 60)
    repaired = act(client, auth, session, "upsolve", error_classification="implementation_bug")
    assert repaired.status_code == 200, repaired.text
    assert repaired.json()["competitive_result"] == refreshed["competitive_result"]
