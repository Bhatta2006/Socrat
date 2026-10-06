"""Transactional, owned execution broker; never imports a process executor."""

import secrets
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.config import Settings
from socrat.database import record_event
from socrat.diagnostics.scoring import VerifiedImplementationResult, implementation_score
from socrat.execution.protocol import (
    COMMANDS,
    JobEnvelope,
    JobManifest,
    ResultEnvelope,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
    verify,
)
from socrat.learnerstate.policy import POLICIES, digest
from socrat.learnerstate.projector import EvidenceFact, state_key
from socrat.learnerstate.service import append_fact, facts_for, project
from socrat.models import (
    CodeAttempt,
    CodeDraft,
    CodeRun,
    CodeRunSource,
    CurriculumHead,
    CurriculumRevision,
    DiagnosticAttempt,
    DiagnosticResponse,
    DiagnosticSession,
    ExecutionCapacity,
    ExecutionWorker,
    LearnerGoal,
    LearnerState,
    SkillPackHead,
    SkillPackVersion,
    identifier,
)
from socrat.planning.engine import ready
from socrat.skillpacks.service import load


class ExecutionError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status


def healthy_images(db: Session, settings: Settings, as_of: int) -> list[str]:
    if not settings.execution_enabled:
        return []
    allowed = {x["image"] for x in settings.execution_profiles}
    return sorted(
        {
            image
            for worker in db.scalars(
                select(ExecutionWorker).where(ExecutionWorker.seen_at >= as_of - 30)
            )
            for image in worker.images
            if image in allowed
        }
    )


def content(db: Session, attempt: CodeAttempt):
    record = db.get(SkillPackVersion, attempt.pack_id)
    if record is None:
        raise ExecutionError("execution_content_missing")
    db.scalar(
        select(SkillPackHead).where(SkillPackHead.pack_key == record.pack_key).with_for_update()
    )
    db.refresh(record)
    if record.status != "released":
        raise ExecutionError("execution_content_withdrawn")
    pack = load(record)
    if pack.digest() != attempt.snapshot["pack_digest"]:
        raise ExecutionError("execution_content_mismatch")
    exercise = next(x for x in pack.exercises if x.id == attempt.exercise_id)
    return pack, exercise


def create_attempt(
    db: Session,
    goal: LearnerGoal,
    exercise_id: str,
    key: str,
    diagnostic_attempt_id: str | None,
    settings: Settings,
    stamp: int,
    learning_context: dict | None = None,
):
    request_digest = digest(
        dict(
            goal_id=goal.id,
            exercise_id=exercise_id,
            diagnostic_attempt_id=diagnostic_attempt_id,
            **({"learning_context": learning_context} if learning_context else {}),
        )
    )
    existing = db.scalar(
        select(CodeAttempt).where(
            CodeAttempt.user_id == goal.user_id, CodeAttempt.idempotency_key == key
        )
    )
    if existing:
        if existing.request_digest != request_digest:
            raise ExecutionError("idempotency_key_reused")
        return existing
    if not goal.snapshot["routing_outcome"].startswith("accept_"):
        raise ExecutionError("accepted_goal_required")
    chosen = None
    for pin in sorted(goal.snapshot["pack_versions"], key=lambda x: x["key"]):
        db.scalar(
            select(SkillPackHead).where(SkillPackHead.pack_key == pin["key"]).with_for_update()
        )
        record = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == pin["key"], SkillPackVersion.version == pin["version"]
            )
        )
        if record is None:
            raise ExecutionError("goal_content_unavailable")
        db.refresh(record)
        if record.status != "released" or record.digest != pin["digest"]:
            raise ExecutionError("goal_content_unavailable")
        pack = load(record)
        exercise = next((x for x in pack.exercises if x.id == exercise_id), None)
        if exercise:
            chosen = record, pack, exercise
    if chosen is None:
        raise ExecutionError("exercise_not_available", 404)
    record, pack, exercise = chosen
    language = goal.snapshot["goal"]["language"]
    variant = next((x for x in exercise.variants if x.language == language), None)
    if exercise.modality != "code" or exercise.calibration != "reviewed" or variant is None:
        raise ExecutionError("exercise_language_unavailable")
    profile = next(
        (
            RuntimeProfile.model_validate(x)
            for x in settings.execution_profiles
            if x["language"] == language and x["image"] == variant.runtime_ref
        ),
        None,
    )
    if profile is None or profile.image not in healthy_images(db, settings, stamp):
        raise ExecutionError("sandbox_unavailable", 503)
    mode = "practice"
    if diagnostic_attempt_id:
        issued = db.get(DiagnosticAttempt, diagnostic_attempt_id)
        session = db.get(DiagnosticSession, issued.diagnostic_id) if issued else None
        latest = (
            db.scalar(
                select(DiagnosticAttempt)
                .where(DiagnosticAttempt.diagnostic_id == session.id)
                .order_by(DiagnosticAttempt.position.desc())
                .limit(1)
            )
            if session
            else None
        )
        if (
            issued is None
            or latest is None
            or session is None
            or session.user_id != goal.user_id
            or session.goal_id != goal.id
            or session.pack_id != record.id
            or session.status != "in_progress"
            or session.result is not None
            or issued.exercise_id != exercise.id
            or latest.id != issued.id
            or stamp >= session.deadline_at
        ):
            raise ExecutionError("diagnostic_response_stale")
        definition = next(x for x in pack.diagnostics if x.blueprint_id == session.blueprint_id)
        if not any(
            x.exercise_id == exercise.id and x.response.kind == "implementation"
            for x in definition.items
        ):
            raise ExecutionError("diagnostic_item_mismatch")
        mode = "diagnostic"
        if db.scalar(
            select(CodeAttempt).where(
                CodeAttempt.user_id == goal.user_id,
                CodeAttempt.snapshot["diagnostic_attempt_id"].as_string() == diagnostic_attempt_id,
            )
        ):
            raise ExecutionError("diagnostic_attempt_already_started")
    else:
        if exercise.inventory != "practice":
            raise ExecutionError("protected_inventory", 403)
        from datetime import datetime
        from zoneinfo import ZoneInfo

        head = db.get(CurriculumHead, goal.id)
        revision = db.get(CurriculumRevision, head.active_id) if head else None
        if head is None or head.status != "confirmed" or revision is None:
            raise ExecutionError("reviewed_plan_required")
        today = (
            datetime.fromtimestamp(stamp, ZoneInfo(goal.snapshot["goal"]["timezone"]))
            .date()
            .isoformat()
        )
        eligible_ids = {
            key
            for day in revision.snapshot["days"]
            if day["date"] == today
            for block in day["blocks"]
            for key in block["exercise_ids"]
        }
        if exercise.id not in eligible_ids or revision.snapshot["evidence_watermark"] != len(
            facts_for(db, goal.user_id)
        ):
            raise ExecutionError("exercise_not_planned")
        overlay = next(x for x in pack.tracks if x.id == goal.snapshot["active_track"])
        if not set(exercise.concept_ids) <= set(overlay.concept_ids):
            raise ExecutionError("exercise_outside_track")
        state = db.get(LearnerState, goal.user_id)
        projection = project(db, goal.user_id, state.active_policy if state else "1.0.0", stamp)
        if any(
            not ready(
                projection["concepts"].get(state_key(record.id, language, edge.prerequisite), {}),
                max(0.75, edge.minimum_mastery),
            )
            for edge in pack.edges
            if edge.concept in exercise.concept_ids
        ):
            raise ExecutionError("prerequisite_not_ready")
    unseen = not any(
        f.family_id == exercise.family_id and f.pack_id == record.id and f.language == language
        for f in facts_for(db, goal.user_id)
    )
    attempt = CodeAttempt(
        user_id=goal.user_id,
        goal_id=goal.id,
        pack_id=record.id,
        exercise_id=exercise.id,
        idempotency_key=key,
        request_digest=request_digest,
        created_at=stamp,
        snapshot=dict(
            pack_digest=pack.digest(),
            language=language,
            runtime=profile.model_dump(),
            mode=mode,
            diagnostic_attempt_id=diagnostic_attempt_id,
            hint_level=0,
            unseen=unseen,
            **({"learning_context": learning_context} if learning_context else {}),
        ),
    )
    db.add(attempt)
    db.flush()
    db.add(
        CodeDraft(attempt_id=attempt.id, source=variant.starter_code, revision=0, updated_at=stamp)
    )
    record_event(db, goal.user_id, "execution.attempt_created", attempt.id)
    return attempt


def attempt_view(db: Session, attempt: CodeAttempt):
    from socrat.tutor.service import assistance_level

    pack, exercise = content(db, attempt)
    draft = db.get(CodeDraft, attempt.id)
    assert draft is not None
    return dict(
        id=attempt.id,
        exercise_id=exercise.id,
        title=exercise.title,
        statement=exercise.statement,
        language=attempt.snapshot["language"],
        source=draft.source,
        revision=draft.revision,
        samples=[x.model_dump() for x in exercise.tests if x.visibility == "public"],
        mode=attempt.snapshot["mode"],
        assistance_level=assistance_level(db, attempt),
        runtime_id=attempt.snapshot["runtime"]["id"],
    )


def create_upsolve_attempt(db, parent, session_id, index, settings, stamp, repair_id=None):
    """Internal repair of an already-issued practice item; never a new unseen item."""
    pack, exercise = content(db, parent)
    if exercise.inventory != "practice" or parent.snapshot["mode"] != "practice":
        raise ExecutionError("protected_inventory", 403)
    if parent.snapshot["runtime"]["image"] not in healthy_images(db, settings, stamp):
        raise ExecutionError("sandbox_unavailable", 503)
    draft = db.get(CodeDraft, parent.id)
    assert draft is not None
    source, runtime = draft.source, parent.snapshot["runtime"]
    if repair_id:
        from socrat.models import LearningSession

        session = db.get(LearningSession, session_id)
        if (
            session is None
            or session.snapshot["blocks"][index].get("repair_exercise_id") != repair_id
        ):
            raise ExecutionError("session_attempt_mismatch")
        repair = next((x for x in pack.exercises if x.id == repair_id), None)
        if (
            repair is None
            or repair.inventory != "practice"
            or repair.calibration != "reviewed"
            or repair.modality != "code"
            or set(repair.concept_ids) != set(exercise.concept_ids)
            or repair.difficulty > exercise.difficulty
        ):
            raise ExecutionError("exercise_not_available")
        variant = next(
            (x for x in repair.variants if x.language == parent.snapshot["language"]), None
        )
        profile = next(
            (
                x
                for x in settings.execution_profiles
                if variant
                and x["language"] == variant.language
                and x["image"] == variant.runtime_ref
            ),
            None,
        )
        if (
            variant is None
            or profile is None
            or profile["image"] not in healthy_images(db, settings, stamp)
        ):
            raise ExecutionError("sandbox_unavailable", 503)
        exercise = repair
        runtime = RuntimeProfile.model_validate(profile).model_dump()
        source = variant.starter_code
    context = dict(session_id=session_id, block_index=index, phase="upsolve", parent_id=parent.id)
    attempt = CodeAttempt(
        user_id=parent.user_id,
        goal_id=parent.goal_id,
        pack_id=parent.pack_id,
        exercise_id=exercise.id,
        idempotency_key="session_" + session_id + "_" + str(index) + "_upsolve",
        request_digest=digest(context),
        created_at=stamp,
        snapshot={
            **parent.snapshot,
            "runtime": runtime,
            "unseen": False,
            "learning_context": context,
        },
    )
    db.add(attempt)
    db.flush()
    db.add(CodeDraft(attempt_id=attempt.id, source=source, revision=0, updated_at=stamp))
    record_event(db, parent.user_id, "execution.upsolve_created", attempt.id)
    return attempt


def enqueue(
    db: Session,
    attempt: CodeAttempt,
    mode: Literal["run", "submit"],
    body: dict,
    settings: Settings,
    stamp: int,
    client_key: str,
):
    request_digest = digest(dict(mode=mode, **body))
    existing = db.scalar(
        select(CodeRun).where(
            CodeRun.attempt_id == attempt.id, CodeRun.idempotency_key == body["idempotency_key"]
        )
    )
    if existing:
        if existing.request_digest != request_digest:
            raise ExecutionError("idempotency_key_reused")
        return existing
    from socrat.learning.admission import admission_error

    rejection = admission_error(db, attempt, stamp, settings.learning_sessions_enabled)
    if rejection:
        raise ExecutionError(rejection)
    db.scalar(select(ExecutionCapacity).where(ExecutionCapacity.id == 1).with_for_update())
    pack, exercise = content(db, attempt)
    if attempt.snapshot["runtime"]["image"] not in healthy_images(db, settings, stamp):
        raise ExecutionError("sandbox_unavailable", 503)
    if mode == "submit" and db.scalar(
        select(CodeRun).where(
            CodeRun.attempt_id == attempt.id,
            CodeRun.manifest["mode"].as_string() == "submit",
            CodeRun.status.in_(["queued", "running", "completed"]),
        )
    ):
        raise ExecutionError("attempt_already_submitted")
    queued = (
        db.scalar(
            select(func.count())
            .select_from(CodeRun)
            .where(CodeRun.user_id == attempt.user_id, CodeRun.status.in_(["queued", "running"]))
        )
        or 0
    )
    recent = (
        db.scalar(
            select(func.count())
            .select_from(CodeRun)
            .where(CodeRun.user_id == attempt.user_id, CodeRun.created_at >= stamp - 86400)
        )
        or 0
    )
    if queued >= settings.execution_queue_limit or recent >= settings.execution_daily_quota:
        raise ExecutionError("execution_quota_exceeded", 429)
    global_pending = (
        db.scalar(
            select(func.count())
            .select_from(CodeRun)
            .where(CodeRun.status.in_(["queued", "running"]))
        )
        or 0
    )
    ip_recent = (
        db.scalar(
            select(func.count())
            .select_from(CodeRun)
            .where(CodeRun.client_key == client_key, CodeRun.created_at >= stamp - 86400)
        )
        or 0
    )
    if (
        global_pending >= settings.execution_global_queue_limit
        or ip_recent >= settings.execution_ip_daily_quota
    ):
        raise ExecutionError("execution_quota_exceeded", 429)
    draft = db.get(CodeDraft, attempt.id)
    assert draft is not None
    if draft.revision != body["draft_revision"]:
        raise ExecutionError("code_draft_stale")
    if not draft.source:
        raise ExecutionError("source_required", 422)
    if body.get("stdin") is not None:
        if mode != "run":
            raise ExecutionError("custom_input_not_allowed", 422)
        tests = [TestInput(input=body["stdin"], visibility="public").model_dump()]
    else:
        tests = [
            TestInput.model_validate(x.model_dump()).model_dump()
            for x in exercise.tests
            if mode == "submit" or x.visibility == "public"
        ]
    if not tests or len(tests) > 100:
        raise ExecutionError("execution_test_bundle_invalid")
    profile = RuntimeProfile.model_validate(attempt.snapshot["runtime"])
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=attempt.id,
        nonce=secrets.token_hex(32),
        issued_at=stamp,
        expires_at=stamp + 600,
        language=profile.language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(draft.source.encode()),
        test_digest=hashed(canonical(tests)),
        pack_digest="sha256:" + pack.digest(),
        mode=mode,
        limits=profile.limits,
        compile_config=COMMANDS[profile.language],
    )
    run = CodeRun(
        id=manifest.job_id,
        attempt_id=attempt.id,
        user_id=attempt.user_id,
        idempotency_key=body["idempotency_key"],
        request_digest=request_digest,
        client_key=client_key,
        manifest=manifest.model_dump(),
        signature=sign(manifest.model_dump(), settings.execution_signing_secret.get_secret_value()),
        tests=tests,
        status="queued",
        created_at=stamp,
    )
    db.add(run)
    db.flush()
    db.add(CodeRunSource(run_id=run.id, source=draft.source))
    if mode == "submit":
        from socrat.models import SubmitAssistance
        from socrat.tutor.service import assistance_level

        db.add(SubmitAssistance(run_id=run.id, hint_level=assistance_level(db, attempt)))
    record_event(db, attempt.user_id, "execution.queued", run.id)
    return run


def run_view(run: CodeRun):
    result = run.result
    public = None
    if result:
        public = dict(
            operational_status=result["operational_status"],
            reason_code=result["reason_code"],
            cases=[
                {
                    **case,
                    "stdout": case["stdout"]
                    if run.tests[case["index"]]["visibility"] == "public"
                    else "",
                    "stderr": case["stderr"]
                    if run.tests[case["index"]]["visibility"] == "public"
                    else "",
                }
                for case in result["cases"]
            ],
        )
    return dict(
        id=run.id,
        status=run.status,
        mode=run.manifest["mode"],
        created_at=run.created_at,
        result=public,
    )


def claim(db: Session, worker_id: str, settings: Settings, stamp: int):
    worker = db.get(ExecutionWorker, worker_id)
    if worker is None or worker.seen_at < stamp - 30:
        raise ExecutionError("worker_capability_expired", 403)
    for stale in db.scalars(
        select(CodeRun)
        .where(CodeRun.status.in_(["queued", "running"]), CodeRun.created_at < stamp - 600)
        .with_for_update(skip_locked=True)
    ):
        stale.status = "failed"
        record_event(db, stale.user_id, "execution.expired", stale.id)
    job = db.scalar(
        select(CodeRun)
        .where(CodeRun.status == "queued", CodeRun.manifest["image"].as_string().in_(worker.images))
        .order_by(CodeRun.created_at, CodeRun.id)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    if job.manifest["image"] not in worker.images:
        return None
    if stamp > job.manifest["expires_at"]:
        job.status = "failed"
        record_event(db, job.user_id, "execution.expired", job.id)
        return None
    job.status, job.worker_id, job.lease_until = "running", worker_id, job.manifest["expires_at"]
    source = db.get(CodeRunSource, job.id)
    assert source is not None
    return JobEnvelope(
        manifest=JobManifest.model_validate(job.manifest),
        signature=job.signature,
        source=source.source,
        tests=[TestInput.model_validate(x) for x in job.tests],
    ).model_dump()


def finalize(db: Session, worker_id: str, envelope: ResultEnvelope, settings: Settings, stamp: int):
    result = envelope.result
    verify(
        result.model_dump(),
        envelope.signature,
        settings.execution_signing_secret.get_secret_value(),
    )
    run = db.get(CodeRun, result.job_id)
    if run is None or run.worker_id != worker_id:
        raise ExecutionError("execution_job_not_owned", 404)
    for field in ("nonce", "code_hash", "test_digest", "image"):
        if getattr(result, field) != run.manifest[field]:
            raise ExecutionError("execution_result_mismatch")
    if run.result is not None:
        if run.result_signature != envelope.signature:
            raise ExecutionError("execution_result_conflict")
        return run
    if run.status != "running" or run.lease_until is None or stamp > run.lease_until:
        raise ExecutionError("execution_lease_expired")
    if result.operational_status == "healthy" and (
        [x.index for x in result.cases] != list(range(len(run.tests)))
        or result.reason_code != "execution_finalized"
    ):
        raise ExecutionError("execution_result_incomplete")
    # Hidden output is removed before any application persistence, not just at rendering.
    sanitized = result.model_dump()
    for case in sanitized["cases"]:
        if case["index"] >= len(run.tests):
            raise ExecutionError("execution_result_mismatch")
        if run.tests[case["index"]]["visibility"] == "hidden":
            case["stdout"], case["stderr"] = "", ""
    attempt = db.get(CodeAttempt, run.attempt_id)
    assert attempt is not None
    try:
        pack, exercise = content(db, attempt)
    except ExecutionError:
        sanitized.update(operational_status="failed", reason_code="content_withdrawn", cases=[])
    if attempt.snapshot["diagnostic_attempt_id"]:
        diagnostic_attempt = db.get(DiagnosticAttempt, attempt.snapshot["diagnostic_attempt_id"])
        diagnostic = (
            db.get(DiagnosticSession, diagnostic_attempt.diagnostic_id)
            if diagnostic_attempt
            else None
        )
        latest = (
            db.scalar(
                select(DiagnosticAttempt)
                .where(DiagnosticAttempt.diagnostic_id == diagnostic.id)
                .order_by(DiagnosticAttempt.position.desc())
                .limit(1)
            )
            if diagnostic
            else None
        )
        if (
            diagnostic is None
            or diagnostic.status != "in_progress"
            or diagnostic.result is not None
            or stamp >= diagnostic.deadline_at
            or latest is None
            or latest.id != attempt.snapshot["diagnostic_attempt_id"]
            or db.get(DiagnosticResponse, attempt.snapshot["diagnostic_attempt_id"]) is not None
        ):
            sanitized.update(operational_status="failed", reason_code="lease_expired", cases=[])
    run.result = sanitized
    run.result_signature = envelope.signature
    run.status = "completed" if sanitized["operational_status"] == "healthy" else "failed"
    if run.manifest["mode"] == "submit" and run.status == "completed":
        score = sum(x.status == "passed" for x in result.cases) / len(run.tests)
        evaluation = implementation_score(
            VerifiedImplementationResult(
                attempt_id=attempt.id,
                runtime_digest=run.manifest["image"].split("@")[-1],
                test_digest=run.manifest["test_digest"],
                operational_status="healthy",
                finalized=True,
                signature_verified=True,
                score=score,
            ),
            attempt.id,
            run.manifest["image"].split("@")[-1],
            run.manifest["test_digest"],
        )
        state = db.get(LearnerState, attempt.user_id)
        version = state.active_policy if state else "1.0.0"
        facts = facts_for(db, attempt.user_id)
        goal = db.get(LearnerGoal, attempt.goal_id)
        assert goal is not None
        from socrat.learning.admission import solve_seconds

        learner_seconds = solve_seconds(db, attempt, run.created_at)
        from socrat.tutor.service import submitted_level

        fact = EvidenceFact(
            event_id=identifier(),
            user_id=attempt.user_id,
            goal_id=attempt.goal_id,
            track=goal.snapshot["declared_track"],
            sequence=len(facts) + 1,
            source_id=attempt.snapshot["diagnostic_attempt_id"] or attempt.id,
            pack_id=attempt.pack_id,
            pack_digest=pack.digest(),
            language=attempt.snapshot["language"],
            concept_ids=exercise.concept_ids,
            mode=attempt.snapshot["mode"],
            evidence_type="implement",
            family_id=exercise.family_id,
            score=score,
            quality=evaluation.quality,
            hint_level=submitted_level(db, run, attempt),
            elapsed_seconds=learner_seconds
            if learner_seconds is not None
            else float(min(2700, stamp - attempt.created_at)),
            expected_seconds=float(exercise.estimated_minutes * 60),
            difficulty=exercise.difficulty,
            valid=True,
            unseen=attempt.snapshot["unseen"],
            finalized=True,
            occurred_at=stamp,
            scoring_version=evaluation.scoring_version,
            policy_version=version,
            policy_digest=digest(POLICIES[version].model_dump()),
            reason_code=evaluation.reason_code,
        )
        append_fact(db, attempt.user_id, fact)
        if attempt.snapshot["diagnostic_attempt_id"]:
            from socrat.diagnostics.service import select_next

            diagnostic_attempt = db.get(
                DiagnosticAttempt, attempt.snapshot["diagnostic_attempt_id"]
            )
            assert diagnostic_attempt is not None
            diagnostic = db.get(DiagnosticSession, diagnostic_attempt.diagnostic_id)
            assert diagnostic is not None
            db.add(
                DiagnosticResponse(
                    attempt_id=diagnostic_attempt.id,
                    diagnostic_id=diagnostic.id,
                    idempotency_key=run.id,
                    request_digest=digest(run.manifest),
                    answer_digest=run.manifest["code_hash"].split(":")[-1],
                    outcome=evaluation.model_dump(),
                    created_at=stamp,
                )
            )
            diagnostic.revision += 1
            definition = next(
                x for x in pack.diagnostics if x.blueprint_id == diagnostic.blueprint_id
            )
            db.flush()
            db.info["execution_settings"] = settings
            select_next(db, diagnostic, pack, definition, stamp)
    record_event(db, run.user_id, "execution.finalized", run.id)
    return run
