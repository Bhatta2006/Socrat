"""Owned learner workflows and authenticated independent human review."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.assessment import service
from socrat.assessment.contracts import DisputeInput, ResponseInput, ReviewInput, StartInput
from socrat.auth import require_csrf, require_session
from socrat.models import (
    AssessmentAnswer,
    AssessmentItem,
    AssessmentReview,
    AssessmentSession,
    LearnerGoal,
    User,
    now,
)
from socrat.skillpacks.routes import require_admin
from socrat.skillpacks.service import PackError

router = APIRouter(prefix="/api/v1")


def identity(request, db, write=False):
    if not request.app.state.settings.assessments_enabled:
        raise HTTPException(404, "not_found")
    login = require_session(request, db)
    if write:
        require_csrf(request, login)
        db.scalar(select(User).where(User.id == login.user_id).with_for_update())
    return login.user_id


def owned(db, user_id, assessment_id):
    session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == assessment_id, AssessmentSession.user_id == user_id
        )
    )
    if session is None:
        raise HTTPException(404, "not_found")
    return session


def goal_for(db, user_id, goal_id):
    goal = db.scalar(
        select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
    )
    if goal is None:
        raise HTTPException(404, "not_found")
    return goal


def boundary(exc):
    if isinstance(exc, IntegrityError):
        raise HTTPException(409, "concurrent_assessment_retry") from exc
    raise HTTPException(exc.status, exc.code) from exc


@router.post("/goals/{goal_id}/assessments")
def start(goal_id: str, body: StartInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            session = service.start(db, goal_for(db, user_id, goal_id), body.model_dump(), now())
            return service.public_view(db, session, now())
    except (service.AssessmentError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/goals/{goal_id}/assessments")
def history(goal_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db:
            user_id = identity(request, db)
            goal_for(db, user_id, goal_id)
            records = db.scalars(
                select(AssessmentSession)
                .where(AssessmentSession.goal_id == goal_id)
                .order_by(AssessmentSession.started_at.desc())
            )
            return {"items": [service.public_view(db, x, now()) for x in records]}
    except (service.AssessmentError, PackError) as exc:
        boundary(exc)


@router.get("/goals/{goal_id}/retention")
def due(goal_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        return {
            "items": service.retention_due(db, goal_for(db, user_id, goal_id), now()),
            "ordinary_session_budget_fraction": 0.25,
        }


@router.get("/assessments/{assessment_id}")
def read(assessment_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db:
            return service.public_view(db, owned(db, identity(request, db), assessment_id), now())
    except (service.AssessmentError, PackError) as exc:
        boundary(exc)


@router.post("/assessments/{assessment_id}/responses")
def respond(assessment_id: str, body: ResponseInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            session = owned(db, identity(request, db, True), assessment_id)
            return service.respond(db, session, body.model_dump(), now())
    except (service.AssessmentError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.post("/assessments/{assessment_id}/complete")
def complete(assessment_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            session = owned(db, identity(request, db, True), assessment_id)
            return service.complete(db, session, now())
    except (service.AssessmentError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/admin/assessments/reviews")
def queue(request: Request):
    with Session(request.app.state.engine) as db:
        if not request.app.state.settings.assessments_enabled:
            raise HTTPException(404, "not_found")
        require_admin(request, db)
        rows = []
        for session in db.scalars(select(AssessmentSession)):
            for item in service.items_for(db, session):
                response = service.effective_response(db, item)
                disputed = service.pending_dispute(db, item)
                reviewed = db.scalar(
                    select(AssessmentReview).where(AssessmentReview.item_id == item.id)
                )
                if (
                    disputed
                    or response
                    and not reviewed
                    and session.result is None
                    and (
                        response["status"] == "pending_review" or session.status == "pending_review"
                    )
                ):
                    answer = db.get(AssessmentAnswer, item.id)
                    rows.append(
                        dict(
                            session_id=session.id,
                            item_id=item.id,
                            revision=session.revision,
                            exercise_id=item.exercise_id,
                            response=response,
                            answer=answer.answer if answer else None,
                            rubric_criteria=service.spec_for(session, item).rubric_criteria,
                            dispute=disputed.rationale if disputed else None,
                        )
                    )
        return {"items": rows}


@router.post("/assessments/{assessment_id}/items/{item_id}/dispute")
def dispute(assessment_id: str, item_id: str, body: DisputeInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            session = owned(db, identity(request, db, True), assessment_id)
            item = db.get(AssessmentItem, item_id)
            if item is None or item.session_id != session.id:
                raise HTTPException(404, "not_found")
            return service.dispute(db, session, item, body.model_dump(), now())
    except (service.AssessmentError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.post("/admin/assessments/items/{item_id}/review")
def review(item_id: str, body: ReviewInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            if not request.app.state.settings.assessments_enabled:
                raise HTTPException(404, "not_found")
            actor = require_admin(request, db, True)
            item = db.get(AssessmentItem, item_id)
            if item is None:
                raise HTTPException(404, "not_found")
            session = db.get(AssessmentSession, item.session_id)
            assert session is not None
            db.scalar(select(User).where(User.id == session.user_id).with_for_update())
            db.refresh(session)
            return service.review(db, session, item, actor, body.model_dump(), now())
    except (service.AssessmentError, PackError, IntegrityError) as exc:
        boundary(exc)
