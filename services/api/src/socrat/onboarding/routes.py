from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.database import record_event
from socrat.models import LearnerGoal, OutboxEvent, SkillPackHead, SkillPackVersion, User, now
from socrat.onboarding.policy import GoalInput, digest, route
from socrat.skillpacks.routes import require_admin
from socrat.skillpacks.schema import Contract
from socrat.skillpacks.service import load

router = APIRouter(prefix="/api/v1/onboarding")


class Confirmation(Contract):
    goal: GoalInput
    review_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed: bool
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


def identity(request: Request, db: Session, write: bool = False) -> User:
    if not request.app.state.settings.onboarding_enabled:
        raise HTTPException(404, "not_found")
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "authentication_required")
    return user


def preview(db: Session, user: User, goal: GoalInput, lock: bool = False) -> dict:
    heads = select(SkillPackHead).order_by(SkillPackHead.pack_key)
    if lock:
        heads = heads.with_for_update()
    packs = []
    for head in db.scalars(heads):
        record = db.get(SkillPackVersion, head.active_id) if head.active_id else None
        if record and record.status == "released":
            pack = load(record)
            if pack.purpose == "launch":
                packs.append(pack)
    snapshot = route(
        goal,
        user.adult_confirmed,
        packs,
        datetime.fromtimestamp(now(), ZoneInfo(goal.timezone)).date(),
    )
    return {**snapshot, "review_digest": digest({"user_id": user.id, "snapshot": snapshot})}


def view(record: LearnerGoal) -> dict:
    return {
        "id": record.id,
        **record.snapshot,
        "confirmation_at": datetime.fromtimestamp(record.confirmation_at, UTC).isoformat(),
    }


@router.post("/preview")
def review_goal(body: GoalInput, request: Request):
    with Session(request.app.state.engine) as db:
        user = identity(request, db, write=True)
        return preview(db, user, body)


@router.post("/confirm")
def confirm_goal(body: Confirmation, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user = identity(request, db, write=True)
            if not body.reviewed:
                raise HTTPException(422, "goal_review_required")
            existing = db.scalar(
                select(LearnerGoal).where(
                    LearnerGoal.user_id == user.id,
                    LearnerGoal.idempotency_key == body.idempotency_key,
                )
            )
            if existing:
                if (
                    existing.review_digest != body.review_digest
                    or existing.snapshot["goal"] != body.goal.model_dump()
                ):
                    raise HTTPException(409, "idempotency_key_reused")
                return view(existing)
            snapshot = preview(db, user, body.goal, lock=True)
            if snapshot["review_digest"] != body.review_digest:
                raise HTTPException(409, "goal_review_stale")
            if snapshot["routing_outcome"] == "ineligible":
                raise HTTPException(422, snapshot["reason_codes"][0])
            record = LearnerGoal(
                user_id=user.id,
                idempotency_key=body.idempotency_key,
                review_digest=body.review_digest,
                snapshot=snapshot,
            )
            db.add(record)
            db.flush()
            record_event(db, user.id, "goal.created", record.id)
            record_event(db, user.id, "route.confirmed", record.id)
            return view(record)
    except IntegrityError as exc:
        raise HTTPException(409, "concurrent_goal_confirmation_retry") from exc


@router.get("/goals")
def own_goals(request: Request):
    with Session(request.app.state.engine) as db:
        user = identity(request, db)
        records = db.scalars(
            select(LearnerGoal)
            .where(LearnerGoal.user_id == user.id)
            .order_by(LearnerGoal.confirmation_at.desc(), LearnerGoal.id)
            .limit(100)
        )
        return {"items": [view(record) for record in records]}


@router.get("/reconciliation")
def reconciliation(request: Request):
    """Compare committed goals with exactly one event of each kind, including retry duplicates."""
    if not request.app.state.settings.onboarding_enabled:
        raise HTTPException(404, "not_found")
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        total = db.scalar(select(func.count()).select_from(LearnerGoal)) or 0
        results = {}
        for kind in ["goal.created", "route.confirmed"]:
            event_counts = (
                select(
                    OutboxEvent.payload["resource_id"].as_string().label("goal_id"),
                    func.count().label("event_count"),
                )
                .where(OutboxEvent.kind == kind)
                # Group by the selected alias: PostgreSQL treats separate bound JSON
                # path parameters as different expressions even when values match.
                .group_by("goal_id")
                .subquery()
            )
            matched = (
                db.scalar(
                    select(func.count())
                    .select_from(LearnerGoal)
                    .join(event_counts, LearnerGoal.id == event_counts.c.goal_id)
                    .where(event_counts.c.event_count == 1)
                )
                or 0
            )
            events = (
                db.scalar(
                    select(func.count()).select_from(OutboxEvent).where(OutboxEvent.kind == kind)
                )
                or 0
            )
            denominator = max(total, events)
            results[kind] = {
                "goals": total,
                "events": events,
                "matched_goals": matched,
                "reconciliation_ratio": matched / denominator if denominator else None,
            }
        return {"items": results, "required_ratio": 0.99}
