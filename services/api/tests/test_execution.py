import itertools

import pytest
from m6_support import SIGNING, setup
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform

from socrat.execution.protocol import ExecutionResult, JobEnvelope, sign
from socrat.models import CodeRun, LearningEvidence


def start(client, headers, goal):
    response = client.post(
        f"/api/v1/goals/{goal['id']}/code-attempts",
        headers=headers,
        json=dict(exercise_id="a_runtime_probe", idempotency_key="first"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def queue(client, headers, attempt, mode="submit", key="first", **changes):
    return client.post(
        f"/api/v1/attempts/{attempt['id']}/{mode}",
        headers=headers,
        json={"idempotency_key": key, "draft_revision": attempt["revision"], **changes},
    )


def claim(client, worker):
    response = client.post(
        "/api/v1/execution/worker/claim", headers=worker, json=dict(worker_id="worker-1")
    )
    assert response.status_code == 200, response.text
    return JobEnvelope.model_validate(response.json()["job"])


def result(job, failed=False, status="passed"):
    base = {
        key: job.manifest.model_dump()[key]
        for key in ("job_id", "nonce", "code_hash", "test_digest", "image")
    }
    payload = ExecutionResult.model_validate(
        dict(
            **base,
            operational_status="failed" if failed else "healthy",
            reason_code="worker_failure" if failed else "execution_finalized",
            cases=[]
            if failed
            else [
                dict(
                    index=index,
                    status=status,
                    wall_ms=10,
                    stdout="4" if test.visibility == "public" else "HIDDEN-INPUT-718",
                    stderr="",
                )
                for index, test in enumerate(job.tests)
            ],
        )
    ).model_dump()
    return dict(
        worker_id="worker-1", envelope=dict(result=payload, signature=sign(payload, SIGNING))
    )


@pytest.mark.parametrize(
    "track,language",
    list(itertools.product(["foundations", "interview", "competitive"], ["python", "cpp", "java"])),
)
def test_nine_cells_drafts_runs_submits_signature_secrecy_and_exactly_once(
    platform, monkeypatch, track, language
):
    app, client, headers, worker, goal = setup(platform, monkeypatch, track, language)
    attempt = start(client, headers, goal)
    assert "1436" not in str(attempt) and "reference_solution" not in str(attempt)
    source = "\n" + attempt["source"] + "\n"
    saved = client.patch(
        f"/api/v1/attempts/{attempt['id']}/draft",
        headers=headers,
        json=dict(source=source, expected_revision=0),
    )
    assert saved.status_code == 200
    assert client.get(f"/api/v1/attempts/{attempt['id']}").json()["source"] == source
    assert (
        client.patch(
            f"/api/v1/attempts/{attempt['id']}/draft",
            headers=headers,
            json=dict(source=source, expected_revision=0),
        ).json()
        == saved.json()
    )
    attempt["revision"] = 1
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    sample = queue(client, headers, attempt, "runs", key="sample", stdin=" 3\n")
    assert sample.status_code == 200, sample.text
    job = claim(client, worker)
    job.authenticate(SIGNING, job.manifest.issued_at)
    assert job.source == source and job.tests[0].input == " 3\n"
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=result(job)).status_code
        == 200
    )
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial
    submit = queue(client, headers, attempt)
    assert submit.status_code == 200, submit.text
    assert queue(client, headers, attempt).json() == submit.json()
    job = claim(client, worker)
    signed = result(job)
    finalized = client.post("/api/v1/execution/worker/result", headers=worker, json=signed)
    assert finalized.status_code == 200, finalized.text
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=signed).json()
        == finalized.json()
    )
    assert "HIDDEN-INPUT" not in finalized.text
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial + 1
    assert queue(client, headers, attempt, key="different").status_code == 409
    with Session(app.state.engine) as db:
        stored = db.get(CodeRun, job.manifest.job_id)
        assert "HIDDEN-INPUT" not in str(stored.result)
        assert (
            db.scalar(
                select(func.count())
                .select_from(LearningEvidence)
                .where(LearningEvidence.source_id == attempt["id"])
            )
            == 1
        )
        with pytest.raises(DBAPIError):
            db.execute(update(CodeRun).where(CodeRun.id == stored.id).values(manifest={}))


def test_broker_failures_forgery_ownership_and_quota_have_no_evidence(platform, monkeypatch):
    app, client, headers, worker, goal = setup(platform, monkeypatch)
    attempt = start(client, headers, goal)
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    assert queue(client, {"Origin": headers["Origin"]}, attempt).status_code == 403
    assert queue(client, headers, attempt, draft_revision=3).status_code == 409
    assert queue(client, headers, attempt, stdin="custom").status_code == 422
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    forged = result(job)
    forged["envelope"]["result"]["nonce"] = "0" * 64
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=forged).status_code
        == 409
    )
    failed = result(job, failed=True)
    assert (
        client.post("/api/v1/execution/worker/result", headers=worker, json=failed).json()["status"]
        == "failed"
    )
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial
    app.state.settings.execution_daily_quota = 1
    assert queue(client, headers, attempt, key="quota").status_code == 429
    login(client, "bob")
    assert client.get(f"/api/v1/attempts/{attempt['id']}").status_code == 404


def test_empty_draft_is_saved_and_cannot_run_previous_source(platform, monkeypatch):
    _, client, headers, _, goal = setup(platform, monkeypatch)
    attempt = start(client, headers, goal)
    response = client.patch(
        f"/api/v1/attempts/{attempt['id']}/draft",
        headers=headers,
        json=dict(source="", expected_revision=0),
    )
    assert response.status_code == 200
    assert client.get(f"/api/v1/attempts/{attempt['id']}").json()["source"] == ""
    attempt["revision"] = 1
    assert queue(client, headers, attempt, "runs").status_code == 422


@pytest.mark.parametrize("expired", [False, True])
def test_diagnostic_implementation_advances_only_with_current_verified_result(
    platform, monkeypatch, expired
):
    from m4_support import accepted, submit
    from m6_support import WORKER, code_pack, profiles
    from pydantic import SecretStr

    from socrat.models import DiagnosticSession, now
    from socrat.skillpacks.schema import SkillPack

    payload = code_pack().model_dump()
    probe = next(x for x in payload["exercises"] if x["id"] == "a_runtime_probe")
    probe["inventory"] = "assessment"
    for blueprint in payload["blueprints"]:
        blueprint["exercise_ids"].append(probe["id"])
    for definition in payload["diagnostics"]:
        definition["scope"] = "full_placement"
        definition["maximum_items"] += 1
        definition["items"].append(
            dict(
                exercise_id=probe["id"],
                stage="implementation_diagnostic",
                languages=["python", "cpp", "java"],
                response=dict(kind="implementation"),
            )
        )
    monkeypatch.setattr("m4_support.diagnostic_pack", lambda: SkillPack.model_validate(payload))
    app, client, headers, goal = accepted(platform)
    settings = app.state.settings
    settings.execution_enabled = True
    settings.execution_signing_secret = SecretStr(SIGNING)
    settings.execution_worker_secret = SecretStr(WORKER)
    settings.execution_profiles = profiles()
    worker = {"Origin": headers["Origin"], "Authorization": "Bearer " + WORKER}
    assert (
        client.post(
            "/api/v1/execution/worker/heartbeat",
            headers=worker,
            json=dict(worker_id="worker-1", images=[x["image"] for x in profiles()]),
        ).status_code
        == 200
    )
    diagnostic = client.post(
        f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers, json={}
    ).json()
    for _ in range(100):
        assert diagnostic["item"], diagnostic
        if diagnostic["item"]["kind"] == "implementation":
            break
        diagnostic = submit(client, headers, diagnostic).json()
    else:
        pytest.fail("Healthy runtime never selected implementation item")
    assert submit(client, headers, diagnostic).status_code == 422
    attempt = client.post(
        f"/api/v1/goals/{goal['id']}/code-attempts",
        headers=headers,
        json=dict(
            exercise_id=probe["id"],
            idempotency_key="diagnostic-code",
            diagnostic_attempt_id=diagnostic["item"]["attempt_id"],
        ),
    ).json()
    assert "id" in attempt, attempt
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    if expired:
        with Session(app.state.engine) as db, db.begin():
            db.get(DiagnosticSession, diagnostic["id"]).deadline_at = now() - 1
    callback = client.post("/api/v1/execution/worker/result", headers=worker, json=result(job))
    assert callback.status_code == 200, callback.text
    assert callback.json()["status"] == ("failed" if expired else "completed")
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial + (not expired)
    if not expired:
        resumed = client.get(f"/api/v1/diagnostics/{diagnostic['id']}").json()
        assert resumed["answered"] == diagnostic["answered"] + 1
    app.state.settings.execution_enabled = False
    assert client.get(f"/api/v1/attempts/{attempt['id']}").status_code == 404
