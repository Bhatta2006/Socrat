"""M4 API, replay, ownership, publication and transaction acceptance."""

import itertools
import json
from pathlib import Path

import pytest
from m4_support import accepted, diagnostic_pack, submit
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform

from socrat.config import ContentAdminIdentity
from socrat.learnerstate.policy import POLICIES
from socrat.learnerstate.projector import EvidenceFact
from socrat.models import (
    DiagnosticResponse,
    DiagnosticSession,
    LearningEvidence,
    MasteryEvent,
    SkillPackVersion,
)


@pytest.mark.parametrize(
    "track,language",
    list(itertools.product(["foundations", "interview", "competitive"], ["python", "cpp", "java"])),
)
def test_nine_cell_diagnostic_resume_replay_and_results(platform, track, language):
    app, client, headers, goal = accepted(platform, track, language, "professional")
    path = f"/api/v1/goals/{goal['id']}/diagnostics"
    session = client.post(path, headers=headers).json()
    assert session["item"]
    assert client.post(path, headers=headers).json()["id"] == session["id"]
    assert client.get(f"/api/v1/diagnostics/{session['id']}/next").json()["item"] == session["item"]
    assert '"answer":' not in json.dumps(session) and "reference_solution" not in json.dumps(
        session
    )
    assert (
        client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers).status_code
        == 409
    )
    while session["item"]:
        old = session
        response = submit(client, headers, old)
        assert response.status_code == 200, response.text
        session = response.json()
        retry = submit(client, headers, old).json()
        assert {key: value for key, value in retry.items() if key != "server_time"} == {
            key: value for key, value in session.items() if key != "server_time"
        }
    result = client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers)
    assert result.status_code == 200
    assert result.json()["placement_sufficient"] is True
    assert result.json()["full_placement"] is False
    assert result.json()["missing_evidence"] == ["implementation_not_verified"]
    assert all(state["band"] != "mastered" for state in result.json()["concepts"].values())
    assert client.get(f"/api/v1/diagnostics/{session['id']}/result").json() == result.json()
    assert (
        client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers).json()
        == result.json()
    )
    app.state.settings.diagnostics_enabled = False
    assert client.get(f"/api/v1/diagnostics/{session['id']}").status_code == 200
    assert client.post(path, headers=headers).status_code == 404
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(LearningEvidence)) == session["answered"]


def test_bridge_and_private_resources(platform):
    app, client, headers, goal = accepted(platform, "interview")
    session = client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers).json()
    assert session["active_track"] == "foundations" and session["declared_track"] == "interview"
    assert submit(client, headers, session, "unknown").status_code == 422
    assert submit(client, {"Origin": "http://localhost:3000"}, session).status_code == 403
    assert submit(client, {**headers, "Origin": "https://evil.test"}, session).status_code == 403
    submitted = submit(client, headers, session)
    assert submitted.status_code == 200
    assert submit(client, headers, session, "three").status_code == 409
    login(client, "bob")
    assert client.get(f"/api/v1/diagnostics/{session['id']}").status_code == 404
    assert client.get(f"/api/v1/goals/{goal['id']}/diagnostics").status_code == 404
    assert client.get("/api/v1/learner-state/evidence").json()["items"] == []
    assert client.get("/api/v1/admin/diagnostics/calibration").status_code == 403


def test_failed_score_rolls_back_every_effect(platform, monkeypatch):
    import socrat.learnerstate.service as service

    app, client, headers, goal = accepted(platform)
    session = client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers).json()

    def failed(*args):
        raise RuntimeError("Synthetic outbox failure")

    monkeypatch.setattr(service, "record_event", failed)
    assert submit(client, headers, session).status_code == 500
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(DiagnosticResponse)) == 0
        assert db.scalar(select(func.count()).select_from(LearningEvidence)) == 0
        assert db.scalar(select(func.count()).select_from(MasteryEvent)) == 0
    assert client.get(f"/api/v1/diagnostics/{session['id']}").json()["revision"] == 0


def test_withdrawal_zero_evidence_and_immutable_facts(platform):
    app, client, headers, goal = accepted(platform)
    session = client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers).json()
    with Session(app.state.engine) as db, db.begin():
        pack = db.scalar(select(SkillPackVersion))
        pack.status = "quarantined"
    assert client.get(f"/api/v1/diagnostics/{session['id']}").json()["item"] is None
    response = submit(client, headers, session)
    assert response.status_code == 200
    assert response.json()["status"] == "blocked_content"
    with Session(app.state.engine) as db:
        evidence = db.scalar(select(LearningEvidence))
        assert evidence.payload["quality"] == 0 and evidence.payload["valid"] is False
        assert db.scalar(select(func.count()).select_from(MasteryEvent)) == 0
        with pytest.raises(DBAPIError):
            db.execute(update(LearningEvidence).values(payload={}))
        db.rollback()
    result = client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers).json()
    assert result["placement_sufficient"] is False


def test_content_report_replacement_and_expiry(platform):
    app, client, headers, goal = accepted(platform)
    session = client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers).json()
    after = submit(client, headers, session, report_problem=True).json()
    assert after["item"]["attempt_id"] != session["item"]["attempt_id"]
    evidence = client.get("/api/v1/learner-state/evidence").json()["items"]
    assert evidence[0]["quality"] == 0
    with Session(app.state.engine) as db, db.begin():
        record = db.get(DiagnosticSession, session["id"])
        record.deadline_at = 1
    assert client.get(f"/api/v1/diagnostics/{session['id']}").json()["status"] == "expired"
    assert submit(client, headers, after).status_code == 409
    assert (
        client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers).json()[
            "placement_sufficient"
        ]
        is False
    )


def test_admin_correction_shadow_promotion_and_rollback(platform):
    app, client, headers, goal = accepted(platform)
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="alice")
    ]
    user_id = client.get("/api/v1/me").json()["id"]
    session = client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers).json()
    while session["item"]:
        session = submit(client, headers, session).json()
    client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers)
    before = client.get("/api/v1/learner-state").json()
    path = f"/api/v1/admin/learner-state/{user_id}"
    for version in ["1.0.1", "1.0.0"]:
        body = dict(policy_version=version, as_of=before["as_of"])
        preview = client.post(f"{path}/replay", headers=headers, json=body).json()
        assert (
            client.post(
                f"{path}/policy",
                headers=headers,
                json={
                    **body,
                    "projection_digest": "0" * 64,
                    "evidence_reference": "synthetic-review",
                },
            ).status_code
            == 409
        )
        response = client.post(
            f"{path}/policy",
            headers=headers,
            json={
                **body,
                "projection_digest": preview["projection_digest"],
                "evidence_reference": "synthetic-review",
            },
        )
        assert response.status_code == 200, response.text
    assert response.json() == before
    event_id = client.get("/api/v1/learner-state/evidence").json()["items"][0]["event_id"]
    correction = client.post(
        f"{path}/corrections",
        headers=headers,
        json=dict(event_id=event_id, evidence_reference="synthetic-incident"),
    )
    assert correction.status_code == 200, correction.text
    assert correction.json()["affected_diagnostic_ids"] == [session["id"]]
    assert client.post(
        f"{path}/corrections",
        headers=headers,
        json=dict(event_id=event_id, evidence_reference="synthetic-incident"),
    ).json()["already_corrected"]
    assert client.get("/api/v1/learner-state").json()["watermark"] == before["watermark"] + 1
    repaired_result = client.get(f"/api/v1/diagnostics/{session['id']}/result").json()
    assert (
        repaired_result["evidence_current"] is False
        and repaired_result["placement_sufficient"] is False
    )
    assert (
        client.get("/api/v1/admin/diagnostics/calibration").json()["items"][0]["calibration"]
        == "insufficient_data"
    )


def test_contract_artifacts_and_non_dsa():
    assert diagnostic_pack("writing").diagnostics
    policies = json.loads(
        Path("contracts/product/m4-learning-policies.json").read_text(encoding="utf-8")
    )
    assert policies["policies"] == {
        version: policy.model_dump() for version, policy in POLICIES.items()
    }
    assert (
        json.loads(
            Path("contracts/schemas/learning-evidence.schema.json").read_text(encoding="utf-8")
        )
        == EvidenceFact.model_json_schema()
    )


def test_diagnostic_metrics_are_private_and_use_bounded_labels(platform):
    from pydantic import SecretStr

    app, client, headers, goal = accepted(platform)
    client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers)
    app.state.settings.metrics_token = SecretStr("synthetic-m4-metrics-only")
    assert client.get("/api/metrics").status_code == 404
    response = client.get(
        "/api/metrics", headers={"Authorization": "Bearer synthetic-m4-metrics-only"}
    )
    assert response.status_code == 200
    assert (
        'socrat_diagnostic_sessions{language="python",status="in_progress",track="foundations"} 1.0'
        in response.text
    )
    assert goal["id"] not in response.text
