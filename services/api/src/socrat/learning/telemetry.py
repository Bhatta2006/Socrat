"""Versioned learner-owned participation export; no response/source artifacts."""

from statistics import median

from sqlalchemy import select

from socrat.diagnostics.service import result_view
from socrat.learnerstate.service import facts_for
from socrat.learning.service import day_end
from socrat.models import (
    CodeRun,
    DiagnosticSession,
    LearningSession,
    PlanningCommand,
    SkillPackVersion,
)


def valid_facts(db, goal):
    facts = facts_for(db, goal.user_id)
    invalidated = {x.target_event_id for x in facts if x.kind == "invalidated"}
    return [
        x
        for x in facts
        if x.kind == "scored"
        and x.goal_id == goal.id
        and x.valid
        and x.finalized
        and x.event_id not in invalidated
        and x.mode in {"practice", "retention"}
    ]


def session_summary(db, goal, session, stamp, facts=None):
    facts = valid_facts(db, goal) if facts is None else facts
    record = db.get(SkillPackVersion, session.pack_id)
    available = record is not None and record.status == "released"
    attempt_ids = {
        key
        for step in session.progress
        for key in (step.get("attempt_id"), step.get("upsolve_attempt_id"))
        if key
    }
    meaningful = available and any(x.source_id in attempt_ids for x in facts)
    expired = session.status in {"in_progress", "paused"} and stamp >= day_end(goal, session)
    planned = sum(x["minutes"] for x in session.snapshot["blocks"])
    # Optional repair allocations are only actual plan burden when repair is used.
    planned += sum(
        block.get("upsolve_minutes", 0)
        for block, step in zip(session.snapshot["blocks"], session.progress, strict=True)
        if step.get("phase") == "upsolve"
    )
    active = sum(x.get("active_seconds", 0) for x in session.progress)
    normal = not any(x["timed"] for x in session.snapshot["blocks"])
    duration = (
        abs(active / 60 - planned) / planned
        if session.status == "completed" and normal and available and planned
        else None
    )
    return dict(
        id=session.id,
        local_date=session.local_date,
        status="expired" if expired else session.status,
        track=session.snapshot["track"],
        language=session.snapshot["language"],
        meaningful=bool(meaningful),
        content_available=available,
        active_seconds=active,
        planned_minutes=planned,
        duration_error=duration,
        can_resume=session.status == "paused" and not expired and available,
        recovery_required=expired or session.status in {"expired", "abandoned"},
    )


def export_sessions(db, goal, stamp):
    sessions = db.scalars(
        select(LearningSession)
        .where(LearningSession.goal_id == goal.id)
        .order_by(LearningSession.local_date, LearningSession.id)
    ).all()
    facts = valid_facts(db, goal)
    rows = [session_summary(db, goal, x, stamp, facts) for x in sessions]
    independent_ids = {
        step["attempt_id"]
        for session in sessions
        for step in session.progress
        if "attempt_id" in step
    }
    released = {
        x.pack_id
        for x in sessions
        if (record := db.get(SkillPackVersion, x.pack_id)) and record.status == "released"
    }
    valid_independent_ids = {
        x.source_id
        for x in facts
        if x.source_id in independent_ids and x.hint_level == 0 and x.pack_id in released
    }
    first = db.scalar(
        select(CodeRun.created_at)
        .where(
            CodeRun.attempt_id.in_(valid_independent_ids),
            CodeRun.user_id == goal.user_id,
            CodeRun.manifest["mode"].as_string() == "submit",
            CodeRun.status == "completed",
            CodeRun.result_signature.is_not(None),
        )
        .order_by(CodeRun.created_at)
        .limit(1)
    )
    diagnostic = db.scalar(select(DiagnosticSession).where(DiagnosticSession.goal_id == goal.id))
    confirmed = db.scalar(
        select(PlanningCommand)
        .where(
            PlanningCommand.goal_id == goal.id,
            PlanningCommand.outcome["status"].as_string() == "confirmed",
        )
        .order_by(PlanningCommand.created_at)
        .limit(1)
    )
    diagnostic_result = result_view(db, diagnostic) if diagnostic is not None else None
    prerequisites = (
        diagnostic is not None
        and diagnostic.result is not None
        and diagnostic.status == "completed"
        and diagnostic_result is not None
        and diagnostic_result["evidence_current"]
        and confirmed is not None
        and first is not None
        and confirmed.created_at <= first
    )
    errors = [x["duration_error"] for x in rows if x["duration_error"] is not None]
    return dict(
        version="m7_participation_1.0.0",
        scope="owned_goal",
        as_of=stamp,
        activation=dict(
            definition="diagnostic_plan_independent_submit_1.0.0",
            window_anchor="goal_confirmation",
            window_seconds=48 * 3600,
            first_independent_submit_at=first,
            activated=bool(
                prerequisites
                and first is not None
                and goal.confirmation_at <= first <= goal.confirmation_at + 48 * 3600
            ),
        ),
        meaningful_sessions=sum(x["meaningful"] for x in rows),
        duration=dict(
            samples=len(errors),
            median_error=median(errors) if errors else None,
            calibrated=False,
        ),
        sessions=rows,
    )
