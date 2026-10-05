from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.execution.service import ExecutionError
from socrat.learning.contracts import SessionAction, StartSession
from socrat.learning.service import SessionError, command, local_day, start, view
from socrat.models import LearnerGoal, LearningSession, User, now
from socrat.planning.service import PlanningError
from socrat.skillpacks.service import PackError

router = APIRouter(prefix="/api/v1")


def identity(request, db, write=False):
    if not request.app.state.settings.learning_sessions_enabled:
        raise HTTPException(404, "not_found")
    login = require_session(request, db)
    if write:
        require_csrf(request, login)
        db.scalar(select(User).where(User.id == login.user_id).with_for_update())
    return login.user_id


def owned_goal(db, goal_id, user_id):
    goal = db.scalar(
        select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
    )
    if goal is None:
        raise HTTPException(404, "not_found")
    return goal


def boundary(exc):
    if isinstance(exc, IntegrityError):
        raise HTTPException(409, "concurrent_session_retry") from exc
    raise HTTPException(exc.status, exc.code) from exc


@router.get("/goals/{goal_id}/learning-session")
def today(goal_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db:
            goal = owned_goal(db, goal_id, identity(request, db))
            session = db.scalar(
                select(LearningSession).where(
                    LearningSession.goal_id == goal.id,
                    LearningSession.local_date == local_day(goal, now()),
                )
            )
            return {"session": view(db, session, now()) if session else None}
    except (SessionError, PackError) as exc:
        boundary(exc)


@router.post("/goals/{goal_id}/learning-session")
def begin(goal_id: str, body: StartSession, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            goal = owned_goal(db, goal_id, identity(request, db, True))
            return start(
                db, goal, body.curriculum_revision, request.app.state.settings, now(), body.timing
            )
    except (SessionError, PlanningError, ExecutionError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.post("/learning-sessions/{session_id}/commands")
def mutate(session_id: str, body: SessionAction, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            session = db.scalar(
                select(LearningSession).where(
                    LearningSession.id == session_id,
                    LearningSession.user_id == user_id,
                )
            )
            if session is None:
                raise HTTPException(404, "not_found")
            return command(
                db,
                owned_goal(db, session.goal_id, user_id),
                session,
                body,
                now(),
                request.app.state.settings,
            )
    except (SessionError, ExecutionError, PackError, IntegrityError) as exc:
        boundary(exc)
