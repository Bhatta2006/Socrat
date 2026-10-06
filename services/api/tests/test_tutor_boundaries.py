import json

import pytest
from m6_support import code_pack
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import platform as platform
from test_tutor import ask, prepared

from socrat.models import DiagnosticSession, TutorArtifact, TutorTurn
from socrat.skillpacks.schema import SkillPack
from socrat.tutor import gateway


def test_authored_scaffold_requires_exit_and_records_learning_only(platform, monkeypatch):
    def authored():
        payload = code_pack().model_dump()
        payload["tutor_hints"] = [
            dict(
                exercise_id="a_runtime_probe",
                language="python",
                level=4,
                message="Read the value, then fill in the missing transformation before printing.",
                question="Which transformation matches the required result?",
            )
        ]
        return SkillPack.model_validate(payload)

    monkeypatch.setattr("m6_support.code_pack", authored)
    app, client, headers, _, _, attempt = prepared(platform, monkeypatch)
    path = f"/api/v1/attempts/{attempt['id']}/tutor"
    body = dict(
        idempotency_key="locked", draft_revision=0, reasoning="I tried a sample", requested_level=4
    )
    assert client.post(path, headers=headers, json=body).json()["granted_level"] == 1
    response = client.post(
        path, headers=headers, json={**body, "idempotency_key": "exit", "action": "exit"}
    )
    assert response.status_code == 200 and response.json()["granted_level"] == 4
    assert "missing transformation" in response.json()["response"]["message"]
    assert response.json()["fresh_task_required"]
    with Session(app.state.engine) as db, db.begin():
        db.delete(db.get(TutorArtifact, response.json()["id"]))
    history = client.get(path).json()
    assert history["assistance_level"] == 4 and history["items"][-1]["response"] is None
    with Session(app.state.engine) as db:
        assert len(list(db.scalars(select(TutorTurn)))) == 2


def test_active_diagnostic_blocks_other_practice_hint_history(platform, monkeypatch):
    app, client, headers, _, goal, attempt = prepared(platform, monkeypatch)
    assert ask(client, headers, attempt).status_code == 200
    with Session(app.state.engine) as db, db.begin():
        diagnostic = db.scalar(
            select(DiagnosticSession).where(DiagnosticSession.goal_id == goal["id"])
        )
        diagnostic.status = "in_progress"
        diagnostic.deadline_at = 4_000_000_000
    monkeypatch.setattr(
        gateway, "generate", lambda *a, **k: pytest.fail("Assessment called provider")
    )
    assert ask(client, headers, attempt).status_code == 403
    assert client.get(f"/api/v1/attempts/{attempt['id']}/tutor").status_code == 403


def test_stale_draft_and_zero_rollout_never_call_provider(platform, monkeypatch):
    app, client, headers, _, _, attempt = prepared(platform, monkeypatch)
    stale = ask(client, headers, {**attempt, "revision": 10})
    assert stale.status_code == 409 and "code_draft_stale" in stale.text
    settings = app.state.settings
    settings.tutor_model_enabled = True
    settings.tutor_model_rollout_percent = 0
    monkeypatch.setattr(
        gateway, "transport", lambda *a, **k: pytest.fail("Zero rollout called provider")
    )
    assert ask(client, headers, attempt).json()["fallback"]
    with Session(app.state.engine) as db:
        turn = db.scalar(select(TutorTurn))
        assert turn.telemetry["reason"] == "rollout_hold"
        assert turn.telemetry["reserved_microusd"] == 0


def test_authored_hints_cannot_target_protected_or_unknown_inventory():
    payload = code_pack().model_dump()
    protected = next(x for x in payload["exercises"] if x["inventory"] == "assessment")
    payload["tutor_hints"] = [
        dict(
            exercise_id=protected["id"],
            language="python",
            level=1,
            message="A hint",
            question="A question?",
        )
    ]
    with pytest.raises(ValueError):
        SkillPack.model_validate(payload)
    payload["tutor_hints"][0]["exercise_id"] = "a_runtime_probe"
    payload["tutor_hints"] *= 2
    with pytest.raises(ValueError):
        SkillPack.model_validate(payload)
    payload["tutor_hints"] = []
    pack = SkillPack.model_validate(payload)
    assert "tutor_hints" not in json.loads(pack.canonical_json())


@pytest.mark.parametrize("reason", ["provider_timeout", "provider_http_401", "provider_http_429"])
def test_repeated_provider_failures_queue_review(platform, monkeypatch, reason):
    _, client, headers, _, _, attempt = prepared(platform, monkeypatch)
    monkeypatch.setattr(gateway, "generate", lambda *a, **k: gateway.GatewayResult(None, reason))
    first = ask(client, headers, attempt).json()
    second = client.post(
        f"/api/v1/attempts/{attempt['id']}/tutor",
        headers=headers,
        json=dict(
            idempotency_key="second",
            draft_revision=attempt["revision"],
            reasoning="I will trace the given sample first",
            requested_level=1,
        ),
    ).json()
    assert first["fallback"] and not first["review_required"]
    assert second["fallback"] and second["review_required"]
