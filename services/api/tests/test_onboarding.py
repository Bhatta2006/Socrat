import itertools
import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform

from socrat.config import ContentAdminIdentity
from socrat.models import LearnerGoal, OutboxEvent, SkillPackHead, SkillPackVersion, User
from socrat.onboarding.policy import OUTCOMES, GoalInput, route
from socrat.skillpacks.schema import SkillPack


def goal(track="foundations", **changes):
    value = dict(
        goal_template_id=track,
        language="python",
        target_outcome=sorted(OUTCOMES[track])[0],
        target_date="no_fixed_date",
        days_per_week=4,
        minutes_per_session=30,
        timezone="Asia/Kolkata",
        language_experience="none",
        dsa_experience="never",
        role_level="new_grad" if track == "interview" else None,
        platform_or_format="codeforces" if track == "competitive" else None,
        target_value="released_novice_band" if track == "competitive" else None,
    )
    return GoalInput.model_validate({**value, **changes})


def pack():
    source = next(Path("contracts/fixtures/skill-packs").glob("*dsa*1.0.0*.json"))
    data = json.loads(source.read_text(encoding="utf-8"))
    data["purpose"] = "launch"
    for template in data["goals"]:
        value = goal(template["id"])
        template["released_targets"] = [
            dict(
                outcome=value.target_outcome,
                value=value.target_value,
                role_level=value.role_level,
                platform_or_format=value.platform_or_format,
            )
        ]
    return SkillPack.model_validate(data)


def test_decision_table_all_combinations():
    content = pack()
    for track, adult, language, days, minutes, experience in itertools.product(
        OUTCOMES,
        [True, False],
        ["python", "cpp", "java", "javascript"],
        [2, 3, 7],
        [10, 20, 90],
        ["none", "syntax_only", "solved_problems", "professional"],
    ):
        value = goal(
            track,
            language=language,
            days_per_week=days,
            minutes_per_session=minutes,
            language_experience=experience,
        )
        actual = route(value, adult, [content], date(2026, 10, 2))
        assert actual == route(value, adult, [content], date(2026, 10, 2))
        if not adult:
            assert actual["reason_codes"] == ["adult_confirmation_required"]
        elif language == "javascript":
            assert actual["reason_codes"] == ["unsupported_language"]
        elif days < 3 or minutes < 20:
            assert actual["reason_codes"] == ["minimum_practice_commitment_not_met"]
        elif track != "foundations" and experience in {"none", "syntax_only"}:
            assert actual["routing_outcome"] == "accept_with_foundations_bridge"
            assert actual["active_track"] == "foundations"
            assert actual["declared_track"] == track
        else:
            assert actual["routing_outcome"].startswith("accept_")
        assert "mastery" not in actual


def test_missing_coverage_and_variants_fail_closed():
    content = pack()
    today = date(2026, 10, 2)
    assert route(goal(), True, [], today)["reason_codes"] == ["goal_coverage_not_released"]
    assert route(goal("competitive", target_value="9999"), True, [content], today)[
        "reason_codes"
    ] == ["competitive_target_not_released"]
    fixture = content.model_copy(deep=True)
    fixture.purpose = "fixture"
    assert route(goal(), True, [fixture], today)["routing_outcome"] == "waitlist"
    no_bridge = content.model_copy(deep=True)
    next(g for g in no_bridge.goals if g.id == "foundations").released_targets = []
    assert route(goal("interview"), True, [no_bridge], today)["reason_codes"] == [
        "foundations_bridge_not_released"
    ]
    missing_variant = content.model_copy(deep=True)
    for item in missing_variant.exercises:
        item.variants = [v for v in item.variants if v.language != "python"]
    assert route(goal(), True, [missing_variant], today)["routing_outcome"] == "waitlist"


@pytest.mark.parametrize(
    "changes",
    [
        {"timezone": "Mars/City"},
        {"target_date": "tomorrow"},
        {"target_date": "20261002"},
        {"target_outcome": "get_a_job"},
        {"role_level": "intern"},
        {"days_per_week": True},
        {"language_experience": "unknown"},
        {"minutes_per_session": 15},
    ],
)
def test_invalid_inputs(changes):
    with pytest.raises(ValidationError):
        goal(**changes)


def test_missing_track_fields_and_feasibility():
    for value in [goal("interview").model_dump(), goal("competitive").model_dump()]:
        value["role_level"] = None
        value["platform_or_format"] = None
        with pytest.raises(ValidationError):
            GoalInput.model_validate(value)
    for target in ["2026-10-01", "2026-10-02"]:
        assert route(goal(target_date=target), True, [pack()], date(2026, 10, 2))["warnings"] == [
            "target_date_feasibility_warning"
        ]
    assert (
        route(goal(target_date="2030-10-02"), True, [pack()], date(2026, 10, 2))["warnings"] == []
    )


def prepare(platform, adult=True):
    app, client = platform
    app.state.settings.onboarding_enabled = True
    login(client)
    profile = client.get("/api/v1/me").json()
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": profile["csrf_token"]}
    client.patch(
        "/api/v1/me",
        headers=headers,
        json={"display_name": "Learner", "timezone": "Asia/Kolkata", "adult_confirmed": adult},
    )
    return app, client, headers


def test_preview_confirmation_reload_idempotency_and_reconciliation(platform):
    app, client, headers = prepare(platform)
    value = goal().model_dump()
    preview = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    assert preview["routing_outcome"] == "waitlist"
    body = dict(
        goal=value,
        review_digest=preview["review_digest"],
        reviewed=True,
        idempotency_key="retry-key",
    )
    saved = client.post("/api/v1/onboarding/confirm", json=body, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["confirmation_at"]
    assert (
        client.post("/api/v1/onboarding/confirm", json=body, headers=headers).json() == saved.json()
    )
    assert client.get("/api/v1/onboarding/goals").json()["items"] == [saved.json()]
    body["goal"]["days_per_week"] = 5
    assert client.post("/api/v1/onboarding/confirm", json=body, headers=headers).status_code == 409
    with Session(app.state.engine) as db:
        goals = db.scalars(select(LearnerGoal)).all()
        for kind in ["goal.created", "route.confirmed"]:
            events = db.scalars(select(OutboxEvent).where(OutboxEvent.kind == kind)).all()
            assert {event.payload["resource_id"] for event in events} == {item.id for item in goals}
            assert len(events) == len(goals) == 1
    login(client, "bob")
    assert client.get("/api/v1/onboarding/goals").json() == {"items": []}


def test_review_auth_csrf_flag_and_stale_profile(platform):
    app, client = platform
    assert client.get("/api/v1/onboarding/goals").status_code == 404
    app.state.settings.onboarding_enabled = True
    assert client.get("/api/v1/onboarding/goals").status_code == 401
    app, client, headers = prepare(platform)
    value = goal().model_dump()
    assert (
        client.post(
            "/api/v1/onboarding/preview", json=value, headers={"Origin": "http://localhost:3000"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/onboarding/preview",
            json=value,
            headers={**headers, "Origin": "https://evil.test"},
        ).status_code
        == 403
    )
    review = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    body = dict(
        goal=value, review_digest=review["review_digest"], reviewed=False, idempotency_key="key"
    )
    assert client.post("/api/v1/onboarding/confirm", json=body, headers=headers).status_code == 422
    client.patch(
        "/api/v1/me",
        headers=headers,
        json={"display_name": "Learner", "timezone": "UTC", "adult_confirmed": False},
    )
    body["reviewed"] = True
    assert (
        client.post("/api/v1/onboarding/confirm", json=body, headers=headers).json()["error"][
            "code"
        ]
        == "goal_review_stale"
    )
    review = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    body["review_digest"] = review["review_digest"]
    assert client.post("/api/v1/onboarding/confirm", json=body, headers=headers).status_code == 422


def test_active_release_changes_invalidate_preview(platform):
    app, client, headers = prepare(platform)
    value = goal("interview").model_dump()
    original = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    with Session(app.state.engine) as db, db.begin():
        user = db.scalar(select(User))
        content = pack()
        record = SkillPackVersion(
            pack_key=content.key,
            version=content.version,
            domain=content.domain,
            payload=json.loads(content.canonical_json()),
            digest=content.digest(),
            status="released",
            author_id=user.id,
        )
        db.add(record)
        db.flush()
        db.add(SkillPackHead(pack_key=content.key, active_id=record.id))
    body = dict(
        goal=value,
        review_digest=original["review_digest"],
        reviewed=True,
        idempotency_key="release-key",
    )
    assert client.post("/api/v1/onboarding/confirm", json=body, headers=headers).status_code == 409
    revised = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    assert revised["routing_outcome"] == "accept_with_foundations_bridge"
    body["review_digest"] = revised["review_digest"]
    assert client.post("/api/v1/onboarding/confirm", json=body, headers=headers).status_code == 200


def test_pre_m3_digest_is_compatible():
    source = next(Path("contracts/fixtures/skill-packs").glob("*dsa*1.0.0*.json"))
    payload = json.loads(source.read_text(encoding="utf-8"))
    model = SkillPack.model_validate(payload)
    assert all(
        "released_targets" not in item for item in json.loads(model.canonical_json())["goals"]
    )


def test_admin_reconciliation_detects_missing_duplicate_and_orphan_events(platform):
    app, client, headers = prepare(platform)
    assert client.get("/api/v1/onboarding/reconciliation").status_code == 403
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="alice")
    ]
    initial = client.get("/api/v1/onboarding/reconciliation").json()
    assert initial["items"]["goal.created"]["reconciliation_ratio"] is None
    value = goal().model_dump()
    preview = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    client.post(
        "/api/v1/onboarding/confirm",
        headers=headers,
        json=dict(
            goal=value,
            review_digest=preview["review_digest"],
            reviewed=True,
            idempotency_key="analytics",
        ),
    )
    healthy = client.get("/api/v1/onboarding/reconciliation").json()
    assert all(item["reconciliation_ratio"] == 1 for item in healthy["items"].values())
    with Session(app.state.engine) as db, db.begin():
        existing = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == "goal.created"))
        db.add(OutboxEvent(kind="goal.created", payload=existing.payload))
        missing = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == "route.confirmed"))
        db.delete(missing)
        db.add(OutboxEvent(kind="route.confirmed", payload={"resource_id": "unknown"}))
    broken = client.get("/api/v1/onboarding/reconciliation").json()
    assert all(item["reconciliation_ratio"] == 0 for item in broken["items"].values())


def test_malformed_onboarding_requires_confirmation(platform):
    _, client, headers = prepare(platform)
    response = client.post("/api/v1/onboarding/preview", headers=headers, json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "input_confirmation_required"


def test_dsa_self_report_changes_check_not_mastery():
    content = pack()
    beginner = route(
        goal(language_experience="professional", dsa_experience="never"),
        True,
        [content],
        date(2026, 10, 2),
    )
    experienced = route(
        goal(language_experience="professional", dsa_experience="comfortable"),
        True,
        [content],
        date(2026, 10, 2),
    )
    assert beginner["first_diagnostic_stage"] == "dsa_trace_and_reasoning"
    assert experienced["first_diagnostic_stage"] == "implementation_diagnostic"
    assert beginner["routing_outcome"] == experienced["routing_outcome"]


def test_failed_confirmation_rolls_back_goal_and_both_events(platform, monkeypatch):
    import socrat.onboarding.routes as routes

    app, client, headers = prepare(platform)
    value = goal().model_dump()
    preview = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    actual = routes.record_event

    def fail_second_event(db, actor_id, kind, resource_id):
        if kind == "route.confirmed":
            raise RuntimeError("Synthetic outbox failure")
        actual(db, actor_id, kind, resource_id)

    monkeypatch.setattr(routes, "record_event", fail_second_event)
    response = client.post(
        "/api/v1/onboarding/confirm",
        headers=headers,
        json=dict(
            goal=value,
            review_digest=preview["review_digest"],
            reviewed=True,
            idempotency_key="failed-write",
        ),
    )
    assert response.status_code == 500
    with Session(app.state.engine) as db:
        assert db.scalar(select(LearnerGoal)) is None
        assert (
            db.scalar(
                select(OutboxEvent).where(OutboxEvent.kind.in_(["goal.created", "route.confirmed"]))
            )
            is None
        )
