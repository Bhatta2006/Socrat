"""Authored diagnostic scope, unavailable adapters and calibration exclusions."""

import copy

import pytest
from m4_support import accepted, diagnostic_pack, submit
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import platform as platform
from test_onboarding import goal, prepare

from socrat.diagnostics.calibration import outcome_pairs, summarize
from socrat.diagnostics.contracts import ResponseSpec
from socrat.learnerstate.projector import state_key
from socrat.models import DiagnosticAnswer, SkillPackVersion
from socrat.skillpacks.schema import SkillPack


@pytest.mark.parametrize(
    "changes",
    [
        {"answer": "unknown"},
        {"choices": [{"id": "a", "label": "A"}]},
        {"misconception_answers": {"unknown": "boundary"}},
        {"kind": "trace"},
        {"kind": "human_rubric"},
    ],
)
def test_response_specs_fail_closed(changes):
    body = dict(
        kind="choice", choices=[dict(id="a", label="A"), dict(id="b", label="B")], answer="a"
    )
    with pytest.raises(ValidationError):
        ResponseSpec.model_validate({**body, **changes})


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_concept",
        "missing_language",
        "unknown_misconception",
        "wrong_modality",
        "item_mismatch",
        "time_budget",
        "protected_family",
    ],
)
def test_diagnostic_authoring_rejects_unsafe_contract(mutation):
    payload = diagnostic_pack().model_dump()
    definition = payload["diagnostics"][0]
    if mutation == "unknown_concept":
        payload["misconception_taxonomy"][0]["repair_concept_id"] = "unknown"
    elif mutation == "missing_language":
        definition["languages"] = []
    elif mutation == "unknown_misconception":
        definition["items"][0]["response"]["misconception_answers"] = {"three": "unknown"}
    elif mutation == "wrong_modality":
        definition["items"][0]["response"] = dict(kind="implementation")
    elif mutation == "item_mismatch":
        definition["items"].pop()
    elif mutation == "time_budget":
        definition["maximum_seconds"] = 1000
    else:
        blueprint = copy.deepcopy(payload["blueprints"][0])
        blueprint.update(id="protected_final", kind="final")
        payload["blueprints"].append(blueprint)
    with pytest.raises(ValidationError):
        SkillPack.model_validate(payload)


def test_waitlist_cannot_start_diagnostic(platform):
    app, client, headers = prepare(platform)
    app.state.settings.diagnostics_enabled = True
    value = goal().model_dump()
    preview = client.post("/api/v1/onboarding/preview", headers=headers, json=value).json()
    saved = client.post(
        "/api/v1/onboarding/confirm",
        headers=headers,
        json=dict(
            goal=value,
            review_digest=preview["review_digest"],
            reviewed=True,
            idempotency_key="waitlist",
        ),
    ).json()
    response = client.post(f"/api/v1/goals/{saved['id']}/diagnostics", headers=headers)
    assert (
        response.status_code == 422 and response.json()["error"]["code"] == "accepted_goal_required"
    )


def test_pending_qualitative_scores_do_not_change_mastery(platform):
    app, client, headers, saved = accepted(platform)
    # Create the blueprint before publication; immutable released rows cannot be edited.
    with Session(app.state.engine) as db, db.begin():
        record = db.scalar(select(SkillPackVersion))
        # This scenario is tested by a separate draft version activated as synthetic launch data.
        payload = copy.deepcopy(record.payload)
        payload["version"] = "2.1.0"
        for blueprint in payload["blueprints"]:
            blueprint["scoring"] = "human_rubric"
        for definition in payload["diagnostics"]:
            for item in definition["items"]:
                item["response"] = dict(kind="human_rubric")
        content = SkillPack.model_validate(payload)
        new = SkillPackVersion(
            pack_key=content.key,
            version=content.version,
            domain=content.domain,
            author_id=record.author_id,
            payload=content.model_dump(),
            digest=content.digest(),
            status="released",
        )
        db.add(new)
        db.flush()
        from socrat.models import LearnerGoal

        goal_record = db.get(LearnerGoal, saved["id"])
        snapshot = copy.deepcopy(goal_record.snapshot)
        snapshot["pack_versions"] = [
            {"key": content.key, "version": content.version, "digest": content.digest()}
        ]
        goal_record.snapshot = snapshot
    session = client.post(f"/api/v1/goals/{saved['id']}/diagnostics", headers=headers).json()
    response = submit(client, headers, session, answer="An explanation requiring expert review")
    assert response.status_code == 200 and response.json()["status"] == "pending_review"
    with Session(app.state.engine) as db, db.begin():
        raw = db.scalar(select(DiagnosticAnswer))
        assert raw.answer.startswith("An explanation")
        db.delete(raw)  # Artifact erasure does not alter retained scoring facts.
    projection = client.get("/api/v1/learner-state").json()
    assert all(value["evidence_count"] == 0 for value in projection["concepts"].values())


def test_calibration_only_pairs_next_valid_unseen_matching_scope():
    from test_learner_state import fact

    result = dict(
        concepts={"loops": {"evidence_count": 2, "mastery_mean": 0.7}},
        watermark=1,
        policy_version="1.0.0",
    )
    facts = [
        fact(),
        fact(2, mode="assessment", language="java"),
        fact(3, mode="assessment", valid=False),
        fact(4, mode="assessment", score=0.8),
    ]
    pairs = outcome_pairs(result, "pack", "python", facts)
    assert pairs == [
        dict(
            prediction=0.7,
            outcome=0.8,
            model_version="1.0.0",
            concept="loops",
            outcome_event_id="event-4",
        )
    ]
    assert summarize(pairs)["calibration"] == "insufficient_data"
    assert summarize(pairs * 20)["outcome_pairs"] == 1
    calibrated = summarize(
        [{**pairs[0], "outcome_event_id": f"next-{index}"} for index in range(20)]
    )
    assert calibrated["brier_score"] == pytest.approx(0.01)
    assert sum(bin["count"] for bin in calibrated["bins"]) == 20
    assert state_key("pack", "python", "loops") != state_key("pack", "java", "loops")


def test_implementation_adapter_rejects_untrusted_stale_and_failed_runs():
    from socrat.diagnostics.scoring import VerifiedImplementationResult, implementation_score

    payload = dict(
        attempt_id="attempt",
        runtime_digest="sha256:" + "a" * 64,
        test_digest="sha256:" + "b" * 64,
        operational_status="healthy",
        finalized=True,
        signature_verified=True,
        score=1.0,
    )
    result = VerifiedImplementationResult.model_validate(payload)
    assert (
        implementation_score(
            result, "attempt", payload["runtime_digest"], payload["test_digest"]
        ).score
        == 1.0
    )
    for changes in [
        dict(signature_verified=False),
        dict(attempt_id="stale"),
        dict(test_digest="sha256:" + "c" * 64),
    ]:
        with pytest.raises(ValueError, match="Untrusted"):
            implementation_score(
                VerifiedImplementationResult.model_validate({**payload, **changes}),
                "attempt",
                payload["runtime_digest"],
                payload["test_digest"],
            )
    failed = implementation_score(
        VerifiedImplementationResult.model_validate({**payload, "operational_status": "failed"}),
        "attempt",
        payload["runtime_digest"],
        payload["test_digest"],
    )
    assert failed.score is None and failed.quality == 0
