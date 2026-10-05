"""Synthetic ready Competitive learners; no claim of live runtime/content acceptance."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from m6_support import profiles, setup
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_execution import claim, queue, result
from test_foundation import platform as platform
from test_learner_state import fact
from test_learning_sessions import act

from socrat.learnerstate.service import append_fact, facts_for
from socrat.models import (
    CodeAttempt,
    LearnerGoal,
    LearningEvidence,
    SkillPackVersion,
    identifier,
    now,
)
from socrat.skillpacks.service import load


def prepared(
    platform, monkeypatch, language="python", timing="standard", minutes=30, ready_all=False
):
    # Keep duration tests away from local midnight; expiry is tested separately.
    clock = [
        int(
            datetime.fromtimestamp(now(), ZoneInfo("Asia/Kolkata"))
            .replace(hour=9, minute=0, second=0)
            .timestamp()
        )
    ]
    for route in ("learning", "execution", "planning", "diagnostics"):
        monkeypatch.setattr(f"socrat.{route}.routes.now", lambda: clock[0])
    app, client, headers, worker, goal = setup(platform, monkeypatch, "competitive", language)
    app.state.settings.learning_sessions_enabled = True
    monkeypatch.setattr("socrat.learning.routes.now", lambda: clock[0])
    monkeypatch.setattr("socrat.execution.routes.now", lambda: clock[0])
    path = f"/api/v1/goals/{goal['id']}/curriculum"
    plan = client.get(path).json()
    with Session(app.state.engine) as db, db.begin():
        owner = db.get(LearnerGoal, goal["id"])
        record = db.get(SkillPackVersion, plan["pack_id"])
        roots = (
            load(record).topological_order() if ready_all else load(record).topological_order()[:1]
        )
        for index in range(10 * len(roots)):
            sequence = len(facts_for(db, owner.user_id)) + 1
            append_fact(
                db,
                owner.user_id,
                fact(
                    index=sequence,
                    sequence=sequence,
                    event_id=identifier(),
                    source_id=identifier(),
                    user_id=owner.user_id,
                    goal_id=goal["id"],
                    pack_id=record.id,
                    pack_digest=record.digest,
                    concept_ids=[roots[index // 10]],
                    track="competitive",
                    language=language,
                    family_id=f"ready_family_{index}",
                    occurred_at=clock[0],
                ),
            )
    refreshed = client.post(
        path + "/commands",
        headers=headers,
        json=dict(
            action="refresh",
            expected_revision=plan["revision"],
            idempotency_key="ready-plan",
            minutes=minutes,
        ),
    )
    assert refreshed.status_code == 200, refreshed.text
    plan = refreshed.json()
    assert (
        client.post(
            path + "/commands",
            headers=headers,
            json=dict(
                action="confirm",
                expected_revision=plan["revision"],
                idempotency_key="ready-confirm",
                reviewed_digest=plan["review_digest"],
            ),
        ).status_code
        == 200
    )
    plan = client.get(path).json()
    response = client.post(
        f"/api/v1/goals/{goal['id']}/learning-session",
        headers=headers,
        json=dict(curriculum_revision=plan["revision"], timing=timing),
    )
    assert response.status_code == 200, response.text
    session = response.json()
    assert any(x["timed"] for x in session["blocks"]) == (timing == "standard")
    return app, client, headers, worker, goal, session, clock


def independent(client, headers, session):
    for mode in ("retrieval", "instruction", "guided"):
        response = act(
            client, headers, session, **({} if mode == "instruction" else {"answer": "trace"})
        )
        assert response.status_code == 200, response.text
        session = response.json()
    return session


def tick(client, worker, clock, stamp):
    clock[0] = stamp
    response = client.post(
        "/api/v1/execution/worker/heartbeat",
        headers=worker,
        json=dict(worker_id="worker-1", images=[x["image"] for x in profiles()]),
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("language", ["python", "cpp", "java"])
def test_timed_deadline_preserves_source_and_upsolve_is_seen(platform, monkeypatch, language):
    app, client, headers, worker, goal, session, clock = prepared(platform, monkeypatch, language)
    code_block = next(x for x in session["blocks"] if x["mode"] == "independent")
    parent = client.get(f"/api/v1/attempts/{code_block['attempt_id']}").json()
    assert queue(client, headers, parent).json()["error"]["code"] == "session_block_locked"
    session = independent(client, headers, session)
    assert queue(client, headers, parent).json()["error"]["code"] == "timed_block_not_started"
    response = act(client, headers, session, "start_timed")
    assert response.status_code == 200, response.text
    timed = response.json()
    assert act(client, headers, session, "start_timed").json() == timed
    block = next(x for x in timed["blocks"] if x["status"] == "available")
    deadline = block["deadline_at"]
    assert act(client, headers, timed, "start_timed", key="reset-timer").status_code == 409
    assert (
        act(client, headers, timed, "pause").json()["error"]["code"] == "timed_block_cannot_pause"
    )
    assert (
        act(client, headers, timed, "upsolve", error_classification="time_pressure").status_code
        == 409
    )
    source = (
        parent["source"] + "\n// learner draft"
        if language != "python"
        else parent["source"] + "\n# learner draft"
    )
    assert (
        client.patch(
            f"/api/v1/attempts/{parent['id']}/draft",
            headers=headers,
            json=dict(source=source, expected_revision=0),
        ).status_code
        == 200
    )
    parent["revision"] = 1
    tick(client, worker, clock, deadline)
    assert queue(client, headers, parent).json()["error"]["code"] == "timed_window_ended"
    loaded = client.get(f"/api/v1/goals/{goal['id']}/learning-session").json()["session"]
    assert (
        next(x for x in loaded["blocks"] if x["status"] == "available")["deadline_at"] == deadline
    )
    assert act(client, headers, timed, "upsolve").status_code == 422
    before = client.get("/api/v1/learner-state/evidence").json()["total"]
    response = act(client, headers, timed, "upsolve", error_classification="time_pressure")
    assert response.status_code == 200, response.text
    upsolve = response.json()
    block = next(x for x in upsolve["blocks"] if x["status"] == "available")
    assert block["mode"] == "upsolve" and not block["timed"]
    assert block["timed_outcome"]["outcome"] == "timed_out"
    repair = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    assert repair["id"] != parent["id"] and repair["source"] == source
    assert queue(client, headers, parent, key="after-upsolve").status_code == 409
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == before
    assert queue(client, headers, repair).status_code == 200
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    response = act(client, headers, upsolve, run_id=job.manifest.job_id)
    assert response.status_code == 200, response.text
    session = response.json()
    session = act(
        client, headers, session, answer="why it works", reflection="time_pressure"
    ).json()
    assert session["status"] == "completed"
    with Session(app.state.engine) as db:
        stored = db.get(CodeAttempt, repair["id"])
        assert not stored.snapshot["unseen"]
        evidence = db.scalar(
            select(LearningEvidence).where(LearningEvidence.source_id == repair["id"])
        )
        assert not evidence.payload["unseen"]
        assert evidence.payload["elapsed_seconds"] == 0


def test_on_time_submit_finishes_after_deadline_without_queue_penalty(platform, monkeypatch):
    app, client, headers, worker, goal, session, clock = prepared(platform, monkeypatch)
    session = independent(client, headers, session)
    session = act(client, headers, session, "start_timed").json()
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    tick(client, worker, clock, block["deadline_at"] - 1)
    queued = queue(client, headers, attempt)
    assert queued.status_code == 200, queued.text
    tick(client, worker, clock, block["deadline_at"] + 5)
    assert queue(client, headers, attempt).json() == queued.json()
    assert (
        act(client, headers, session, "upsolve", error_classification="time_pressure").json()[
            "error"
        ]["code"]
        == "timed_submit_pending"
    )
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    assert (
        act(client, headers, session, "upsolve", error_classification="time_pressure").json()[
            "error"
        ]["code"]
        == "upsolve_not_required"
    )
    response = act(client, headers, session, run_id=job.manifest.job_id)
    assert response.status_code == 200, response.text
    step = next(x for x in response.json()["blocks"] if x["mode"] == "independent")
    assert step["timed_outcome"]["outcome"] == "solved"
    with Session(app.state.engine) as db:
        evidence = db.scalar(
            select(LearningEvidence).where(LearningEvidence.source_id == attempt["id"])
        )
        assert evidence.payload["elapsed_seconds"] == block["minutes"] * 60 - 1


@pytest.mark.parametrize(
    "failed,status,outcome",
    [(True, "passed", "unscored_operational_failure"), (False, "wrong_answer", "unsuccessful")],
)
def test_unsuccessful_and_operational_results_enter_upsolve_without_forged_scores(
    platform, monkeypatch, failed, status, outcome
):
    app, client, headers, worker, goal, session, clock = prepared(platform, monkeypatch)
    session = independent(client, headers, session)
    session = act(client, headers, session, "start_timed").json()
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    before = client.get("/api/v1/learner-state/evidence").json()["total"]
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    assert (
        client.post(
            "/api/v1/execution/worker/result",
            headers=worker,
            json=result(job, failed=failed, status=status),
        ).status_code
        == 200
    )
    if not failed:
        assert (
            act(client, headers, session, run_id=job.manifest.job_id).json()["error"]["code"]
            == "upsolve_required"
        )
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == before + int(not failed)
    response = act(client, headers, session, "upsolve", error_classification="implementation_bug")
    assert response.status_code == 200, response.text
    step = next(x for x in response.json()["blocks"] if x["status"] == "available")
    assert step["timed_outcome"]["outcome"] == outcome
    if failed:
        assert "score" not in step["timed_outcome"]


def test_untimed_choice_is_pinned_and_not_a_timed_result(platform, monkeypatch):
    app, client, headers, worker, goal, session, clock = prepared(
        platform, monkeypatch, timing="untimed"
    )
    assert session["timing"] == "untimed"
    response = client.post(
        f"/api/v1/goals/{goal['id']}/learning-session",
        headers=headers,
        json=dict(curriculum_revision=session["curriculum_revision"], timing="standard"),
    )
    assert response.json()["error"]["code"] == "session_timing_already_chosen"
    session = independent(client, headers, session)
    assert act(client, headers, session, "start_timed").status_code == 409
    block = next(x for x in session["blocks"] if x["status"] == "available")
    assert "deadline_at" not in block
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    assert queue(client, headers, attempt).status_code == 200


def test_solve_duration_uses_admission_receipt_not_later_pause(platform, monkeypatch):
    app, client, headers, worker, goal, session, clock = prepared(
        platform, monkeypatch, timing="untimed"
    )
    session = independent(client, headers, session)
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    started = clock[0]
    tick(client, worker, clock, started + 5)
    session = act(client, headers, session, "pause").json()
    assert queue(client, headers, attempt).json()["error"]["code"] == "session_not_active"
    tick(client, worker, clock, started + 100)
    session = act(client, headers, session, "resume").json()
    tick(client, worker, clock, started + 103)
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    tick(client, worker, clock, started + 110)
    assert act(client, headers, session, "pause").status_code == 200
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    with Session(app.state.engine) as db:
        evidence = db.scalar(
            select(LearningEvidence).where(LearningEvidence.source_id == attempt["id"])
        )
        assert evidence.payload["elapsed_seconds"] == 8


def test_session_bound_attempt_obeys_feature_kill_switch(platform, monkeypatch):
    app, client, headers, worker, goal, session, clock = prepared(
        platform, monkeypatch, timing="untimed"
    )
    session = independent(client, headers, session)
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    app.state.settings.learning_sessions_enabled = False
    assert (
        queue(client, headers, attempt).json()["error"]["code"] == "learning_sessions_unavailable"
    )
    assert (
        client.patch(
            f"/api/v1/attempts/{attempt['id']}/draft",
            headers=headers,
            json=dict(source="saved even during rollback", expected_revision=0),
        ).status_code
        == 200
    )
