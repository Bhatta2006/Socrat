"""Broker admission for immutable session-bound attempts. No execution dependency."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from socrat.models import CurriculumHead, LearnerGoal, LearningSession, SessionCommand


def admission_error(db, attempt, stamp, enabled=True) -> str | None:
    context = attempt.snapshot.get("learning_context")
    if context is None:  # Existing standalone/diagnostic and historical M7 attempts.
        return None
    if not enabled:
        return "learning_sessions_unavailable"
    session = db.get(LearningSession, context["session_id"])
    if (
        session is None
        or session.user_id != attempt.user_id
        or session.goal_id != attempt.goal_id
        or session.pack_id != attempt.pack_id
    ):
        return "session_attempt_mismatch"
    goal = db.get(LearnerGoal, session.goal_id)
    head = db.get(CurriculumHead, session.goal_id)
    if head is None or head.status != "confirmed":
        return "reviewed_plan_required"
    if session.status != "in_progress":
        return "session_not_active"
    day = (
        datetime.fromtimestamp(stamp, ZoneInfo(goal.snapshot["goal"]["timezone"]))
        .date()
        .isoformat()
    )
    if day != session.local_date:
        return "session_day_ended"
    index = context["block_index"]
    block, step = session.snapshot["blocks"][index], session.progress[index]
    if step["status"] != "available" or block["mode"] != "independent":
        return "session_block_locked"
    if context["phase"] == "upsolve":
        if step.get("phase") != "upsolve" or step.get("upsolve_attempt_id") != attempt.id:
            return "session_attempt_mismatch"
    elif step.get("phase") == "upsolve" or step.get("attempt_id") != attempt.id:
        return "session_attempt_mismatch"
    elif block["timed"]:
        if "deadline_at" not in step:
            return "timed_block_not_started"
        if stamp >= step["deadline_at"]:
            return "timed_window_ended"
    return None


def solve_seconds(db, attempt, submitted_at) -> float | None:
    """Measure learner work at admission, excluding queue/worker latency and pauses."""
    context = attempt.snapshot.get("learning_context")
    if context is None:
        return None
    session = db.get(LearningSession, context["session_id"])
    if session is None:
        return None
    receipt = db.scalar(
        select(SessionCommand)
        .where(
            SessionCommand.session_id == session.id,
            SessionCommand.created_at <= submitted_at,
        )
        .order_by(SessionCommand.outcome["revision"].as_integer().desc())
        .limit(1)
    )
    step = (
        receipt.outcome["blocks"][context["block_index"]]
        if receipt
        else session.progress[context["block_index"]]
    )
    if context["phase"] == "independent" and "timed_started_at" in step:
        seconds = submitted_at - step["timed_started_at"]
    else:
        seconds = (
            step.get("active_seconds", 0)
            - step.get("timed_active_seconds", 0)
            + max(0, submitted_at - step.get("started_at", submitted_at))
        )
    return float(min(2700, max(0, seconds)))
