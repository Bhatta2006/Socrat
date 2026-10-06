from sqlalchemy import func, select

from socrat.database import record_event
from socrat.execution.service import ExecutionError, content
from socrat.learnerstate.policy import digest
from socrat.learning.admission import admission_error
from socrat.models import (
    AdvisorShadow,
    CodeAttempt,
    CodeDraft,
    CodeRun,
    DiagnosticSession,
    LearnerGoal,
    LearnerState,
    LearningEvidence,
    SubmitAssistance,
    TutorArtifact,
    TutorTurn,
)
from socrat.tutor import gateway
from socrat.tutor.contracts import HintRequest, TutorOutput
from socrat.tutor.policy import (
    FALLBACKS,
    POLICY_VERSION,
    allowed_level,
    dependency_summary,
    validate_output,
)


def history(db, attempt):
    return list(
        db.scalars(
            select(TutorTurn).where(TutorTurn.attempt_id == attempt.id).order_by(TutorTurn.position)
        )
    )


def assistance_level(db, attempt):
    # Reopening the same family cannot erase prior help or a revealed solution.
    pack, exercise = content(db, attempt)
    family = [x.id for x in pack.exercises if x.family_id == exercise.family_id]
    return max(
        attempt.snapshot.get("hint_level", 0),
        db.scalar(
            select(func.max(TutorTurn.granted_level))
            .join(CodeAttempt, CodeAttempt.id == TutorTurn.attempt_id)
            .where(
                CodeAttempt.user_id == attempt.user_id,
                CodeAttempt.pack_id == attempt.pack_id,
                CodeAttempt.exercise_id.in_(family),
                CodeAttempt.snapshot["language"].as_string() == attempt.snapshot["language"],
            )
        )
        or 0,
    )


def submitted_level(db, run, attempt):
    pin = db.get(SubmitAssistance, run.id)
    return pin.hint_level if pin else attempt.snapshot.get("hint_level", 0)


def dependency(db, user_id):
    facts = list(
        db.scalars(
            select(LearningEvidence)
            .where(LearningEvidence.user_id == user_id, LearningEvidence.kind == "scored")
            .order_by(LearningEvidence.sequence.desc())
        )
    )
    items = []
    invalidated = set(
        db.scalars(
            select(LearningEvidence.payload["target_event_id"].as_string()).where(
                LearningEvidence.user_id == user_id, LearningEvidence.kind == "invalidated"
            )
        )
    )
    for fact in reversed(
        [
            x
            for x in facts
            if x.payload.get("mode") == "practice"
            and x.id not in invalidated
            and x.payload.get("valid")
            and x.payload.get("evidence_type") == "implement"
        ][:10]
    ):
        attempt = db.get(CodeAttempt, fact.source_id)
        if not attempt:
            continue
        turns = history(db, attempt)
        items.append(
            dict(
                level=fact.payload["hint_level"],
                score=fact.payload["score"],
                first_hint_seconds=max(0, turns[0].created_at - attempt.created_at)
                if turns
                else None,
                repeated_requests=sum(x.telemetry.get("repeated_action", False) for x in turns),
            )
        )
    return dependency_summary(items)


def budget(db, user_id, scope_id, settings, stamp):
    daily = list(
        db.scalars(
            select(TutorTurn).where(
                TutorTurn.user_id == user_id, TutorTurn.created_at >= stamp - 86400
            )
        )
    )
    shadows = list(
        db.scalars(
            select(AdvisorShadow).where(
                AdvisorShadow.user_id == user_id, AdvisorShadow.created_at >= stamp - 86400
            )
        )
    )
    used = sum(x.telemetry.get("reserved_microusd", 0) for x in daily)
    used += sum(x.outcome.get("reserved_microusd", 0) for x in shadows)
    calls = sum(x.telemetry.get("reserved_microusd", 0) > 0 for x in daily)
    calls += sum(x.outcome.get("reserved_microusd", 0) > 0 for x in shadows)
    scope_calls = sum(
        x.telemetry.get("reserved_microusd", 0) > 0
        for x in db.scalars(
            select(TutorTurn).where(TutorTurn.user_id == user_id, TutorTurn.scope_id == scope_id)
        )
    )
    return (
        calls < settings.tutor_daily_calls
        and scope_calls < settings.tutor_session_calls
        and used + settings.tutor_call_reserve_microusd <= settings.tutor_daily_budget_microusd
    )


def view(db, turn):
    artifact = db.get(TutorArtifact, turn.id)
    return dict(
        id=turn.id,
        **turn.outcome,
        response=artifact.response if artifact else None,
        created_at=turn.created_at,
    )


def request_hint(db, attempt, body: HintRequest, settings, stamp):
    if db.scalar(
        select(DiagnosticSession.id).where(
            DiagnosticSession.user_id == attempt.user_id,
            DiagnosticSession.status == "in_progress",
            DiagnosticSession.deadline_at > stamp,
        )
    ):
        raise ExecutionError("tutor_assessment_forbidden", 403)
    pack, exercise = content(db, attempt)
    # Always authorize before receipt lookup or context construction.
    if (
        attempt.snapshot["mode"] != "practice"
        or exercise.inventory != "practice"
        or attempt.snapshot.get("diagnostic_attempt_id")
    ):
        raise ExecutionError("tutor_assessment_forbidden", 403)
    old = db.scalar(
        select(TutorTurn).where(
            TutorTurn.attempt_id == attempt.id, TutorTurn.idempotency_key == body.idempotency_key
        )
    )
    if old:
        if old.request_digest != digest(body.model_dump()):
            raise ExecutionError("idempotency_key_reused")
        return view(db, old)
    rejection = admission_error(db, attempt, stamp, settings.learning_sessions_enabled)
    if rejection:
        raise ExecutionError(rejection)
    pending = db.scalar(
        select(CodeRun).where(
            CodeRun.attempt_id == attempt.id,
            CodeRun.manifest["mode"].as_string() == "submit",
            CodeRun.status.in_(["queued", "running"]),
        )
    )
    if pending:
        raise ExecutionError("tutor_submit_pending")
    draft = db.get(CodeDraft, attempt.id)
    if draft is None or draft.revision != body.draft_revision:
        raise ExecutionError("code_draft_stale")
    turns = history(db, attempt)
    if len(turns) >= 100:
        raise ExecutionError("tutor_turn_limit", 429)
    submitted = (
        db.scalar(
            select(CodeRun).where(
                CodeRun.attempt_id == attempt.id,
                CodeRun.manifest["mode"].as_string() == "submit",
                CodeRun.status == "completed",
            )
        )
        is not None
    )
    action_digest = digest(dict(source=draft.source, reasoning=body.reasoning))
    repeated = any(x.action_digest == action_digest for x in turns)
    previous = max((x.granted_level for x in turns), default=0)
    goal = db.get(LearnerGoal, attempt.goal_id)
    track = goal.snapshot["active_track"]
    ceiling = next(x.help_ceiling for x in pack.tracks if x.id == track)
    level = allowed_level(
        previous,
        body.requested_level,
        submitted=submitted,
        exited=body.action == "exit",
        accessibility=body.action == "accessibility",
        new_action=not repeated,
        ceiling=ceiling,
    )
    if level == 0:
        raise ExecutionError("tutor_help_locked", 403)
    authorized_level = level
    summary = dependency(db, attempt.user_id)
    require_plan = (
        summary["require_plan"] and len(body.reasoning.split()) < 5 and body.action != "exit"
    )
    if require_plan:
        level = 1
    language = attempt.snapshot["language"]
    variant = pack.variant_for(exercise.id, language)
    assert variant is not None
    authored = next(
        (
            x
            for x in pack.tutor_hints
            if x.exercise_id == exercise.id and x.language == language and x.level == level
        ),
        None,
    )
    if level == 4 and authored is None:
        level = 3
    fallback = FALLBACKS.get(level, FALLBACKS[1])
    response = dict(
        diagnosis="",
        hint_level=level,
        message=fallback[0],
        question=fallback[1],
        concept_refs=exercise.concept_ids,
        code_lines=[],
        reasoning_quote="",
    )
    if authored:
        response.update(message=authored.message, question=authored.question)
    if level == 5:
        response.update(
            message=exercise.rubric + "\n\n" + variant.reference_solution,
            question="Explain why this works, then refresh your plan for a fresh independent task.",
        )
    if require_plan:
        response.update(
            message="Write a short plan in your own words before the next hint.",
            question="What have you tried, and what will you check next?",
        )
    # Explicit allow-list: no reference solutions, hidden tests, identity, other tasks or full pack.
    last_run = db.scalar(
        select(CodeRun)
        .where(CodeRun.attempt_id == attempt.id, CodeRun.status == "completed")
        .order_by(CodeRun.created_at.desc())
        .limit(1)
    )
    public_results = []
    if last_run and last_run.result:
        public_results = [
            dict(
                status=x["status"],
                stdout=gateway.redact(x["stdout"][:1000]),
                stderr=gateway.redact(x["stderr"][:1000]),
            )
            for x in last_run.result.get("cases", [])
            if last_run.tests[x["index"]]["visibility"] == "public"
        ][:3]
    from socrat.learnerstate.projector import state_key

    state = db.get(LearnerState, attempt.user_id)
    labels = set()
    if state:
        for concept_id in exercise.concept_ids:
            labels.update(
                state.projection.get("concepts", {})
                .get(state_key(attempt.pack_id, language, concept_id), {})
                .get("misconceptions", {})
            )
    labels &= {x.id for x in pack.misconception_taxonomy}
    context = dict(
        statement=exercise.statement,
        language=language,
        track=track,
        allowed_level=level,
        concepts=[
            dict(id=x.id, title=x.title, excerpt=x.explanation[:800])
            for x in pack.concepts
            if x.id in exercise.concept_ids
        ],
        code=gateway.redact(draft.source[:12000]),
        reasoning=gateway.redact(body.reasoning),
        public_results=public_results,
        misconception_labels=sorted(labels)[:10],
        prior_hints=[
            db.get(TutorArtifact, x.id).response
            for x in turns[-3:]
            if db.get(TutorArtifact, x.id) and x.granted_level <= 3
        ],
    )
    scope_id = attempt.snapshot.get("learning_context", {}).get("session_id", attempt.id)
    result = gateway.GatewayResult(
        None, "reviewed_explanation" if level >= 4 else "curated_fallback"
    )
    if level <= 3 and not require_plan:
        result = gateway.generate(
            settings,
            prompt=settings.tutor_prompt_version,
            context=context,
            schema=TutorOutput.model_json_schema(),
            budget_available=budget(db, attempt.user_id, scope_id, settings, stamp),
            rollout_key=attempt.user_id,
        )
    if result.output is not None:
        try:
            response = validate_output(
                result.output,
                level=level,
                concepts=exercise.concept_ids,
                code=context["code"],
                reasoning=context["reasoning"],
                reference=variant.reference_solution,
            ).model_dump()
            level = response["hint_level"]
            result.reason = "validated_model"
        except ValueError:
            result.reason = "rejected_output"

    def failure(reason):
        return reason.startswith("provider_") or reason == "rejected_output"

    failed = failure(result.reason)
    review_required = failed and sum(failure(x.telemetry["reason"]) for x in turns) >= 1
    turn = TutorTurn(
        user_id=attempt.user_id,
        attempt_id=attempt.id,
        scope_id=scope_id,
        position=len(turns) + 1,
        idempotency_key=body.idempotency_key,
        request_digest=digest(body.model_dump()),
        context_digest=digest(context),
        action_digest=action_digest,
        granted_level=level,
        outcome=dict(
            mode="practice",
            allowed_level=authorized_level,
            granted_level=level,
            policy_version=POLICY_VERSION,
            prompt_version=settings.tutor_prompt_version,
            fallback=result.reason != "validated_model",
            review_required=review_required,
            fresh_task_required=level >= 4,
            require_plan=require_plan,
        ),
        telemetry=dict(
            reason=result.reason,
            model=settings.tutor_model if result.reserved_microusd else "none",
            prompt_digest=digest(gateway.PROMPTS[settings.tutor_prompt_version]),
            output_digest=digest(response),
            language=language,
            track=track,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            reserved_microusd=result.reserved_microusd,
            repeated_action=repeated,
            latency_alert=result.latency_ms >= 4000,
            budget_alert=result.reason == "budget_exhausted",
        ),
        created_at=stamp,
    )
    db.add(turn)
    db.flush()
    db.add(
        TutorArtifact(turn_id=turn.id, reasoning=body.reasoning, context=context, response=response)
    )
    record_event(
        db,
        attempt.user_id,
        "tutor.review_required" if review_required else "tutor.hint_granted",
        turn.id,
    )
    db.flush()
    return view(db, turn)


def protect_exposed_families(db, goal, pack, pack_id, language, exposures):
    """Pin fresh-task obligations into planner replay inputs without inventing evidence."""
    items = {x.id: x for x in pack.exercises}
    exposed = set(
        db.scalars(
            select(CodeAttempt.exercise_id)
            .join(TutorTurn, TutorTurn.attempt_id == CodeAttempt.id)
            .where(
                CodeAttempt.user_id == goal.user_id,
                CodeAttempt.pack_id == pack_id,
                CodeAttempt.snapshot["language"].as_string() == language,
                TutorTurn.granted_level >= 4,
            )
        )
    )
    families = {items[x].family_id for x in exposed if x in items}
    from socrat.planning.policy import POLICY

    for item in items.values():
        if item.family_id in families:
            exposures[item.id] = dict(count=POLICY.maximum_exposures, last_date="")


def exposure_watermark(db, user_id):
    return (
        db.scalar(
            select(func.count())
            .select_from(TutorTurn)
            .where(TutorTurn.user_id == user_id, TutorTurn.granted_level >= 4)
        )
        or 0
    )
