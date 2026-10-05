"""Deterministic diagnostics. Public views never contain scoring specifications."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.diagnostics.contracts import DiagnosticDefinition
from socrat.diagnostics.scoring import score_response
from socrat.learnerstate.policy import POLICIES, digest
from socrat.learnerstate.projector import EvidenceFact, band, state_key
from socrat.learnerstate.service import append_fact, facts_for, project
from socrat.models import (
    DiagnosticAnswer,
    DiagnosticAttempt,
    DiagnosticResponse,
    DiagnosticSession,
    LearnerGoal,
    LearnerState,
    SkillPackHead,
    SkillPackVersion,
    identifier,
)
from socrat.skillpacks.schema import SkillPack
from socrat.skillpacks.service import PackError, load


class DiagnosticError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status


def content_for(
    db: Session, session: DiagnosticSession, eligibility: bool = True
) -> tuple[SkillPack, DiagnosticDefinition]:
    record = db.get(SkillPackVersion, session.pack_id)
    if record is None:
        raise DiagnosticError("diagnostic_content_missing", 503)
    # Release/quarantine uses the head lock too. Immutable old releases may remain eligible.
    db.scalar(
        select(SkillPackHead).where(SkillPackHead.pack_key == record.pack_key).with_for_update()
    )
    db.refresh(record)
    if eligibility and record.status != "released":
        raise DiagnosticError("diagnostic_content_withdrawn")
    try:
        pack = load(record)
    except PackError as exc:
        raise DiagnosticError(exc.code, exc.status) from exc
    if pack.digest() != session.snapshot["pack_digest"]:
        raise DiagnosticError("diagnostic_content_mismatch", 503)
    definition = next(
        (item for item in pack.diagnostics if item.blueprint_id == session.blueprint_id), None
    )
    if definition is None:
        raise DiagnosticError("diagnostic_blueprint_missing", 503)
    return pack, definition


def attempts_for(db: Session, session_id: str) -> list[DiagnosticAttempt]:
    return list(
        db.scalars(
            select(DiagnosticAttempt)
            .where(DiagnosticAttempt.diagnostic_id == session_id)
            .order_by(DiagnosticAttempt.position)
        )
    )


def responses_for(db: Session, session_id: str) -> list[DiagnosticResponse]:
    return list(
        db.scalars(select(DiagnosticResponse).where(DiagnosticResponse.diagnostic_id == session_id))
    )


def completion_state(
    db: Session,
    session: DiagnosticSession,
    pack: SkillPack,
    definition: DiagnosticDefinition,
    as_of: int,
) -> tuple[bool, dict]:
    projection = project(db, session.user_id, session.policy_version, as_of)
    blueprint = next(item for item in pack.blueprints if item.id == definition.blueprint_id)
    language = session.snapshot["language"]
    states = {
        concept: projection["concepts"].get(state_key(session.pack_id, language, concept))
        for concept in blueprint.concept_ids
    }
    # Only verified evidence counts; priors and self-report cannot meet coverage.
    stable = all(
        state
        and state["independent_count"] >= definition.minimum_per_concept
        and len(state["families"]) >= 2
        and band(max(0, state["mastery_mean"] - definition.uncertainty_margin))
        == band(min(1, state["mastery_mean"] + definition.uncertainty_margin))
        for state in states.values()
    )
    for concept, state in states.items():
        if state is None:
            stable = False
            continue
        thresholds = {0.4, 0.65, 0.75, 0.8} | {
            max(0.75, edge.minimum_mastery) for edge in pack.edges if edge.prerequisite == concept
        }
        if any(
            abs(state["mastery_mean"] - threshold) <= definition.uncertainty_margin
            for threshold in thresholds
        ):
            stable = False
    if definition.scope == "full_placement":
        stable = stable and all(
            state and "implement" in state["forms"] and len(state["forms"]) >= 2
            for state in states.values()
        )
    return bool(stable), {
        "schema_version": 1,
        "scope": definition.scope,
        "full_placement": bool(stable and definition.scope == "full_placement"),
        "placement_sufficient": bool(stable),
        "concepts": states,
        "declared_track": session.snapshot["declared_track"],
        "active_track": session.snapshot["active_track"],
        "language": language,
        "pack_digest": pack.digest(),
        "policy_version": session.policy_version,
        "as_of": as_of,
        "watermark": projection["watermark"],
    }


def select_next(
    db: Session,
    session: DiagnosticSession,
    pack: SkillPack,
    definition: DiagnosticDefinition,
    as_of: int,
):
    attempts = attempts_for(db, session.id)
    responses = {response.attempt_id: response for response in responses_for(db, session.id)}
    if attempts and attempts[-1].id not in responses:
        return
    stable, _ = completion_state(db, session, pack, definition, as_of)
    if as_of >= session.deadline_at:
        session.status = "expired"
        return
    if stable:
        session.status = "ready_to_complete"
        return
    if any(response.outcome["status"] == "pending_review" for response in responses.values()):
        session.status = "pending_review"
        return
    if len(attempts) >= definition.maximum_items:
        session.status = "limited"
        return
    exposed = db.scalars(
        select(DiagnosticAttempt)
        .join(DiagnosticSession)
        .where(
            DiagnosticSession.user_id == session.user_id,
            DiagnosticSession.pack_id == session.pack_id,
        )
    ).all()
    exercises = {item.id: item for item in pack.exercises}
    families = {exercises[attempt.exercise_id].family_id for attempt in exposed}
    language = session.snapshot["language"]
    projection = project(db, session.user_id, session.policy_version, as_of)
    first_stage = session.snapshot["first_diagnostic_stage"]
    candidates = []
    blocked_runtime = False
    for item in definition.items:
        exercise = exercises[item.exercise_id]
        if item.languages and language not in item.languages:
            continue
        if exercise.family_id in families or exercise.calibration != "reviewed":
            continue
        if item.response.kind == "implementation":
            from socrat.execution.service import healthy_images

            settings = db.info.get("execution_settings")
            images = healthy_images(db, settings, as_of) if settings else []
            if not any(
                v.language == language and v.runtime_ref in images for v in exercise.variants
            ):
                blocked_runtime = True
                continue
        if exercise.estimated_minutes * 60 > session.deadline_at - as_of:
            continue
        # Diagnostic probes may inspect unready prerequisites only within the authored blueprint.
        need = sum(
            1
            / (
                1
                + projection["concepts"]
                .get(state_key(session.pack_id, language, concept), {})
                .get("independent_count", 0)
            )
            for concept in exercise.concept_ids
        )
        stage_penalty = int(not attempts and item.stage != first_stage)
        estimates = [
            projection["concepts"].get(state_key(session.pack_id, language, concept), {})
            for concept in exercise.concept_ids
        ]
        # Earned evidence can change difficulty; priors/self-report cannot accelerate it.
        target_difficulty = min(
            10,
            1
            + min((estimate.get("independent_successes", 0) for estimate in estimates), default=0),
        )
        candidates.append(
            (stage_penalty, -need, abs(exercise.difficulty - target_difficulty), exercise.id, item)
        )
    if not candidates:
        session.status = "blocked_runtime" if blocked_runtime else "limited"
        return
    selected = min(candidates, key=lambda row: row[:4])[-1]
    db.add(
        DiagnosticAttempt(
            diagnostic_id=session.id,
            exercise_id=selected.exercise_id,
            position=len(attempts) + 1,
            issued_at=as_of,
            selection={
                "reason_code": "blueprint_coverage_probe",
                "stage": selected.stage,
                "candidate_ids": sorted(row[3] for row in candidates),
                "as_of": as_of,
                "watermark": projection["watermark"],
            },
        )
    )
    session.status = "in_progress"
    db.flush()


def create_diagnostic(db: Session, goal: LearnerGoal, as_of: int) -> DiagnosticSession:
    existing = db.scalar(select(DiagnosticSession).where(DiagnosticSession.goal_id == goal.id))
    if existing:
        return existing
    recent = db.scalars(
        select(DiagnosticSession).where(
            DiagnosticSession.user_id == goal.user_id, DiagnosticSession.started_at >= as_of - 86400
        )
    ).all()
    if len(recent) >= 10:
        raise DiagnosticError("diagnostic_daily_limit", 429)
    snapshot = goal.snapshot
    if not snapshot["routing_outcome"].startswith("accept_"):
        raise DiagnosticError("accepted_goal_required", 422)
    language, active = snapshot["goal"]["language"], snapshot["active_track"]
    chosen = None
    # Every pin must still be valid, including the declared target behind a bridge.
    for pin in sorted(
        snapshot["pack_versions"], key=lambda value: (value["key"], value["version"])
    ):
        db.scalar(
            select(SkillPackHead).where(SkillPackHead.pack_key == pin["key"]).with_for_update()
        )
        record = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == pin["key"], SkillPackVersion.version == pin["version"]
            )
        )
        if record is None or record.status != "released" or record.digest != pin["digest"]:
            raise DiagnosticError("goal_content_unavailable")
        pack = load(record)
        if pack.purpose != "launch":
            raise DiagnosticError("launch_content_required")
        for definition in sorted(pack.diagnostics, key=lambda value: value.blueprint_id):
            if definition.track == active and (
                not definition.languages or language in definition.languages
            ):
                chosen = chosen or (record, pack, definition)
    if chosen is None:
        raise DiagnosticError("diagnostic_coverage_unavailable")
    record, pack, definition = chosen
    state = db.get(LearnerState, goal.user_id)
    session = DiagnosticSession(
        user_id=goal.user_id,
        goal_id=goal.id,
        pack_id=record.id,
        blueprint_id=definition.blueprint_id,
        policy_version=state.active_policy if state else "1.0.0",
        started_at=as_of,
        deadline_at=as_of + definition.maximum_seconds,
        snapshot={
            "pack_digest": record.digest,
            "language": language,
            "declared_track": snapshot["declared_track"],
            "active_track": active,
            "first_diagnostic_stage": snapshot["first_diagnostic_stage"],
            "scope": definition.scope,
            "goal_policy_version": snapshot["policy_version"],
        },
    )
    db.add(session)
    db.flush()
    select_next(db, session, pack, definition, as_of)
    record_event(db, goal.user_id, "diagnostic.started", session.id)
    return session


def result_view(db: Session, session: DiagnosticSession) -> dict | None:
    if session.result is None:
        return None
    facts = facts_for(db, session.user_id)
    targets = {fact.event_id: fact for fact in facts if fact.kind == "scored"}
    corrected = any(
        fact.kind == "invalidated"
        and fact.target_event_id in targets
        and targets[fact.target_event_id].sequence <= session.result["watermark"]
        and fact.pack_id == session.pack_id
        and fact.language == session.snapshot["language"]
        for fact in facts
    )
    record = db.get(SkillPackVersion, session.pack_id)
    current = not corrected and bool(record and record.status == "released")
    result = {**session.result, "evidence_current": current}
    if not current:
        result = {
            **result,
            "placement_sufficient": False,
            "full_placement": False,
            "historical_placement_sufficient": session.result["placement_sufficient"],
            "stop_reason": "evidence_corrected" if corrected else "content_withdrawn",
            "missing_evidence": [
                *session.result["missing_evidence"],
                "fresh_placement_review_required",
            ],
        }
    return result


def public_view(db: Session, session: DiagnosticSession, as_of: int) -> dict:
    pack, definition = content_for(db, session, eligibility=False)
    record = db.get(SkillPackVersion, session.pack_id)
    attempts = attempts_for(db, session.id)
    assert record is not None
    responses = {response.attempt_id: response for response in responses_for(db, session.id)}
    status = session.status
    if status == "in_progress" and record.status != "released":
        status = "blocked_content"
    elif status == "in_progress" and as_of >= session.deadline_at:
        status = "expired"
    item_view = None
    if status == "in_progress" and attempts and attempts[-1].id not in responses:
        attempt = attempts[-1]
        exercise = next(item for item in pack.exercises if item.id == attempt.exercise_id)
        spec = next(item for item in definition.items if item.exercise_id == attempt.exercise_id)
        item_view = {
            "attempt_id": attempt.id,
            "title": exercise.title,
            "statement": exercise.statement,
            "exercise_id": exercise.id,
            "kind": spec.response.kind,
            "choices": [choice.model_dump() for choice in spec.response.choices],
            "position": attempt.position,
            "stage": spec.stage,
        }
    return {
        "id": session.id,
        "goal_id": session.goal_id,
        "status": status,
        "revision": session.revision,
        "scope": definition.scope,
        "deadline_at": session.deadline_at,
        "server_time": as_of,
        "active_track": session.snapshot["active_track"],
        "declared_track": session.snapshot["declared_track"],
        "answered": len(responses),
        "item": item_view,
        "result": result_view(db, session),
    }


def respond(db: Session, session: DiagnosticSession, body: dict, as_of: int) -> dict:
    request_digest = digest(body)
    existing = db.get(DiagnosticResponse, body["attempt_id"])
    duplicate_key = db.scalar(
        select(DiagnosticResponse).where(
            DiagnosticResponse.diagnostic_id == session.id,
            DiagnosticResponse.idempotency_key == body["idempotency_key"],
        )
    )
    if existing or duplicate_key:
        existing = existing or duplicate_key
        assert existing is not None
        if existing.diagnostic_id != session.id or existing.request_digest != request_digest:
            raise DiagnosticError("idempotency_key_reused")
        return public_view(db, session, as_of)
    attempts = attempts_for(db, session.id)
    if (
        session.status != "in_progress"
        or not attempts
        or attempts[-1].id != body["attempt_id"]
        or session.revision != body["revision"]
    ):
        raise DiagnosticError("diagnostic_response_stale")
    if as_of >= session.deadline_at:
        raise DiagnosticError("diagnostic_time_expired")
    try:
        pack, definition = content_for(db, session)
    except DiagnosticError as exc:
        if exc.code != "diagnostic_content_withdrawn":
            raise
        pack, definition = content_for(db, session, eligibility=False)
        withdrawn = True
    else:
        withdrawn = False
    exercise = next(item for item in pack.exercises if item.id == attempts[-1].exercise_id)
    spec = next(item for item in definition.items if item.exercise_id == exercise.id).response
    if spec.kind == "implementation" and not withdrawn and not body["report_problem"]:
        raise DiagnosticError("implementation_requires_verified_submission", 422)
    answer = body["answer"]
    if (
        not withdrawn
        and not body["report_problem"]
        and spec.kind == "choice"
        and answer not in {choice.id for choice in spec.choices}
    ):
        raise DiagnosticError("invalid_diagnostic_choice", 422)
    evaluation = score_response(spec, answer, withdrawn, body["report_problem"])
    valid = evaluation.status == "scored"
    score = evaluation.score or 0.0
    reason = evaluation.reason_code
    outcome = evaluation.model_dump()
    db.add(
        DiagnosticResponse(
            attempt_id=body["attempt_id"],
            diagnostic_id=session.id,
            idempotency_key=body["idempotency_key"],
            request_digest=request_digest,
            answer_digest=digest(answer),
            outcome=outcome,
            created_at=as_of,
        )
    )
    db.add(
        DiagnosticAnswer(
            attempt_id=body["attempt_id"], user_id=session.user_id, answer=answer, created_at=as_of
        )
    )
    state = db.get(LearnerState, session.user_id)
    current = project(db, session.user_id, state.active_policy if state else "1.0.0", as_of)
    fact = EvidenceFact(
        event_id=identifier(),
        user_id=session.user_id,
        goal_id=session.goal_id,
        track=session.snapshot["declared_track"],
        sequence=current["watermark"] + 1,
        source_id=body["attempt_id"],
        pack_id=session.pack_id,
        pack_digest=pack.digest(),
        language=session.snapshot["language"],
        concept_ids=exercise.concept_ids,
        mode="diagnostic",
        evidence_type=exercise.evidence_mode,
        family_id=exercise.family_id,
        score=score,
        quality=evaluation.quality,
        hint_level=0,
        elapsed_seconds=float(max(0, as_of - attempts[-1].issued_at)),
        expected_seconds=float(exercise.estimated_minutes * 60),
        difficulty=exercise.difficulty,
        valid=valid,
        unseen=True,
        finalized=valid,
        occurred_at=as_of,
        scoring_version=evaluation.scoring_version,
        policy_version=session.policy_version,
        policy_digest=digest(POLICIES[session.policy_version].model_dump()),
        reason_code=reason,
        misconception_codes=evaluation.misconception_codes,
    )
    append_fact(db, session.user_id, fact)
    session.revision += 1
    db.flush()
    if withdrawn:
        session.status = "blocked_content"
    else:
        select_next(db, session, pack, definition, as_of)
    record_event(db, session.user_id, "diagnostic.response_finalized", session.id)
    return public_view(db, session, as_of)


def complete(db: Session, session: DiagnosticSession, as_of: int) -> dict:
    if session.result is not None:
        return result_view(db, session) or {}
    pack, definition = content_for(db, session, eligibility=False)
    record = db.get(SkillPackVersion, session.pack_id)
    stable, result = completion_state(db, session, pack, definition, as_of)
    assert record is not None
    if record.status != "released":
        stable = False
        session.status = "blocked_content"
    elif as_of >= session.deadline_at:
        stable = False
        session.status = "expired"
    elif session.status == "in_progress" and not stable:
        raise DiagnosticError("diagnostic_not_ready")
    elif stable:
        session.status = "completed"
    result["placement_sufficient"] = stable
    result["full_placement"] = bool(stable and definition.scope == "full_placement")
    result["stop_reason"] = "placement_stable" if stable else session.status
    result["missing_evidence"] = [] if stable else ["required_coverage_or_stability_not_met"]
    if definition.scope == "objective_readiness":
        result["missing_evidence"].append("implementation_not_verified")
    session.result = result
    record_event(
        db, session.user_id, "diagnostic.completed" if stable else "diagnostic.limited", session.id
    )
    return result_view(db, session) or {}
