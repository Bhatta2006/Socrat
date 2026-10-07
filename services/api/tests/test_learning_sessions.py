import itertools

import pytest
from m6_support import setup
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_execution import claim, queue, result
from test_foundation import login
from test_foundation import platform as platform

from socrat.models import LearningSession, OutboxEvent, SessionCommand, SkillPackVersion


def begin(platform, monkeypatch, track="foundations", language="python"):
    app, client, headers, worker, goal = setup(platform, monkeypatch, track, language)
    app.state.settings.learning_sessions_enabled = True
    plan = client.get(f"/api/v1/goals/{goal['id']}/curriculum").json()
    response = client.post(
        f"/api/v1/goals/{goal['id']}/learning-session",
        headers=headers,
        json=dict(curriculum_revision=plan["revision"]),
    )
    assert response.status_code == 200, response.text
    return app, client, headers, worker, goal, response.json()


def act(client, headers, session, action="advance", key=None, **changes):
    return client.post(
        f"/api/v1/learning-sessions/{session['id']}/commands",
        headers=headers,
        json=dict(
            action=action,
            expected_revision=session["revision"],
            idempotency_key=key or f"step-{session['revision']}",
            **changes,
        ),
    )


@pytest.mark.parametrize(
    "track,language",
    list(itertools.product(["foundations", "interview", "competitive"], ["python", "cpp", "java"])),
)
def test_nine_cell_normal_session_submit_resume_and_no_passive_mastery(
    platform, monkeypatch, track, language
):
    complete_code_journey(platform, monkeypatch, track, language)


def complete_code_journey(platform, monkeypatch, track, language):
    """Reusable synthetic journey with signed worker results, never a sandbox attestation."""
    app, client, headers, worker, goal, session = begin(platform, monkeypatch, track, language)
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    assert session["track"] == track and session["language"] == language
    visible_content = str([block["content"] for block in session["blocks"]])
    assert "reference_solution" not in str(session) and "1436" not in visible_content
    assert all(not x["content"]["prompt"] for x in session["blocks"][1:])
    assert (
        client.post(
            f"/api/v1/goals/{goal['id']}/learning-session",
            headers=headers,
            json=dict(curriculum_revision=session["curriculum_revision"]),
        ).json()
        == session
    )
    pause = act(client, headers, session, "pause")
    assert pause.status_code == 200, pause.text
    assert act(client, headers, pause.json(), answer="ignored").status_code == 409
    session = act(client, headers, pause.json(), "resume").json()
    for mode in ("retrieval", "instruction", "guided"):
        available = next(x for x in session["blocks"] if x["status"] == "available")
        assert available["mode"] == mode
        before = session
        response = act(
            client, headers, session, **({} if mode == "instruction" else {"answer": "My trace"})
        )
        assert response.status_code == 200, response.text
        assert (
            act(
                client, headers, before, **({} if mode == "instruction" else {"answer": "My trace"})
            ).json()
            == response.json()
        )
        session = response.json()
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    assert act(client, headers, session, answer="I passed").status_code == 409
    assert queue(client, headers, attempt, "runs", key="sample").status_code == 200
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    assert act(client, headers, session, run_id=job.manifest.job_id).status_code == 409
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    signed = result(job)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=signed).status_code
        == 200
    )
    response = act(client, headers, session, run_id=job.manifest.job_id)
    assert response.status_code == 200, response.text
    session = response.json()
    assert act(client, headers, session, answer="My explanation").status_code == 422
    response = act(
        client, headers, session, answer="My explanation", reflection="implementation_bug"
    )
    assert response.status_code == 200, response.text
    session = response.json()
    assert session["status"] == "completed" and not session["mastery_claim"]
    assert client.get(f"/api/v1/goals/{goal['id']}/learning-session").json()["session"] == session
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial + 1
    assert act(client, headers, session, answer="Again").status_code == 409
    with Session(app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.kind == "learning.session_completed")
            )
            == 1
        )
        with pytest.raises(DBAPIError):
            db.execute(update(LearningSession).values(snapshot={}))
    return app, client, headers, goal, session


def test_session_ownership_csrf_revision_quarantine_and_receipts(platform, monkeypatch):
    app, client, headers, worker, goal, session = begin(platform, monkeypatch)
    assert act(client, {}, session, answer="trace").status_code == 403
    assert act(client, headers, {**session, "revision": 999}, answer="trace").status_code == 409
    saved = act(client, headers, session, answer="trace", key="retry")
    assert saved.status_code == 200
    assert act(client, headers, session, answer="different", key="retry").status_code == 409
    login(client, "other")
    me = client.get("/api/v1/me").json()
    other = {**headers, "X-CSRF-Token": me["csrf_token"]}
    assert act(client, other, saved.json()).status_code == 404
    assert client.get(f"/api/v1/goals/{goal['id']}/learning-session").status_code == 404
    with Session(app.state.engine) as db, db.begin():
        row = db.get(LearningSession, session["id"])
        pack = db.get(SkillPackVersion, row.pack_id)
        pack.status = "quarantined"
    login(client)
    me = client.get("/api/v1/me").json()
    headers["X-CSRF-Token"] = me["csrf_token"]
    assert client.get(f"/api/v1/goals/{goal['id']}/learning-session").status_code == 409
    assert act(client, headers, saved.json()).status_code == 409
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(SessionCommand)) == 1


def test_session_feature_is_disabled_by_default(platform):
    app, client = platform
    assert not client.get("/api/v1/features").json()["learning_sessions"]
    assert client.get("/api/v1/goals/any/learning-session").status_code == 404


def test_failed_execution_retry_and_day_boundary_preserve_progress(platform, monkeypatch):
    app, client, headers, worker, goal, session = begin(platform, monkeypatch)
    for mode in ("retrieval", "instruction", "guided"):
        session = act(
            client, headers, session, **({} if mode == "instruction" else {"answer": "trace"})
        ).json()
    block = next(x for x in session["blocks"] if x["status"] == "available")
    attempt = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    assert (
        client.post(
            "/api/v1/execution/worker/result", headers=worker, json=result(job, failed=True)
        ).status_code
        == 200
    )
    assert act(client, headers, session, run_id=job.manifest.job_id).status_code == 409
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial
    assert queue(client, headers, attempt, key="retry-healthy").status_code == 200
    job = claim(client, worker)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    session = act(client, headers, session, run_id=job.manifest.job_id).json()
    from socrat.models import now

    tomorrow = now() + 86400
    monkeypatch.setattr("socrat.learning.routes.now", lambda: tomorrow)
    assert act(client, headers, session, answer="explanation", reflection="none").status_code == 409
    with Session(app.state.engine) as db:
        assert db.get(LearningSession, session["id"]).revision == session["revision"]


def test_text_session_is_ungraded_and_abandon_is_terminal(platform, monkeypatch):
    from m5_support import planner_pack

    monkeypatch.setattr("m6_support.code_pack", planner_pack)
    app, client, headers, worker, goal, session = begin(platform, monkeypatch)
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    for mode in ("retrieval", "instruction", "guided", "independent", "exit_check"):
        changes = {} if mode == "instruction" else dict(answer="response")
        if mode == "exit_check":
            changes["reflection"] = "none"
        response = act(client, headers, session, **changes)
        assert response.status_code == 200, response.text
        session = response.json()
    assert session["status"] == "completed"
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial


def test_abandon_preserves_responses_and_does_not_restart(platform, monkeypatch):
    app, client, headers, worker, goal, session = begin(platform, monkeypatch)
    session = act(client, headers, session, answer="response").json()
    response = act(client, headers, session, "abandon")
    assert response.status_code == 200, response.text
    session = response.json()
    assert session["status"] == "abandoned" and session["blocks"][0]["answer"] == "response"
    assert act(client, headers, session, "resume").status_code == 409
    assert (
        client.post(
            f"/api/v1/goals/{goal['id']}/learning-session",
            headers=headers,
            json=dict(curriculum_revision=session["curriculum_revision"]),
        ).json()
        == session
    )
