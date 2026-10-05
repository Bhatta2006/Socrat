from datetime import date as Date
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.learnerstate.policy import digest
from socrat.learnerstate.service import facts_for
from socrat.models import (
    CurriculumRevision,
    LearnerGoal,
    LearnerState,
    LearningEvidence,
    SkillPackVersion,
    User,
    now,
)
from socrat.planning.contracts import PlanCommand
from socrat.planning.engine import build_plan
from socrat.planning.service import PlanningError, command, current
from socrat.skillpacks.routes import require_admin
from socrat.skillpacks.service import PackError, load

router = APIRouter(prefix="/api/v1")


def identity(request: Request, db: Session, write=False):
    if not request.app.state.settings.planning_enabled:
        raise HTTPException(404, "not_found")
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
        db.scalar(select(User).where(User.id == session.user_id).with_for_update())
    return session.user_id


def owned(db: Session, goal_id: str, user_id: str):
    goal = db.scalar(
        select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
    )
    if goal is None:
        raise HTTPException(404, "not_found")
    return goal


def boundary(exc):
    if isinstance(exc, IntegrityError):
        raise HTTPException(409, "concurrent_plan_retry") from exc
    raise HTTPException(exc.status, exc.code) from exc


@router.post("/goals/{goal_id}/curriculum/commands")
def mutate(goal_id: str, body: PlanCommand, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            db.info["execution_settings"] = request.app.state.settings
            user_id = identity(request, db, True)
            return command(db, owned(db, goal_id, user_id), body, now())
    except (PlanningError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/goals/{goal_id}/curriculum")
def curriculum(goal_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db:
            user_id = identity(request, db)
            value = current(db, owned(db, goal_id, user_id))
            state = db.get(LearnerState, user_id)
            latest = (
                db.scalar(
                    select(LearningEvidence.sequence)
                    .where(LearningEvidence.user_id == user_id)
                    .order_by(LearningEvidence.sequence.desc())
                    .limit(1)
                )
                or 0
            )
            value["needs_refresh"] = latest != value["evidence_watermark"] or bool(
                state and state.active_policy != value["learning_policy_version"]
            )
            return value
    except (PlanningError, PackError) as exc:
        boundary(exc)


@router.get("/daily-plan")
def daily_plan(goal_id: str, request: Request, date: str | None = None):
    value = curriculum(goal_id, request)
    try:
        day = (
            Date.fromisoformat(date)
            if date
            else datetime.fromtimestamp(now(), ZoneInfo(value["schedule"]["timezone"])).date()
        )
    except ValueError as exc:
        raise HTTPException(422, "invalid_plan_date") from exc
    plan = next((x for x in value["days"] if x["date"] == day.isoformat()), None)
    if plan is None:
        raise HTTPException(404, "date_outside_plan_horizon")
    local_today = datetime.fromtimestamp(now(), ZoneInfo(value["schedule"]["timezone"])).date()
    status = plan["status"]
    if status == "draft":
        with Session(request.app.state.engine) as db:
            user_id = identity(request, db)
            facts = facts_for(db, user_id)
            invalidated = {x.target_event_id for x in facts if x.kind == "invalidated"}
            practice = [
                x
                for x in facts
                if x.kind == "scored"
                and x.event_id not in invalidated
                and x.valid
                and x.finalized
                and x.goal_id == goal_id
                and x.pack_id == value["pack_id"]
                and x.language == value["schedule"]["language"]
                and x.mode in {"practice", "retention"}
                and datetime.fromtimestamp(
                    x.occurred_at, ZoneInfo(value["schedule"]["timezone"])
                ).date()
                == day
            ]
            record = db.get(SkillPackVersion, value["pack_id"])
            if record is None:
                raise HTTPException(409, "goal_content_unavailable")
            pack = load(record)
            selected_ids = {key for block in plan["blocks"] for key in block["exercise_ids"]}
            families = {x.family_id for x in pack.exercises if x.id in selected_ids}
            independent = any(x.family_id in families and x.hint_level == 0 for x in practice)
            selected_concepts = {key for block in plan["blocks"] for key in block["concept_ids"]}
            exit_check = any(
                x.hint_level == 0
                and x.evidence_type == "explain"
                and selected_concepts.intersection(x.concept_ids)
                for x in practice
            )
        status = (
            "completed"
            if independent and exit_check
            else "in_progress"
            if practice
            else "missed"
            if day < local_today
            else "paused"
            if value["status"] == "paused"
            else "ready"
            if value["status"] == "confirmed" and not value["needs_refresh"]
            else "draft"
        )
    return dict(
        **{**plan, "status": status},
        curriculum_revision=value["revision"],
        needs_refresh=value["needs_refresh"],
        best_next_action=next((x for x in plan["blocks"] if x["mode"] == "independent"), None),
        actionable=status in {"ready", "in_progress"}
        and day == local_today
        and not value["needs_refresh"],
    )


@router.get("/admin/planning/revisions/{revision_id}/replay")
def replay(revision_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        revision = db.get(CurriculumRevision, revision_id)
        if revision is None:
            raise HTTPException(404, "not_found")
        snapshot = revision.snapshot
        record = db.get(SkillPackVersion, snapshot["pack_id"])
        if record is None or record.digest != snapshot["pack_digest"]:
            raise HTTPException(409, "historical_content_mismatch")
        inputs = {
            **snapshot["replay_inputs"],
            "today": Date.fromisoformat(snapshot["replay_inputs"]["today"]),
        }
        replayed = build_plan(load(record), **inputs)
        return dict(
            snapshot_digest_matches=digest(snapshot) == revision.digest,
            decisions_match=all(snapshot[key] == value for key, value in replayed.items()),
            planner_policy_version=snapshot["planner_policy_version"],
            planner_policy_digest=snapshot["planner_policy_digest"],
        )
