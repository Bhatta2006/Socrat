"""Protected assessment authority, failure isolation, review, and cross-cell persistence."""

import itertools

import pytest
from m6_support import SIGNING, WORKER, profiles
from m9_support import assessment_pack, finish, prepared, respond, start
from pydantic import SecretStr, ValidationError
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_execution import claim, queue, result
from test_foundation import login
from test_foundation import platform as platform

from socrat.config import ContentAdminIdentity
from socrat.models import AssessmentResponse
from socrat.skillpacks.schema import SkillPack


@pytest.mark.parametrize(
    "track,language",
    list(itertools.product(["foundations", "interview", "competitive"], ["python", "cpp", "java"])),
)
def test_parallel_forms_nine_cells_exactly_once_and_private_keys(
    platform, monkeypatch, track, language
):
    app, client, headers, goal = prepared(platform, monkeypatch, track, language)
    session = start(client, headers, goal)
    assert "PRIVATE-M9-KEY" not in str(session)
    assert "assessment_forms" not in client.get("/api/v1/skill-packs").text
    assert start(client, headers, goal) == session
    initial = client.get("/api/v1/learner-state/evidence").json()["total"]
    session = respond(client, headers, session)
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial
    session = respond(client, headers, session)
    finished = finish(client, headers, session)
    assert finished["result"]["passed"]
    assert finish(client, headers, session) == finished
    facts = client.get("/api/v1/learner-state/evidence").json()
    assert facts["total"] == initial + 2
    assert all(
        x["mode"] == "assessment" and x["unseen"] and x["hint_level"] == 0 for x in facts["items"]
    )
    final = start(client, headers, goal, "final", "final")
    assert {x["exercise_id"] for x in final["items"]}.isdisjoint(
        {x["exercise_id"] for x in session["items"]}
    )
    with Session(app.state.engine) as db, db.begin():
        with pytest.raises(DBAPIError):
            db.execute(update(AssessmentResponse).values(outcome={}))


def test_ownership_flags_csrf_staleness_and_expired_exposures(platform, monkeypatch):
    app, client, headers, goal = prepared(platform, monkeypatch)
    session = start(client, headers, goal)
    body = dict(
        item_id=session["items"][0]["id"],
        revision=0,
        idempotency_key="one",
        answer="PRIVATE-M9-KEY",
    )
    path = f"/api/v1/assessments/{session['id']}/responses"
    assert client.post(path, json=body, headers={"Origin": headers["Origin"]}).status_code == 403
    first = client.post(path, json=body, headers=headers)
    assert first.status_code == 200
    assert client.post(path, json=body, headers=headers).json() == first.json()
    assert (
        client.post(path, json={**body, "answer": "different"}, headers=headers).status_code == 409
    )
    assert (
        client.post(
            path,
            json={**body, "item_id": session["items"][1]["id"], "idempotency_key": "two"},
            headers=headers,
        ).status_code
        == 409
    )
    app.state.settings.assessments_enabled = False
    assert client.get(f"/api/v1/assessments/{session['id']}").status_code == 404
    app.state.settings.assessments_enabled = True
    monkeypatch.setattr("socrat.assessment.routes.now", lambda: session["deadline_at"])
    assert (
        client.post(
            path, json={**body, "revision": 1, "idempotency_key": "late"}, headers=headers
        ).status_code
        == 409
    )
    assert finish(client, headers, session)["result"]["status"] == "unscored"
    replacement = start(client, headers, goal, key="replacement")
    assert {x["exercise_id"] for x in replacement["items"]}.isdisjoint(
        {x["exercise_id"] for x in session["items"]}
    )
    login(client, "bob")
    assert client.get(f"/api/v1/assessments/{session['id']}").status_code == 404
    assert client.get(f"/api/v1/goals/{goal['id']}/retention").status_code == 404


def test_reported_form_outage_and_atomic_rollback_never_change_mastery(platform, monkeypatch):
    app, client, headers, goal = prepared(platform, monkeypatch)
    session = start(client, headers, goal)
    session = respond(client, headers, session, report_problem=True)
    session = respond(client, headers, session)
    assert finish(client, headers, session)["result"]["reason_code"] == "replacement_form_required"
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == 0
    replacement = start(client, headers, goal, key="replacement")
    replacement = respond(client, headers, replacement)
    replacement = respond(client, headers, replacement)
    from socrat.assessment import service

    original = service.append_fact
    calls = 0

    def fail_second(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic transaction failure")
        return original(*args)

    monkeypatch.setattr(service, "append_fact", fail_second)
    assert (
        client.post(
            f"/api/v1/assessments/{replacement['id']}/complete", headers=headers
        ).status_code
        == 500
    )
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == 0
    monkeypatch.setattr(service, "append_fact", original)
    assert finish(client, headers, replacement)["result"]["passed"]


def test_qualitative_and_disputed_boundary_results_require_independent_review(
    platform, monkeypatch
):
    from socrat.models import now

    fixed_clock = now()
    monkeypatch.setattr("socrat.assessment.routes.now", lambda: fixed_clock)
    app, client, headers, goal = prepared(platform, monkeypatch, qualitative=True)
    session = start(client, headers, goal)
    session = respond(client, headers, session)
    session = respond(
        client, headers, session, answer="My explanation of correctness and complexity."
    )
    session = finish(client, headers, session)
    assert session["status"] == "pending_review"
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == 0
    assert client.get("/api/v1/admin/assessments/reviews").status_code == 403
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="alice"),
        ContentAdminIdentity(issuer="local-development", subject="reviewer"),
    ]
    item = session["items"][1]
    body = dict(
        revision=session["revision"],
        idempotency_key="review",
        decision="accept",
        criterion_scores=dict(correctness=4, complexity=4),
        evidence_reference="private-review-1",
        rationale="Checked the curated criteria.",
    )
    path = f"/api/v1/admin/assessments/items/{item['id']}/review"
    assert client.post(path, headers=headers, json=body).status_code == 403
    login(client, "reviewer")
    reviewer = client.get("/api/v1/me").json()
    review_headers = {**headers, "X-CSRF-Token": reviewer["csrf_token"]}
    assert "My explanation" in client.get("/api/v1/admin/assessments/reviews").text
    assert (
        client.post(
            path,
            headers=review_headers,
            json={**body, "criterion_scores": dict(correctness=5, complexity=4)},
        ).status_code
        == 422
    )
    reviewed = client.post(path, headers=review_headers, json=body)
    assert reviewed.status_code == 200, reviewed.text
    assert client.post(path, headers=review_headers, json=body).json() == reviewed.json()
    login(client, "alice")
    learner_headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    finished = finish(client, learner_headers, reviewed.json())
    assert finished["result"]["passed"]
    disputed = client.post(
        f"/api/v1/assessments/{finished['id']}/items/{item['id']}/dispute",
        headers=learner_headers,
        json=dict(idempotency_key="dispute", rationale="Please check my explanation again."),
    )
    assert disputed.status_code == 200
    login(client, "reviewer")
    review_headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    resolved = client.post(
        path,
        headers=review_headers,
        json=dict(
            revision=disputed.json()["revision"],
            idempotency_key="resolve",
            decision="exclude",
            evidence_reference="private-resolution",
            rationale="Criterion ambiguity confirmed.",
        ),
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["items"][1]["status"] == "excluded"
    assert not resolved.json()["result"]["dispute_pending"]


@pytest.mark.parametrize("scenario", ["healthy", "failed", "boundary"])
def test_signed_code_result_is_staged_and_tutor_is_forbidden(platform, monkeypatch, scenario):
    app, client, headers, goal = prepared(
        platform, monkeypatch, code=True, code_boundary=scenario == "boundary"
    )
    settings = app.state.settings
    settings.execution_enabled = True
    settings.execution_profiles = profiles()
    settings.execution_signing_secret = SecretStr(SIGNING)
    settings.execution_worker_secret = SecretStr(WORKER)
    settings.tutor_enabled = True
    worker = {"Origin": headers["Origin"], "Authorization": "Bearer " + WORKER}
    client.post(
        "/api/v1/execution/worker/heartbeat",
        headers=worker,
        json=dict(worker_id="worker-1", images=[x["image"] for x in profiles()]),
    )
    session = start(client, headers, goal)
    item = session["items"][0]
    created = client.post(
        f"/api/v1/goals/{goal['id']}/code-attempts",
        headers=headers,
        json=dict(
            exercise_id=item["exercise_id"], assessment_item_id=item["id"], idempotency_key="code"
        ),
    )
    assert created.status_code == 200, created.text
    attempt = created.json()
    assert attempt["mode"] == "assessment"
    assert (
        client.post(
            f"/api/v1/attempts/{attempt['id']}/tutor",
            headers=headers,
            json=dict(
                idempotency_key="hint",
                draft_revision=0,
                reasoning="A hint please",
                requested_level=1,
            ),
        ).status_code
        == 403
    )
    assert queue(client, headers, attempt).status_code == 200
    job = claim(client, worker)
    signed = result(job, failed=scenario == "failed")
    if scenario == "boundary":
        from socrat.execution.protocol import sign

        signed["envelope"]["result"]["cases"][-1]["status"] = "wrong_answer"
        signed["envelope"]["signature"] = sign(signed["envelope"]["result"], SIGNING)
    callback = client.post("/api/v1/execution/worker/result", headers=worker, json=signed)
    assert callback.status_code == 200, callback.text
    assert "HIDDEN-INPUT" not in callback.text
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == 0
    session = client.get(f"/api/v1/assessments/{session['id']}").json()
    session = respond(client, headers, session)
    finished = finish(client, headers, session)
    if scenario == "boundary":
        assert finished["status"] == "pending_review" and finished["result"] is None
    else:
        assert finished["result"]["status"] == ("unscored" if scenario == "failed" else "scored")
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == (
        2 if scenario == "healthy" else 0
    )


@pytest.mark.parametrize(
    "mutation", ["parallel_difficulty", "weekly_mixed", "missing_key", "missing_review", "modality"]
)
def test_authoring_rejects_contaminated_or_unscorable_forms(mutation):
    payload = assessment_pack().model_dump()
    form = payload["assessment_forms"][0]
    if mutation == "parallel_difficulty":
        next(x for x in payload["exercises"] if x["id"] == form["items"][0]["exercise_id"])[
            "difficulty"
        ] = 2
    elif mutation == "weekly_mixed":
        weekly = next(x for x in payload["assessment_forms"] if "weekly" in x["blueprint_id"])
        for spec in weekly["items"]:
            spec["unfamiliar_representation"] = False
    elif mutation == "missing_key":
        del form["items"][0]["response"]["answer"]
    elif mutation == "missing_review":
        form["review_reference"] = ""
    else:
        form["items"][0]["response"] = dict(kind="implementation")
    with pytest.raises(ValidationError):
        SkillPack.model_validate(payload)


def test_dispute_is_queued_and_human_exclusion_appends_correction(platform, monkeypatch):
    app, client, headers, goal = prepared(platform, monkeypatch)
    session = start(client, headers, goal)
    session = respond(client, headers, session)
    session = respond(client, headers, session)
    session = finish(client, headers, session)
    item = session["items"][0]
    path = f"/api/v1/assessments/{session['id']}/items/{item['id']}/dispute"
    body = dict(idempotency_key="dispute", rationale="The key appears ambiguous.")
    disputed = client.post(path, headers=headers, json=body)
    assert disputed.status_code == 200, disputed.text
    assert disputed.json()["result"]["dispute_pending"]
    assert client.post(path, headers=headers, json=body).json() == disputed.json()
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="reviewer")
    ]
    login(client, "reviewer")
    review_headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    assert (
        client.get("/api/v1/admin/assessments/reviews").json()["items"][0]["dispute"]
        == body["rationale"]
    )
    review_path = f"/api/v1/admin/assessments/items/{item['id']}/review"
    review_body = dict(
        idempotency_key="resolve",
        revision=disputed.json()["revision"],
        decision="exclude",
        evidence_reference="private-correction",
        rationale="Ambiguity confirmed.",
    )
    corrected = client.post(review_path, headers=review_headers, json=review_body)
    assert corrected.status_code == 200, corrected.text
    assert not corrected.json()["result"]["evidence_current"]
    assert not corrected.json()["result"]["dispute_pending"]
    assert (
        client.post(review_path, headers=review_headers, json=review_body).json()
        == corrected.json()
    )
    login(client, "alice")
    evidence = client.get("/api/v1/learner-state/evidence").json()
    assert evidence["total"] == 3
    assert evidence["items"][-1]["kind"] == "invalidated"


def test_whole_form_boundary_review_is_queued_without_mastery(platform, monkeypatch):
    # One exact success plus one failure gives 0.5. Author a 0.5 pass threshold.
    original = assessment_pack().model_dump()
    for form in original["assessment_forms"]:
        form["pass_score"] = 0.5
    monkeypatch.setattr("m4_support.diagnostic_pack", lambda: SkillPack.model_validate(original))
    from m4_support import accepted

    app, client, headers, goal = accepted(platform)
    app.state.settings.assessments_enabled = True
    session = start(client, headers, goal)
    session = respond(client, headers, session)
    session = respond(client, headers, session, answer="incorrect")
    session = finish(client, headers, session)
    assert session["status"] == "pending_review"
    assert client.get("/api/v1/learner-state/evidence").json()["total"] == 0
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject="reviewer")
    ]
    login(client, "reviewer")
    review_headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    tasks = client.get("/api/v1/admin/assessments/reviews").json()["items"]
    assert len(tasks) == 2
    for task in tasks:
        reviewed = client.post(
            f"/api/v1/admin/assessments/items/{task['item_id']}/review",
            headers=review_headers,
            json=dict(
                revision=session["revision"],
                idempotency_key=task["item_id"],
                decision="accept",
                evidence_reference="private-boundary-review",
                rationale="Objective key verified.",
            ),
        )
        assert reviewed.status_code == 200, reviewed.text
        session = reviewed.json()
    login(client, "alice")
    learner_headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    assert finish(client, learner_headers, session)["result"]["passed"]


def test_seven_day_retention_flow_uses_reviewed_policy_fresh_form_and_quarter_budget(
    platform, monkeypatch
):
    from socrat.learnerstate.policy import POLICIES, digest
    from socrat.learnerstate.projector import EvidenceFact, state_key
    from socrat.learnerstate.service import append_fact, project, promote_policy
    from socrat.models import AssessmentSession, LearnerGoal, SkillPackVersion, identifier

    app, client, headers, goal = prepared(platform, monkeypatch)
    session = start(client, headers, goal)
    session = respond(client, headers, session)
    session = respond(client, headers, session)
    session = finish(client, headers, session)
    stamp = session["result"]["completed_at"]
    with Session(app.state.engine) as db, db.begin():
        record = db.get(AssessmentSession, session["id"])
        saved = db.get(LearnerGoal, goal["id"])
        saved_user_id = saved.user_id
        pack = db.get(SkillPackVersion, record.pack_id)
        root = SkillPack.model_validate(pack.payload).topological_order()[0]
        for index in range(45):
            append_fact(
                db,
                saved.user_id,
                EvidenceFact(
                    event_id=identifier(),
                    user_id=saved.user_id,
                    goal_id=saved.id,
                    track="foundations",
                    sequence=index + 3,
                    source_id=identifier(),
                    pack_id=pack.id,
                    pack_digest=pack.digest,
                    language="python",
                    concept_ids=[root],
                    mode="practice",
                    evidence_type=["implement", "trace", "explain"][index % 3],
                    family_id=f"retention_fixture_{index}",
                    score=1.0,
                    quality=1.0,
                    hint_level=0,
                    valid=True,
                    unseen=True,
                    finalized=True,
                    occurred_at=stamp,
                    scoring_version="synthetic",
                    policy_version="1.0.0",
                    policy_digest=digest(POLICIES["1.0.0"].model_dump()),
                    reason_code="synthetic_practice",
                ),
            )
        shadow = project(db, saved.user_id, "1.1.0", stamp)
        promote_policy(
            db,
            saved.user_id,
            saved.user_id,
            "1.1.0",
            stamp,
            "synthetic-reviewed-replay",
            digest(shadow),
        )
        concept_key = state_key(pack.id, "python", root)
        assert shadow["concepts"][concept_key]["band"] == "provisionally_mastered"
    monkeypatch.setattr("socrat.assessment.routes.now", lambda: stamp + 7 * 86400)
    due = client.get(f"/api/v1/goals/{goal['id']}/retention").json()
    assert len(due["items"]) == 1
    retention = start(client, headers, goal, "retention", "retention")
    assert (
        retention["deadline_at"] - (stamp + 7 * 86400)
        <= goal["goal"]["minutes_per_session"] * 0.25 * 60
    )
    retention = respond(client, headers, retention)
    retention = respond(client, headers, retention)
    assert finish(client, headers, retention)["result"]["passed"]
    with Session(app.state.engine) as db:
        state = project(db, saved_user_id, "1.1.0", stamp + 7 * 86400)["concepts"][concept_key]
        assert state["retention_passed"] and state["band"] == "mastered"
        assert state["review_interval_days"] == 7
        assert state["review_representation"] == "small_implementation"
