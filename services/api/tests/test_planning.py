import itertools

import pytest
from m5_support import completed
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform

from socrat.config import ContentAdminIdentity
from socrat.models import CurriculumRevision, OutboxEvent, SkillPackVersion


def test_recovery_clock_never_accumulates_debt_and_keeps_reduced_workload(platform, monkeypatch):
    from socrat.models import now

    _, client, headers, goal = completed(platform, monkeypatch)
    stamp = now()
    monkeypatch.setattr("socrat.planning.routes.now", lambda: stamp)
    first = send(client, headers, goal).json()
    confirmed = send(
        client, headers, goal, "confirm", 1, "confirm", reviewed_digest=first["review_digest"]
    ).json()
    monkeypatch.setattr("socrat.planning.routes.now", lambda: stamp + 7 * 86400)
    day = next(x for x in first["days"] if x["blocks"])
    assert (
        client.get(f"/api/v1/daily-plan?goal_id={goal['id']}&date={day['date']}").json()["status"]
        == "missed"
    )
    recovered = send(client, headers, goal, "recover", confirmed["revision"], "recover").json()
    assert "missed_days_recalculate_without_backlog" in recovered["reason_codes"]
    assert recovered["controller"]["workload_minutes"] < first["schedule"]["minutes"]
    assert all(x["capacity_minutes"] <= 30 for x in recovered["days"])
    assert recovered["evidence_watermark"] == first["evidence_watermark"]
    stable = send(client, headers, goal, "refresh", recovered["revision"], "stable").json()
    assert stable["controller"]["workload_minutes"] == recovered["controller"]["workload_minutes"]


def test_daily_progress_comes_only_from_owned_valid_independent_evidence(platform, monkeypatch):
    from socrat.learnerstate.projector import EvidenceFact
    from socrat.learnerstate.service import append_fact, facts_for
    from socrat.models import LearnerGoal, identifier, now

    app, client, headers, goal = completed(platform, monkeypatch)
    draft = send(client, headers, goal).json()
    confirmed = send(
        client, headers, goal, "confirm", 1, "confirm", reviewed_digest=draft["review_digest"]
    ).json()
    day = next(x for x in draft["days"] if x["blocks"])
    with Session(app.state.engine) as db, db.begin():
        owner = db.get(LearnerGoal, goal["id"]).user_id
        facts = facts_for(db, owner)
        base = facts[-1]
        exercise_id = next(x for x in day["blocks"] if x["mode"] == "independent")["exercise_ids"][
            0
        ]
        exercise = next(
            x
            for x in db.get(SkillPackVersion, draft["pack_id"]).payload["exercises"]
            if x["id"] == exercise_id
        )
        from datetime import datetime
        from zoneinfo import ZoneInfo

        timestamp = int(
            datetime.fromisoformat(day["date"])
            .replace(hour=12, tzinfo=ZoneInfo(draft["schedule"]["timezone"]))
            .timestamp()
        )
        timestamp = max(timestamp, now()) if day["date"] == draft["start_date"] else timestamp
        # Synthetic noon evidence can be ahead of the real clock after midnight.
        monkeypatch.setattr("socrat.planning.routes.now", lambda: timestamp)
        independent = EvidenceFact.model_validate(
            {
                **base.model_dump(),
                "event_id": identifier(),
                "source_id": identifier(),
                "sequence": len(facts) + 1,
                "mode": "practice",
                "evidence_type": "trace",
                "family_id": exercise["family_id"],
                "concept_ids": exercise["concept_ids"],
                "occurred_at": timestamp,
            }
        )
        append_fact(db, owner, independent)
    path = f"/api/v1/daily-plan?goal_id={goal['id']}&date={day['date']}"
    assert client.get(path).json()["status"] == "in_progress"
    assert (
        client.get(path).json()["actionable"] is False
    )  # Evidence changed: refresh before the next action.
    with Session(app.state.engine) as db, db.begin():
        facts = facts_for(db, owner)
        exit_check = EvidenceFact.model_validate(
            {
                **independent.model_dump(),
                "event_id": identifier(),
                "source_id": identifier(),
                "sequence": len(facts) + 1,
                "evidence_type": "explain",
            }
        )
        append_fact(db, owner, exit_check)
    assert client.get(path).json()["status"] == "completed"
    assert client.get(f"/api/v1/goals/{goal['id']}/curriculum").json()["needs_refresh"]
    assert send(client, headers, goal, "refresh", confirmed["revision"], "fresh").status_code == 200


def send(client, headers, goal, action="generate", revision=0, key="generate", **extra):
    return client.post(
        f"/api/v1/goals/{goal['id']}/curriculum/commands",
        headers=headers,
        json=dict(action=action, expected_revision=revision, idempotency_key=key, **extra),
    )


@pytest.mark.parametrize(
    "track,language",
    list(itertools.product(["foundations", "interview", "competitive"], ["python", "cpp", "java"])),
)
def test_nine_cells_generate_confirm_replay_idempotency_and_pause(
    platform, monkeypatch, track, language
):
    app, client, headers, goal = completed(platform, monkeypatch, track, language)
    response = send(client, headers, goal)
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["status"] == "draft" and len(draft["days"]) == 14
    assert "replay_inputs" not in draft
    assert send(client, headers, goal).json() == draft
    assert send(client, headers, goal, minutes=20).status_code == 409
    confirm = send(
        client,
        headers,
        goal,
        "confirm",
        draft["revision"],
        "confirm",
        reviewed_digest=draft["review_digest"],
    )
    assert confirm.status_code == 200, confirm.text
    confirmed = confirm.json()
    assert confirmed["status"] == "confirmed"
    assert (
        send(client, headers, goal, "pause", confirmed["revision"], "pause").json()["status"]
        == "paused"
    )
    resumed = send(client, headers, goal, "resume", confirmed["revision"] + 1, "resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "draft"
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="alice")
    ]
    replay = client.get(f"/api/v1/admin/planning/revisions/{draft['id']}/replay")
    assert replay.status_code == 200, replay.text
    assert replay.json()["decisions_match"] and replay.json()["snapshot_digest_matches"]
    with Session(app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.kind == "plan.confirmed")
            )
            == 1
        )
        with pytest.raises(DBAPIError):
            db.execute(update(CurriculumRevision).values(snapshot={"tampered": True}))


def test_security_stale_revision_and_content_withdrawal(platform, monkeypatch):
    app, client, headers, goal = completed(platform, monkeypatch)
    assert send(client, {"Origin": headers["Origin"]}, goal).status_code == 403
    draft = send(client, headers, goal).json()
    assert send(client, headers, goal, "refresh", 0, "stale").status_code == 409
    assert send(client, headers, goal, "lighter", 1, "lighter", minutes=20).status_code == 200
    assert client.get(f"/api/v1/daily-plan?goal_id={goal['id']}&date=bad").status_code == 422
    assert (
        client.get(
            f"/api/v1/daily-plan?goal_id={goal['id']}&date={draft['days'][0]['date']}"
        ).status_code
        == 200
    )
    login(client, "bob")
    assert client.get(f"/api/v1/goals/{goal['id']}/curriculum").status_code == 404
    login(client, "alice")
    with Session(app.state.engine) as db, db.begin():
        db.execute(update(SkillPackVersion).values(status="quarantined"))
    assert client.get(f"/api/v1/goals/{goal['id']}/curriculum").status_code == 409
    app.state.settings.planning_enabled = False
    assert client.get(f"/api/v1/goals/{goal['id']}/curriculum").status_code == 404


def test_impossible_target_requires_explicit_revised_schedule(platform, monkeypatch):
    _, client, headers, goal = completed(platform, monkeypatch)
    assert send(client, headers, goal).status_code == 200
    impossible = send(
        client, headers, goal, "recover", 1, "impossible", target_date="2020-01-01"
    ).json()
    assert impossible["feasibility"] == "date_unfeasible"
    assert (
        send(
            client,
            headers,
            goal,
            "confirm",
            2,
            "confirm-bad",
            reviewed_digest=impossible["review_digest"],
        ).status_code
        == 409
    )
    revised = send(
        client, headers, goal, "recover", 2, "revise", target_date="no_fixed_date"
    ).json()
    assert (
        send(
            client,
            headers,
            goal,
            "confirm",
            3,
            "confirm-good",
            reviewed_digest=revised["review_digest"],
        ).status_code
        == 200
    )
