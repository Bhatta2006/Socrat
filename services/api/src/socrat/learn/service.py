"""Turn evidence into learner state, plans, streaks and today's agenda.

All writes here happen inside the caller's transaction; nothing commits on its own.
"""

import hashlib
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.database import record_event
from socrat.mastery import model as mastery
from socrat.models import (
    ActivityRecord,
    DailyActivity,
    Enrollment,
    Evidence,
    PlanRevision,
    User,
)
from socrat.models import ConceptState as ConceptRow
from socrat.planner.engine import Plan, build_plan, concept_activities

MAX_ACTIVITY_SECONDS = 90 * 60


def local_now(user: User, now: int) -> datetime:
    return datetime.fromtimestamp(now, ZoneInfo(user.timezone))


def local_day(user: User, now: int) -> date:
    return local_now(user, now).date()


def active_enrollment(db: Session, user_id: str) -> Enrollment | None:
    return db.scalar(
        select(Enrollment)
        .where(Enrollment.user_id == user_id, Enrollment.active.is_(True))
        .order_by(Enrollment.created_at.desc())
    )


def require_enrollment(db: Session, user_id: str) -> Enrollment:
    enrollment = active_enrollment(db, user_id)
    if enrollment is None:
        raise HTTPException(404, "no_active_enrollment")
    return enrollment


def states_for(db: Session, enrollment: Enrollment) -> dict[str, mastery.ConceptState]:
    rows = db.scalars(select(ConceptRow).where(ConceptRow.enrollment_id == enrollment.id))
    return {row.concept: mastery.ConceptState.from_dict(row.state) for row in rows}


def completed_for(db: Session, enrollment: Enrollment) -> set[str]:
    return set(
        db.scalars(
            select(ActivityRecord.activity_id).where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.completed_at.is_not(None),
            )
        )
    )


def history_for(db: Session, enrollment: Enrollment, limit: int = 40) -> list[dict]:
    rows = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.enrollment_id == enrollment.id)
            .order_by(Evidence.created_at.desc(), Evidence.id.desc())
            .limit(limit)
        )
    )
    return [
        dict(
            kind=row.kind,
            score=row.score,
            assistance=row.assistance,
            elapsed_seconds=row.elapsed_seconds,
            expected_seconds=row.expected_seconds,
            concept=row.concept,
        )
        for row in reversed(rows)
    ]


def set_state(
    db: Session, enrollment: Enrollment, concept: str, state: mastery.ConceptState, now: int
):
    row = db.get(ConceptRow, (enrollment.id, concept))
    if row is None:
        db.add(ConceptRow(enrollment_id=enrollment.id, concept=concept, state=state.to_dict()))
    else:
        row.state = state.to_dict()
        row.updated_at = now


def record_evidence(
    db: Session,
    enrollment: Enrollment,
    concept: str,
    kind: mastery.EvidenceKind,
    score: float,
    activity_id: str,
    now: int,
    assistance: int = 0,
    elapsed_seconds: int = 0,
    expected_seconds: int = 0,
) -> mastery.ConceptState:
    row = db.get(ConceptRow, (enrollment.id, concept))
    before = mastery.ConceptState.from_dict(row.state if row else None)
    after = mastery.apply(before, kind, score, now, assistance)
    set_state(db, enrollment, concept, after, now)
    db.add(
        Evidence(
            enrollment_id=enrollment.id,
            concept=concept,
            kind=kind,
            score=score,
            assistance=assistance,
            activity_id=activity_id,
            elapsed_seconds=elapsed_seconds,
            expected_seconds=expected_seconds,
            created_at=now,
        )
    )
    return after


def start_activity(
    db: Session, enrollment: Enrollment, activity_id: str, now: int
) -> ActivityRecord:
    record = db.get(ActivityRecord, (enrollment.id, activity_id))
    if record is None:
        record = ActivityRecord(
            enrollment_id=enrollment.id, activity_id=activity_id, started_at=now
        )
        db.add(record)
        db.flush()
    elif record.completed_at is None and now - record.started_at > MAX_ACTIVITY_SECONDS:
        record.started_at = now  # A stale attempt restarts the clock.
    return record


def elapsed(db: Session, enrollment: Enrollment, activity_id: str, now: int) -> int:
    record = db.get(ActivityRecord, (enrollment.id, activity_id))
    if record is None:
        return 0
    return max(0, min(MAX_ACTIVITY_SECONDS, now - record.started_at))


def expected_seconds(catalog: Catalog, activity_id: str, enrollment: Enrollment) -> int:
    kind, _, target = activity_id.partition(":")
    if kind in {"review", "remedial"}:
        return 5 * 60 if kind == "review" else 15 * 60
    if kind == "checkpoint":
        return 15 * 60
    if kind == "problem":
        course_id, problem = catalog.problems[target]
        concept = f"{course_id}:{problem.concepts[0]}"
    else:
        concept = target
    for activity in concept_activities(catalog, concept, mastery.ConceptState(), "steady"):
        if activity.id == activity_id:
            return activity.minutes * 60
    return 15 * 60


def complete_activity(
    db: Session,
    user: User,
    enrollment: Enrollment,
    activity_id: str,
    now: int,
    outcome: dict | None = None,
    solved: bool = False,
) -> bool:
    """Mark complete once; returns False when it was already complete."""
    record = start_activity(db, enrollment, activity_id, now)
    if record.completed_at is not None:
        return False
    record.completed_at = now
    record.outcome = outcome or {}
    minutes = max(1, round(min(MAX_ACTIVITY_SECONDS, now - record.started_at) / 60))
    bump_daily(db, user, now, minutes=minutes, solved=int(solved))
    record_event(db, user.id, "activity.completed")
    return True


def bump_daily(db: Session, user: User, now: int, minutes: int = 0, solved: int = 0):
    day = local_day(user, now).isoformat()
    row = db.get(DailyActivity, (user.id, day))
    if row is None:
        row = DailyActivity(user_id=user.id, day=day, activities=0, minutes=0, solved=0)
        db.add(row)
    row.activities += 1
    row.minutes += minutes
    row.solved += solved


def streak(db: Session, user: User, enrollment: Enrollment, now: int) -> dict:
    """Consecutive scheduled study days with activity; rest days never break a streak."""
    today = local_day(user, now)
    days = {
        date.fromisoformat(d)
        for d in db.scalars(select(DailyActivity.day).where(DailyActivity.user_id == user.id))
    }
    weekdays = set(enrollment.weekdays)
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    start = date.fromtimestamp(enrollment.created_at) - timedelta(days=1)
    while cursor >= start:
        if cursor in days:
            current += 1
        elif cursor.weekday() in weekdays:
            break
        cursor -= timedelta(days=1)
    longest = run = 0
    if days:
        cursor = min(days)
        while cursor <= today:
            if cursor in days:
                run += 1
                longest = max(longest, run)
            elif cursor.weekday() in weekdays:
                run = 0
            cursor += timedelta(days=1)
    return {"current": current, "longest": max(longest, current), "studied_today": today in days}


def plan_for(db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int) -> Plan:
    plan = build_plan(
        catalog,
        catalog.course_concepts(enrollment.course_id),
        states_for(db, enrollment),
        completed_for(db, enrollment),
        history_for(db, enrollment),
        local_day(user, now),
        now,
        set(enrollment.weekdays),
        enrollment.minutes_per_day,
    )
    signature = hashlib.sha256(
        json.dumps([plan.pace, [a.id for a in plan.queue[:12]]], sort_keys=True).encode()
    ).hexdigest()
    if signature != enrollment.plan_signature:
        previous = db.scalar(
            select(PlanRevision)
            .where(PlanRevision.enrollment_id == enrollment.id)
            .order_by(PlanRevision.created_at.desc())
        )
        reasons = list(plan.reasons)
        if previous is None:
            reasons = ["Your personalised path is ready.", *reasons]
        elif previous.pace != plan.pace:
            reasons = [plan.pace_reason, *reasons]
        db.add(
            PlanRevision(
                enrollment_id=enrollment.id,
                pace=plan.pace,
                reasons=reasons or ["Plan adjusted to your latest progress."],
                remaining_minutes=plan.remaining_minutes,
                projected_finish=plan.projected_finish,
                created_at=now,
            )
        )
        enrollment.plan_signature = signature
    return plan


def latest_revisions(db: Session, enrollment: Enrollment, limit: int = 5) -> list[dict]:
    rows = db.scalars(
        select(PlanRevision)
        .where(PlanRevision.enrollment_id == enrollment.id)
        .order_by(PlanRevision.created_at.desc())
        .limit(limit)
    )
    return [
        dict(
            pace=row.pace,
            reasons=row.reasons,
            projected_finish=row.projected_finish,
            remaining_minutes=row.remaining_minutes,
            at=row.created_at,
        )
        for row in rows
    ]


def completed_today(db: Session, user: User, enrollment: Enrollment, now: int) -> list[str]:
    midnight = local_now(user, now).replace(hour=0, minute=0, second=0, microsecond=0)
    return list(
        db.scalars(
            select(ActivityRecord.activity_id)
            .where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.completed_at >= int(midnight.timestamp()),
            )
            .order_by(ActivityRecord.completed_at)
        )
    )


def evidence_counts(db: Session, enrollment: Enrollment) -> dict:
    rows = db.execute(
        select(Evidence.kind, Evidence.assistance, Evidence.score, func.count())
        .where(Evidence.enrollment_id == enrollment.id)
        .group_by(Evidence.kind, Evidence.assistance, Evidence.score)
    ).all()
    independent = sum(c for kind, a, s, c in rows if kind == "code" and s >= 1 and a == 0)
    assisted = sum(c for kind, a, s, c in rows if kind == "code" and s >= 1 and a > 0)
    return {"independent_solves": independent, "assisted_solves": assisted}
