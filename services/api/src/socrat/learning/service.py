"""Owned, version-pinned session transitions. Completion is not mastery."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.execution.service import create_attempt, create_upsolve_attempt
from socrat.learnerstate.policy import digest
from socrat.learnerstate.service import facts_for
from socrat.learning.contracts import SessionAction
from socrat.models import (
    CodeAttempt,
    CodeRun,
    CurriculumHead,
    LearnerState,
    LearningSession,
    SessionCommand,
    SkillPackHead,
    SkillPackVersion,
    identifier,
    now,
)
from socrat.planning.service import current
from socrat.skillpacks.service import load


class SessionError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status


def local_day(goal, stamp):
    return (
        datetime.fromtimestamp(stamp, ZoneInfo(goal.snapshot["goal"]["timezone"]))
        .date()
        .isoformat()
    )


def session_content(db: Session, session: LearningSession):
    record = db.get(SkillPackVersion, session.pack_id)
    if record is None:
        raise SessionError("session_content_unavailable")
    db.scalar(
        select(SkillPackHead).where(SkillPackHead.pack_key == record.pack_key).with_for_update()
    )
    db.refresh(record)
    pack = load(record)
    if record.status != "released" or pack.digest() != session.snapshot["pack_digest"]:
        raise SessionError("session_content_unavailable")
    return pack


def timed_outcome(db, step, stamp):
    run = (
        db.scalar(
            select(CodeRun)
            .where(
                CodeRun.attempt_id == step.get("attempt_id"),
                CodeRun.manifest["mode"].as_string() == "submit",
            )
            .order_by(CodeRun.created_at.desc(), CodeRun.id)
            .limit(1)
        )
        if step.get("attempt_id")
        else None
    )
    if run is not None:
        if run.status in {"queued", "running"}:
            return dict(outcome="pending", run_id=run.id)
        if (
            run.status == "completed"
            and run.result
            and run.result["operational_status"] == "healthy"
        ):
            score = sum(x["status"] == "passed" for x in run.result["cases"]) / len(run.tests)
            eligible = step["timed_started_at"] <= run.created_at < step["deadline_at"]
            return dict(
                outcome="solved" if score == 1 and eligible else "unsuccessful",
                run_id=run.id,
                score=score,
                eligible=eligible,
                submitted_at=run.created_at,
            )
        if run.status == "failed":
            return dict(outcome="unscored_operational_failure", run_id=run.id)
    return dict(outcome="timed_out" if stamp >= step["deadline_at"] else "awaiting_submission")


def view(db: Session, session: LearningSession, stamp: int | None = None):
    stamp = now() if stamp is None else stamp
    pack = session_content(db, session)
    concepts = {x.id: x for x in pack.concepts}
    exercises = {x.id: x for x in pack.exercises}
    blocks = []
    for block, progress in zip(session.snapshot["blocks"], session.progress, strict=True):
        content = dict(prompt="", explanations=[], examples=[])
        if progress["status"] != "locked":
            selected = [concepts[key] for key in block["concept_ids"]]
            if block["mode"] == "instruction":
                content.update(explanations=[x.explanation for x in selected])
            elif block["mode"] == "guided":
                content.update(examples=[item for x in selected for item in x.examples])
                content["prompt"] = "Trace the example and describe each change in state."
            elif block["mode"] == "retrieval":
                content["prompt"] = "Recall what you know about: " + "; ".join(
                    x.competency for x in selected
                )
            elif block["mode"] == "exit_check":
                content["prompt"] = (
                    "Explain your approach, why it works, and what made this task difficult."
                )
            else:
                exercise = exercises[block["exercise_ids"][0]]
                content["prompt"] = exercise.statement
        value = dict(**block, **progress, content=content)
        if progress.get("phase") == "upsolve":
            value.update(mode="upsolve", timed=False, attempt_id=progress.get("upsolve_attempt_id"))
        elif block["timed"] and "deadline_at" in progress:
            value["timed_outcome"] = progress.get("timed_outcome") or timed_outcome(
                db, progress, stamp
            )
        blocks.append(value)
    value = dict(
        id=session.id,
        goal_id=session.goal_id,
        local_date=session.local_date,
        revision=session.revision,
        status=session.status,
        curriculum_revision=session.snapshot["curriculum_revision"],
        track=session.snapshot["track"],
        language=session.snapshot["language"],
        planned_minutes=sum(x["minutes"] for x in session.snapshot["blocks"]),
        active_seconds=sum(x.get("active_seconds", 0) for x in session.progress),
        completed_at=session.completed_at,
        blocks=blocks,
        completion_scope="learning_participation",
        mastery_claim=False,
        timing=session.snapshot.get("timing", "standard"),
    )
    if any(x["timed"] and x["status"] == "available" for x in blocks):
        value["server_now"] = stamp
    return value


def start(db, goal, revision, settings, stamp, timing="standard"):
    day = local_day(goal, stamp)
    existing = db.scalar(
        select(LearningSession).where(
            LearningSession.goal_id == goal.id,
            LearningSession.local_date == day,
        )
    )
    if existing:
        if timing != existing.snapshot.get("timing", "standard"):
            raise SessionError("session_timing_already_chosen")
        return view(db, existing, stamp)
    plan = current(db, goal)
    if plan["status"] != "confirmed" or plan["revision"] != revision:
        raise SessionError("reviewed_plan_required")
    state = db.get(LearnerState, goal.user_id)
    if len(facts_for(db, goal.user_id)) != plan["evidence_watermark"] or (
        state and state.active_policy != plan["learning_policy_version"]
    ):
        raise SessionError("plan_evidence_stale")
    planned = next((x for x in plan["days"] if x["date"] == day), None)
    if planned is None or not planned["blocks"]:
        raise SessionError("no_session_today")
    blocks = [{**x, "timed": x["timed"] and timing == "standard"} for x in planned["blocks"]]
    progress = [
        dict(status="available" if i == 0 else "locked", active_seconds=0)
        for i in range(len(blocks))
    ]
    session_id = identifier()
    # Allocate a fresh independent attempt now, before its own Submit changes the
    # evidence watermark. Browser history must never attach another session's work.
    for index, (block, step) in enumerate(zip(blocks, progress, strict=True)):
        if block["mode"] == "independent" and block["modality"] == "code":
            attempt = create_attempt(
                db,
                goal,
                block["exercise_ids"][0],
                "session_" + session_id,
                None,
                settings,
                stamp,
                learning_context=dict(
                    session_id=session_id, block_index=index, phase="independent"
                ),
            )
            if attempt.pack_id != plan["pack_id"]:
                raise SessionError("session_content_unavailable")
            step["attempt_id"] = attempt.id
    progress[0]["started_at"] = stamp
    session = LearningSession(
        id=session_id,
        user_id=goal.user_id,
        goal_id=goal.id,
        curriculum_id=plan["id"],
        pack_id=plan["pack_id"],
        local_date=day,
        snapshot=dict(
            blocks=blocks,
            pack_digest=plan["pack_digest"],
            curriculum_revision=revision,
            track=plan["active_track"],
            language=plan["schedule"]["language"],
            timing=timing,
        ),
        progress=progress,
        status="in_progress",
        revision=0,
        created_at=stamp,
    )
    db.add(session)
    db.flush()
    record_event(db, goal.user_id, "learning.session_started", session.id)
    return view(db, session, stamp)


def command(db, goal, session, body: SessionAction, stamp, settings=None):
    request_digest = digest(body.model_dump())
    receipt = db.scalar(
        select(SessionCommand).where(
            SessionCommand.session_id == session.id,
            SessionCommand.idempotency_key == body.idempotency_key,
        )
    )
    if receipt:
        if receipt.request_digest != request_digest:
            raise SessionError("idempotency_key_reused")
        session_content(db, session)
        return receipt.outcome
    session_content(db, session)
    if session.revision != body.expected_revision:
        raise SessionError("session_revision_stale")
    if session.status in {"completed", "abandoned", "expired"}:
        raise SessionError("session_transition_invalid")
    if local_day(goal, stamp) != session.local_date:
        raise SessionError("session_day_ended")
    head = db.get(CurriculumHead, goal.id)
    if head is None or head.status != "confirmed":
        raise SessionError("reviewed_plan_required")
    progress = [dict(x) for x in session.progress]
    index = next(i for i, x in enumerate(progress) if x["status"] == "available")
    step, block = progress[index], session.snapshot["blocks"][index]
    if body.action != "advance" and any(
        x is not None for x in (body.answer, body.run_id, body.reflection)
    ):
        raise SessionError("unexpected_session_response", 422)
    if body.action != "upsolve" and body.error_classification is not None:
        raise SessionError("unexpected_session_response", 422)
    timed = block["timed"] and step.get("phase") != "upsolve"
    if body.action == "start_timed":
        if (
            session.status != "in_progress"
            or not timed
            or block["mode"] != "independent"
            or "deadline_at" in step
        ):
            raise SessionError("session_transition_invalid")
        step.update(
            timed_started_at=stamp,
            deadline_at=stamp + block["minutes"] * 60,
            started_at=stamp,
            active_seconds=0,
        )
    elif body.action == "upsolve":
        if session.status != "in_progress" or not timed or "deadline_at" not in step:
            raise SessionError("session_transition_invalid")
        if body.error_classification is None:
            raise SessionError("error_classification_required", 422)
        outcome = timed_outcome(db, step, stamp)
        if outcome["outcome"] == "pending":
            raise SessionError("timed_submit_pending")
        if outcome["outcome"] == "solved":
            raise SessionError("upsolve_not_required")
        if stamp < step["deadline_at"] and outcome["outcome"] not in {
            "unsuccessful",
            "unscored_operational_failure",
        }:
            raise SessionError("timed_window_active")
        if block["modality"] == "code":
            parent = db.get(CodeAttempt, step["attempt_id"])
            if settings is None:
                raise SessionError("sandbox_unavailable", 503)
            attempt = create_upsolve_attempt(db, parent, session.id, index, settings, stamp)
            step["upsolve_attempt_id"] = attempt.id
        step["active_seconds"] += max(
            0, min(stamp, step["deadline_at"]) - step.get("started_at", stamp)
        )
        step.update(
            phase="upsolve",
            timed_outcome=outcome,
            timed_active_seconds=step["active_seconds"],
            error_classification=body.error_classification,
            started_at=stamp,
        )
        record_event(db, session.user_id, "learning.upsolve_started", session.id)
    elif body.action == "resume":
        if session.status != "paused":
            raise SessionError("session_transition_invalid")
        session.status = "in_progress"
        step["started_at"] = stamp
    else:
        if session.status != "in_progress":
            raise SessionError("session_transition_invalid")
        if body.action == "pause" and timed and "deadline_at" in step:
            raise SessionError("timed_block_cannot_pause")
        interval_end = min(stamp, step["deadline_at"]) if timed and "deadline_at" in step else stamp
        step["active_seconds"] += max(0, interval_end - step.get("started_at", stamp))
        step.pop("started_at", None)
        if body.action == "pause":
            session.status = "paused"
        elif body.action == "abandon":
            session.status = "abandoned"
        else:
            if timed and "deadline_at" not in step:
                raise SessionError("timed_block_not_started")
            if block["mode"] == "independent" and block["modality"] == "code":
                run = db.get(CodeRun, body.run_id) if body.run_id else None
                if (
                    run is None
                    or run.user_id != session.user_id
                    or run.attempt_id != step.get("upsolve_attempt_id", step.get("attempt_id"))
                    or run.manifest["mode"] != "submit"
                    or run.status != "completed"
                    or not run.result_signature
                    or not run.result
                    or run.result["operational_status"] != "healthy"
                ):
                    raise SessionError("verified_submit_required")
                if timed:
                    outcome = timed_outcome(db, step, stamp)
                    if outcome["outcome"] != "solved" or outcome.get("run_id") != run.id:
                        raise SessionError("upsolve_required")
                    step["timed_outcome"] = outcome
                step.update(run_id=run.id, scoring="verified_implementation")
                if body.answer is not None:
                    raise SessionError("unexpected_session_response", 422)
            elif block["mode"] != "instruction":
                if timed and stamp >= step["deadline_at"]:
                    raise SessionError("timed_window_ended")
                if not body.answer:
                    raise SessionError("session_response_required", 422)
                step.update(answer=body.answer, scoring="ungraded")
                if timed:
                    step["timed_outcome"] = dict(outcome="ungraded_submission", submitted_at=stamp)
            elif body.answer is not None:
                raise SessionError("unexpected_session_response", 422)
            if block["mode"] == "exit_check":
                if body.reflection is None:
                    raise SessionError("reflection_required", 422)
                step["reflection"] = body.reflection
            elif body.reflection is not None:
                raise SessionError("unexpected_session_response", 422)
            if body.run_id is not None and not (
                block["mode"] == "independent" and block["modality"] == "code"
            ):
                raise SessionError("unexpected_session_response", 422)
            step.update(status="submitted", submitted_at=stamp)
            if index + 1 < len(progress):
                progress[index + 1].update(status="available", started_at=stamp)
            else:
                session.status, session.completed_at = "completed", stamp
                record_event(db, session.user_id, "learning.session_completed", session.id)
            record_event(db, session.user_id, "learning.block_submitted", session.id)
    session.progress, session.revision = progress, session.revision + 1
    outcome = view(db, session, stamp)
    db.add(
        SessionCommand(
            session_id=session.id,
            idempotency_key=body.idempotency_key,
            request_digest=request_digest,
            outcome=outcome,
            created_at=stamp,
        )
    )
    record_event(db, session.user_id, "learning.session_" + body.action, session.id)
    return outcome
