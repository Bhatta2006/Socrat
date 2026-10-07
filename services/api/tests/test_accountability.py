import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from m5_support import completed
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform
from test_planning import send

from socrat.accountability.privacy import erase_once
from socrat.config import ContentAdminIdentity
from socrat.models import LearningEvidence, LoginSession, PrivacyRequest, User


def enabled(platform, monkeypatch):
    app, client, headers, goal = completed(platform, monkeypatch)
    app.state.settings.dashboard_enabled = True
    app.state.settings.reminders_enabled = True
    return app, client, headers, goal


def test_progress_is_owned_read_only_and_separates_evidence(platform, monkeypatch):
    app, client, headers, goal = enabled(platform, monkeypatch)
    with Session(app.state.engine) as db:
        before = [(row.id, row.payload) for row in db.scalars(select(LearningEvidence))]
    initial = client.get("/api/v1/progress").json()
    assert initial["goal_id"] == goal["id"]
    assert initial["today"]["action"] == "generate_plan"
    assert initial["concepts"]
    assert "PRIVATE" not in json.dumps(initial)
    plan = send(client, headers, goal).json()
    result = client.get("/api/v1/progress").json()
    assert result["today"]["action"] == "confirm_plan"
    assert result["plan"]["revision"] == plan["revision"]
    assert all(x["independent"]["count"] == 0 for x in result["trend"])
    with Session(app.state.engine) as db:
        assert before == [(row.id, row.payload) for row in db.scalars(select(LearningEvidence))]
    login(client, "bob")
    assert client.get(f"/api/v1/progress?goal_id={goal['id']}").status_code == 404
    assert client.get("/api/v1/progress").json()["today"]["action"] == "choose_goal"


def test_preferences_csrf_validation_revision_and_consent(platform):
    _, client = platform
    assert client.get("/api/v1/preferences").status_code == 401
    login(client)
    token = client.get("/api/v1/me").json()["csrf_token"]
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": token}
    original = client.get("/api/v1/preferences").json()
    assert original["reminders_consent"] is False
    revision = original.pop("revision")
    body = {**original, "expected_revision": revision}
    assert client.patch("/api/v1/preferences", json=body).status_code == 403
    assert (
        client.patch(
            "/api/v1/preferences", json={**body, "timezone": "Mars/City"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/v1/preferences", json={**body, "quiet_end": "25:00"}, headers=headers
        ).status_code
        == 422
    )
    saved = client.patch("/api/v1/preferences", json=body, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert client.patch("/api/v1/preferences", json=body, headers=headers).status_code == 409


def test_reminders_local_planned_day_quiet_pause_and_idempotency(platform, monkeypatch):
    app, client, headers, goal = enabled(platform, monkeypatch)
    first = send(client, headers, goal).json()
    confirmed = send(
        client, headers, goal, "confirm", 1, "confirm", reviewed_digest=first["review_digest"]
    ).json()
    day = next(x for x in first["days"] if x["blocks"])
    stamp = int(
        datetime.fromisoformat(day["date"])
        .replace(hour=9, minute=15, tzinfo=ZoneInfo("Asia/Kolkata"))
        .timestamp()
    )
    monkeypatch.setattr("socrat.accountability.routes.now", lambda: stamp)
    value = client.get("/api/v1/preferences").json()
    revision = value.pop("revision")
    body = {
        **value,
        "reminders_consent": True,
        "timezone": "Asia/Kolkata",
        "expected_revision": revision,
    }
    assert client.patch("/api/v1/preferences", json=body, headers=headers).status_code == 200
    # No configured time ever bypasses a quiet window, including overnight windows.
    response = client.post("/api/v1/reminders/check", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert client.post("/api/v1/reminders/check", headers=headers).json()["items"] == items
    assert client.get("/api/v1/reminders").json()["items"] == items
    send(client, headers, goal, "pause", confirmed["revision"], "pause")
    assert client.get("/api/v1/reminders").json()["items"] == []
    send(client, headers, goal, "resume", confirmed["revision"] + 1, "resume")
    quiet_body = {**body, "expected_revision": 1, "quiet_start": "08:00", "quiet_end": "10:00"}
    assert client.patch("/api/v1/preferences", json=quiet_body, headers=headers).status_code == 200
    assert client.get("/api/v1/reminders").json()["items"] == []
    assert client.post("/api/v1/reminders/check", headers=headers).json()["items"] == []
    login(client, "bob")
    other_headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    assert (
        client.post(f"/api/v1/reminders/{items[0]['id']}/opened", headers=other_headers).status_code
        == 404
    )


@pytest.mark.parametrize(
    "zone,instant",
    [
        ("America/New_York", "2026-11-01T05:30:00+00:00"),
        ("America/New_York", "2026-11-01T06:30:00+00:00"),
        ("Asia/Kolkata", "2026-10-07T19:00:00+00:00"),
    ],
)
def test_overnight_quiet_hours_and_dst(zone, instant):
    from socrat.accountability.preferences import quiet

    stamp = int(datetime.fromisoformat(instant).timestamp())
    value = {"timezone": zone, "quiet_start": "21:00", "quiet_end": "08:00"}
    assert quiet(value, stamp)
    assert quiet({**value, "quiet_start": "09:00", "quiet_end": "09:00"}, stamp)


def test_export_and_erasure_cover_owned_graph_without_private_keys(platform, monkeypatch):
    app, client, headers, goal = enabled(platform, monkeypatch)
    send(client, headers, goal)
    owner = client.get("/api/v1/me").json()["id"]
    exported = client.post("/api/v1/privacy/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.json()["data"]["diagnostic_answers"]
    assert exported.json()["data"]["learner_goals"][0]["details"]["goal"]
    assert "csrf_token" not in exported.text and "selection" not in exported.text
    assert (
        client.post(
            "/api/v1/privacy/delete", headers=headers, json={"confirmation": "yes"}
        ).status_code
        == 422
    )
    response = client.post(
        "/api/v1/privacy/delete", headers=headers, json={"confirmation": "DELETE MY DATA"}
    )
    assert response.status_code == 202, response.text
    receipt = response.json()
    assert client.get("/api/v1/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/dev-login",
            headers={"Origin": "http://localhost:3000"},
            json={"subject": "alice"},
        ).status_code
        == 403
    )
    with Session(app.state.engine) as db:
        assert db.scalar(select(LoginSession).where(LoginSession.user_id == owner)) is None
        with pytest.raises(DBAPIError):
            db.execute(delete(LearningEvidence).where(LearningEvidence.user_id == owner))
        db.rollback()
    assert erase_once(app.state.engine, receipt["created_at"]) == 1
    assert erase_once(app.state.engine, receipt["created_at"]) == 0
    with Session(app.state.engine) as db:
        from socrat.accountability.privacy import owned_filters
        from socrat.models import Base

        for name, predicate in owned_filters(owner).items():
            assert (
                db.execute(select(Base.metadata.tables[name]).where(predicate)).first() is None
            ), name
        shell = db.get(User, owner)
        assert shell.issuer == "erased" and shell.display_name == ""
        request = db.get(PrivacyRequest, receipt["id"])
        assert request.target_user_id is None
        assert request.status == "awaiting_external_cleanup"
        assert request.tasks["shared_editorial_lineage"] == "pending"
    url = f"/api/v1/privacy/requests/{receipt['id']}"
    assert client.get(url).status_code == 404
    assert (
        client.get(url, headers={"X-Privacy-Token": receipt["receipt_token"]}).json()["tasks"][
            "database"
        ]
        == "complete"
    )


def test_cleanup_requires_operator_receipts(platform):
    app, client = platform
    login(client)
    profile = client.get("/api/v1/me").json()
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": profile["csrf_token"]}
    receipt = client.post(
        "/api/v1/privacy/delete", headers=headers, json={"confirmation": "DELETE MY DATA"}
    ).json()
    erase_once(app.state.engine, receipt["created_at"])
    login(client, "operator")
    headers["X-CSRF-Token"] = client.get("/api/v1/me").json()["csrf_token"]
    url = f"/api/v1/admin/privacy/requests/{receipt['id']}/cleanup"
    body = {"task": "backups_replicas_logs", "evidence_reference": "private-review:cleanup-1"}
    assert client.post(url, json=body, headers=headers).status_code == 403
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="operator")
    ]
    result = client.post(url, json=body, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "complete"


def test_deletion_can_retry_after_session_revocation_without_duplicate_request(platform):
    from socrat.models import identifier

    app, client = platform
    login(client)
    profile = client.get("/api/v1/me").json()
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": profile["csrf_token"]}
    body = {"confirmation": "DELETE MY DATA", "request_id": identifier(), "receipt_token": "a" * 64}
    first = client.post("/api/v1/privacy/delete", headers=headers, json=body)
    assert first.status_code == 202
    retry = client.post("/api/v1/privacy/delete", headers=headers, json=body)
    assert retry.json() == first.json()
    assert (
        client.post(
            "/api/v1/privacy/delete", headers=headers, json={**body, "receipt_token": "b" * 64}
        ).status_code
        == 401
    )
    with Session(app.state.engine) as db:
        assert len(list(db.scalars(select(PrivacyRequest)))) == 1


@pytest.mark.parametrize("language", ["python", "cpp", "java"])
def test_code_tutor_and_session_artifacts_export_and_erase(platform, monkeypatch, language):
    from test_execution import queue
    from test_tutor import ask, prepared

    from socrat.accountability.privacy import owned_filters
    from socrat.models import Base

    app, client, headers, _, goal, attempt = prepared(platform, monkeypatch, language=language)
    assert ask(client, headers, attempt).status_code == 200
    assert queue(client, headers, attempt, mode="runs", stdin="2\n").status_code == 200
    app.state.settings.learning_sessions_enabled = True
    plan = client.get(f"/api/v1/goals/{goal['id']}/curriculum").json()
    session = client.post(
        f"/api/v1/goals/{goal['id']}/learning-session",
        headers=headers,
        json={"curriculum_revision": plan["revision"]},
    )
    # Hint exposure may require a refreshed plan; the earlier work stays owned.
    assert session.status_code in {200, 409}
    owner = client.get("/api/v1/me").json()["id"]
    export = client.post("/api/v1/privacy/export", headers=headers)
    assert export.status_code == 200, export.text
    assert export.json()["data"]["code_run_sources"]
    assert export.json()["data"]["tutor_artifacts"]
    assert all(
        "1436" not in row["source"] and "718" not in row["source"]
        for row in export.json()["data"]["code_run_sources"]
    )
    assert "reference_solution" not in export.text and "manifest" not in export.text
    request = client.post(
        "/api/v1/privacy/delete", headers=headers, json={"confirmation": "DELETE MY DATA"}
    ).json()
    assert erase_once(app.state.engine, request["created_at"]) == 1
    with Session(app.state.engine) as db:
        for name, predicate in owned_filters(owner).items():
            assert (
                db.execute(select(Base.metadata.tables[name]).where(predicate)).first() is None
            ), name


def test_protected_assessment_export_and_erasure(platform, monkeypatch):
    from m9_support import prepared, respond, start

    from socrat.models import AssessmentAnswer, AssessmentItem, AssessmentResponse

    app, client, headers, goal = prepared(platform, monkeypatch)
    session = start(client, headers, goal)
    session = respond(client, headers, session, answer="my-own-trace")
    response = client.post("/api/v1/privacy/export", headers=headers)
    assert response.status_code == 200, response.text
    assert "PRIVATE-M9-KEY" not in response.text
    assert response.json()["data"]["assessment_answers"][0]["answer"] == "my-own-trace"
    request = client.post(
        "/api/v1/privacy/delete", headers=headers, json={"confirmation": "DELETE MY DATA"}
    ).json()
    assert erase_once(app.state.engine, request["created_at"]) == 1
    with Session(app.state.engine) as db:
        assert db.scalar(select(AssessmentItem)) is None
        assert db.scalar(select(AssessmentAnswer)) is None
        assert db.scalar(select(AssessmentResponse)) is None


def test_one_time_defer_survives_expiry_without_mastery_write(platform, monkeypatch):
    from m9_support import assessment_pack

    from socrat.accountability.assessment_due import assessment_due
    from socrat.models import AssessmentDeferral, LearnerGoal, now

    app, client, headers, goal = enabled(platform, monkeypatch)
    stamp = now()
    monkeypatch.setattr("socrat.accountability.routes.now", lambda: stamp)
    pack = assessment_pack()
    with Session(app.state.engine) as db:
        owned = db.get(LearnerGoal, goal["id"])
        due = assessment_due(db, owned, pack, [], [], stamp)
        assert due["kind"] == "baseline" and due["can_defer"]
    monkeypatch.setattr(
        "socrat.accountability.routes.progress", lambda *args: {"assessment_due": due}
    )
    path = f"/api/v1/goals/{goal['id']}/assessment-deferral"
    before = client.get("/api/v1/learner-state/evidence").json()
    assert client.post(path, json={"cycle": due["cycle"]}, headers=headers).status_code == 200
    with Session(app.state.engine) as db:
        owned = db.get(LearnerGoal, goal["id"])
        assert db.scalar(select(AssessmentDeferral)).until_at == stamp + 86400
        deferred = assessment_due(db, owned, pack, [], [], stamp)
        assert not deferred["can_defer"] and not deferred["actionable"]
        expired = assessment_due(db, owned, pack, [], [], stamp + 86400)
        assert not expired["can_defer"] and expired["actionable"]
    monkeypatch.setattr(
        "socrat.accountability.routes.progress", lambda *args: {"assessment_due": expired}
    )
    assert client.post(path, json={"cycle": due["cycle"]}, headers=headers).status_code == 409
    assert client.get("/api/v1/learner-state/evidence").json() == before


def test_raw_retention_prunes_only_artifacts_and_preserves_evidence(platform, monkeypatch):
    from test_execution import queue
    from test_tutor import ask, prepared

    from socrat.accountability.retention import RAW_RETENTION_SECONDS, prune_once
    from socrat.models import CodeDraft, CodeRun, CodeRunSource, TutorArtifact, now

    app, client, headers, _, _, attempt = prepared(platform, monkeypatch)
    assert ask(client, headers, attempt).status_code == 200
    assert queue(client, headers, attempt, mode="runs", stdin="2\n").status_code == 200
    before = client.get("/api/v1/learner-state/evidence").json()
    stamp = now() + RAW_RETENTION_SECONDS + 100
    assert prune_once(app.state.engine, stamp) == 2
    with Session(app.state.engine) as db, db.begin():
        assert db.scalar(select(CodeDraft)) is None
        assert db.scalar(select(TutorArtifact)) is None
        assert db.scalar(select(CodeRunSource)) is not None  # Active job source is preserved.
        db.scalar(select(CodeRun)).status = "completed"
    assert prune_once(app.state.engine, stamp) == 1
    assert client.get("/api/v1/learner-state/evidence").json() == before


def test_privacy_metrics_are_aggregate_and_flag_overdue_cleanup(platform):
    from pydantic import SecretStr

    app, client = platform
    login(client)
    profile = client.get("/api/v1/me").json()
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": profile["csrf_token"]}
    receipt = client.post(
        "/api/v1/privacy/delete", headers=headers, json={"confirmation": "DELETE MY DATA"}
    ).json()
    with Session(app.state.engine) as db, db.begin():
        db.get(PrivacyRequest, receipt["id"]).deadline_at = 0
    app.state.settings.metrics_token = SecretStr("synthetic-metrics-token")
    response = client.get(
        "/api/metrics", headers={"Authorization": "Bearer synthetic-metrics-token"}
    )
    assert response.status_code == 200
    assert "socrat_privacy_overdue_requests 1.0" in response.text
    assert receipt["id"] not in response.text and profile["id"] not in response.text


def test_weekly_due_survives_unpromoted_retention_and_final_uses_mastery(platform, monkeypatch):
    from types import SimpleNamespace

    from m9_support import assessment_pack

    from socrat.accountability.assessment_due import assessment_due
    from socrat.models import LearnerGoal

    app, _, _, goal = enabled(platform, monkeypatch)
    pack = assessment_pack()
    baseline = SimpleNamespace(
        status="completed", snapshot={"kind": "baseline"}, result={"completed_at": 0}
    )
    final = SimpleNamespace(
        status="completed", snapshot={"kind": "final"}, result={"completed_at": 100}
    )
    with Session(app.state.engine) as db:
        owned = db.get(LearnerGoal, goal["id"])
        assert assessment_due(db, owned, pack, [], [baseline], 6 * 86400) is None
        weekly = assessment_due(db, owned, pack, [], [baseline], 7 * 86400)
        assert weekly["kind"] == "weekly"
        concepts = [{"band": "capable", "retention_due": True}]
        monkeypatch.setattr("socrat.assessment.service.retention_due", lambda *args: [])
        assert assessment_due(db, owned, pack, concepts, [baseline], 7 * 86400)["kind"] == "weekly"
        monkeypatch.setattr(
            "socrat.assessment.service.retention_due", lambda *args: [{"due_at": 2 * 86400}]
        )
        assert (
            assessment_due(db, owned, pack, concepts, [baseline], 7 * 86400)["kind"] == "retention"
        )
        assert (
            assessment_due(
                db,
                owned,
                pack,
                [{"band": "mastered", "retention_due": False}],
                [baseline],
                7 * 86400,
            )["kind"]
            == "final"
        )
        assert assessment_due(db, owned, pack, [], [final, baseline], 7 * 86400) is None


def test_today_pause_and_recovery_states_do_not_write_evidence(platform, monkeypatch):
    from socrat.models import now

    app, client, headers, goal = enabled(platform, monkeypatch)
    app.state.settings.learning_sessions_enabled = True
    stamp = now()
    monkeypatch.setattr("socrat.accountability.routes.now", lambda: stamp)
    weekday = datetime.fromtimestamp(stamp, ZoneInfo(goal["goal"]["timezone"])).weekday()
    first = send(
        client, headers, goal, weekdays=sorted({weekday, (weekday + 2) % 7, (weekday + 4) % 7})
    ).json()
    send(client, headers, goal, "confirm", 1, "confirm", reviewed_digest=first["review_digest"])
    before = client.get("/api/v1/learner-state/evidence").json()
    assert client.get("/api/v1/progress").json()["today"]["action"] == "start_session"
    send(client, headers, goal, "pause", 2, "pause")
    assert client.get("/api/v1/progress").json()["today"]["action"] == "resume_plan"
    stamp += 10 * 86400
    paused = client.get("/api/v1/progress").json()
    assert paused["today"]["action"] == "resume_plan" and paused["missed_days"] == 0
    assert client.get("/api/v1/learner-state/evidence").json() == before


def test_saved_today_session_remains_primary_when_new_evidence_stales_plan(platform, monkeypatch):
    from test_learning_sessions import begin

    from socrat.learnerstate.service import append_fact, facts_for
    from socrat.models import LearnerGoal, identifier

    app, client, _, _, goal, saved = begin(platform, monkeypatch)
    app.state.settings.dashboard_enabled = True
    with Session(app.state.engine) as db, db.begin():
        owner = db.get(LearnerGoal, goal["id"]).user_id
        facts = facts_for(db, owner)
        append_fact(
            db,
            owner,
            facts[-1].model_copy(
                update={
                    "event_id": identifier(),
                    "source_id": identifier(),
                    "sequence": len(facts) + 1,
                    "mode": "practice",
                    "hint_level": 0,
                }
            ),
        )
    response = client.get("/api/v1/progress")
    assert response.status_code == 200, response.text
    progress = response.json()
    assert progress["plan"]["needs_refresh"]
    assert progress["today"]["action"] == "resume_session"
    assert progress["today"]["session_id"] == saved["id"]
