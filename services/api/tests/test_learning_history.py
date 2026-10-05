from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_execution import claim, queue, result
from test_foundation import login
from test_foundation import platform as platform
from test_learning_sessions import act, begin

from socrat.learnerstate.service import append_fact, facts_for
from socrat.learning.service import expire_session
from socrat.models import LearnerGoal, LearningSession, OutboxEvent, identifier


def reach_code(client, headers, session):
    for mode in ("retrieval", "instruction", "guided"):
        response = act(
            client, headers, session, **({} if mode == "instruction" else {"answer": "trace"})
        )
        assert response.status_code == 200, response.text
        session = response.json()
    return session, next(x for x in session["blocks"] if x["status"] == "available")


def test_history_is_owned_expired_read_only_and_work_survives(platform, monkeypatch):
    app, client, headers, worker, goal, session = begin(platform, monkeypatch)
    session = act(client, headers, session, answer="saved learner response").json()
    tomorrow = int(
        (datetime.fromisoformat(session["local_date"]) + timedelta(days=1))
        .replace(tzinfo=ZoneInfo(goal["goal"]["timezone"]))
        .timestamp()
    )
    monkeypatch.setattr("socrat.learning.routes.now", lambda: tomorrow)
    history = client.get(f"/api/v1/goals/{goal['id']}/learning-sessions").json()["items"]
    assert history[0]["status"] == "expired" and history[0]["recovery_required"]
    assert not history[0]["can_resume"] and "answer" not in str(history)
    saved = client.get(f"/api/v1/learning-sessions/{session['id']}")
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "expired"
    assert saved.json()["blocks"][0]["answer"] == "saved learner response"
    assert act(client, headers, session, "resume").status_code == 409
    with Session(app.state.engine) as db, db.begin():
        row = db.get(LearningSession, session["id"])
        assert row.revision == session["revision"]  # Reads do not mutate persisted state.
        assert expire_session(db, db.get(LearnerGoal, goal["id"]), row, tomorrow)
        assert not expire_session(db, db.get(LearnerGoal, goal["id"]), row, tomorrow + 100)
    with Session(app.state.engine) as db:
        assert db.get(LearningSession, session["id"]).revision == session["revision"] + 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.kind == "learning.session_expired")
            )
            == 1
        )
    login(client, "other")
    assert client.get(f"/api/v1/goals/{goal['id']}/learning-sessions").status_code == 404
    assert client.get(f"/api/v1/learning-sessions/{session['id']}").status_code == 404
    assert client.get(f"/api/v1/goals/{goal['id']}/learning-session-telemetry").status_code == 404


def test_meaningful_activation_requires_valid_submit_and_invalidation_reconciles(
    platform, monkeypatch
):
    app, client, headers, worker, goal, session = begin(platform, monkeypatch)
    path = f"/api/v1/goals/{goal['id']}/learning-session-telemetry"
    assert client.get(path).json()["meaningful_sessions"] == 0
    session, block = reach_code(client, headers, session)
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    assert queue(client, headers, attempt, "runs", key="sample").status_code == 200
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    assert client.get(path).json()["meaningful_sessions"] == 0
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    export = client.get(path)
    assert export.status_code == 200, export.text
    assert export.json()["meaningful_sessions"] == 1
    assert export.json()["activation"]["activated"]
    for private in ("answer", "source", "reference_solution", "hidden", "1436"):
        assert private not in export.text
    session = act(client, headers, session, run_id=job.manifest.job_id).json()
    session = act(client, headers, session, answer="explanation", reflection="none").json()
    assert session["status"] == "completed"
    assert client.get(path).json()["duration"]["samples"] == 1
    assert not client.get(path).json()["duration"]["calibrated"]
    with Session(app.state.engine) as db, db.begin():
        facts = facts_for(
            db,
            goal["user_id"]
            if "user_id" in goal
            else db.get(LearningSession, session["id"]).user_id,
        )
        original = next(x for x in facts if x.source_id == block["attempt_id"])
        correction = original.model_copy(
            update=dict(
                event_id=identifier(),
                sequence=len(facts) + 1,
                kind="invalidated",
                target_event_id=original.event_id,
                quality=0.0,
                valid=False,
            )
        )
        append_fact(db, original.user_id, correction)
    assert client.get(path).json()["meaningful_sessions"] == 0
    assert not client.get(path).json()["activation"]["activated"]


@pytest.mark.parametrize("finish_set", [False, True])
def test_mixed_recovery_and_new_start_do_not_carry_partial_work(platform, monkeypatch, finish_set):
    from test_competitive_sets import mixed_pack
    from test_timed_learning import independent, prepared, tick

    from socrat.models import CurriculumRevision

    monkeypatch.setattr("m6_support.code_pack", mixed_pack)
    app, client, auth, worker, goal, session, clock = prepared(
        platform, monkeypatch, minutes=60, ready_all=True
    )
    session = independent(client, auth, session)
    for _ in range(2 if finish_set else 1):
        session = act(client, auth, session, "start_timed").json()
        block = next(x for x in session["blocks"] if x["status"] == "available")
        attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
        assert queue(client, auth, attempt).status_code == 200
        job = claim(client, worker)
        assert (
            client.post(
                "/api/v1/execution/worker/result", headers=worker, json=result(job)
            ).status_code
            == 200
        )
        response = act(client, auth, session, run_id=job.manifest.job_id)
        assert response.status_code == 200, response.text
        session = response.json()
    if finish_set:
        session = act(client, auth, session, answer="reflection", reflection="none").json()
        assert session["status"] == "completed"
    old_id = session["id"]
    tick(client, worker, clock, clock[0] + 86400)
    weekday = datetime.fromtimestamp(clock[0], ZoneInfo(goal["goal"]["timezone"])).weekday()
    path = f"/api/v1/goals/{goal['id']}/curriculum"
    plan = client.get(path).json()
    response = client.post(
        path + "/commands",
        headers=auth,
        json=dict(
            action="recover",
            expected_revision=plan["revision"],
            idempotency_key="next-day-recover",
            weekdays=sorted({weekday, (weekday + 2) % 7, (weekday + 4) % 7}),
        ),
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    with Session(app.state.engine) as db:
        revision = db.get(CurriculumRevision, plan["id"])
        assert revision.snapshot["replay_inputs"]["missed_days"] == int(not finish_set)
    confirmed = client.post(
        path + "/commands",
        headers=auth,
        json=dict(
            action="confirm",
            expected_revision=plan["revision"],
            idempotency_key="next-day-confirm",
            reviewed_digest=plan["review_digest"],
        ),
    )
    assert confirmed.status_code == 200, confirmed.text
    started = client.post(
        f"/api/v1/goals/{goal['id']}/learning-session",
        headers=auth,
        json=dict(curriculum_revision=confirmed.json()["revision"]),
    )
    assert started.status_code == 200, started.text
    assert started.json()["id"] != old_id
    with Session(app.state.engine) as db:
        previous = db.get(LearningSession, old_id)
        assert previous.status == ("completed" if finish_set else "expired")
        assert previous.progress[0]["answer"] == "trace"
