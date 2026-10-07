"""Owned progress, consent, notification and privacy operations."""

import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.accountability.preferences import PreferencesUpdate, preferences_for
from socrat.accountability.privacy import export_data, receipt, request_deletion
from socrat.accountability.progress import progress
from socrat.accountability.reminders import enqueue, inbox
from socrat.auth import require_csrf, require_session, token_hash
from socrat.database import record_event
from socrat.models import (
    AssessmentDeferral,
    LearnerGoal,
    PrivacyRequest,
    Reminder,
    User,
    UserPreferences,
    now,
)
from socrat.skillpacks.routes import require_admin
from socrat.skillpacks.types import Contract

router = APIRouter(prefix="/api/v1")


def identity(request, db, write=False):
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
    user = (
        db.scalar(select(User).where(User.id == session.user_id).with_for_update())
        if write
        else db.get(User, session.user_id)
    )
    if user is None:
        raise HTTPException(401, "authentication_required")
    return user


@router.get("/progress")
def dashboard(request: Request, goal_id: str | None = None):
    if not request.app.state.settings.dashboard_enabled:
        raise HTTPException(404, "not_found")
    with Session(request.app.state.engine) as db:
        user = identity(request, db)
        query = select(LearnerGoal).where(LearnerGoal.user_id == user.id)
        if goal_id:
            query = query.where(LearnerGoal.id == goal_id)
        goal = db.scalar(
            query.order_by(LearnerGoal.confirmation_at.desc(), LearnerGoal.id.desc()).limit(1)
        )
        if goal is None:
            if goal_id:
                raise HTTPException(404, "not_found")
            return {"today": {"action": "choose_goal"}, "goal_id": None}
        if not goal.snapshot["routing_outcome"].startswith("accept_"):
            return {"today": {"action": "waitlist"}, "goal_id": goal.id}
        return progress(db, goal, now(), request.app.state.settings)


@router.get("/preferences")
def read_preferences(request: Request):
    with Session(request.app.state.engine) as db:
        return preferences_for(db, identity(request, db))


class DeferInput(Contract):
    cycle: str = Field(min_length=1, max_length=80)


@router.post("/goals/{goal_id}/assessment-deferral")
def defer_assessment(goal_id: str, body: DeferInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user = identity(request, db, True)
            goal = db.scalar(
                select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user.id)
            )
            if goal is None:
                raise HTTPException(404, "not_found")
            stamp = now()
            due = progress(db, goal, stamp, request.app.state.settings)["assessment_due"]
            if not due or due["cycle"] != body.cycle or not due["can_defer"]:
                raise HTTPException(409, "assessment_defer_unavailable")
            db.add(AssessmentDeferral(goal_id=goal.id, cycle=body.cycle, until_at=stamp + 86400))
            record_event(db, user.id, "assessment.deferred", goal.id)
            return {"deferred_until": stamp + 86400}
    except IntegrityError as exc:
        raise HTTPException(409, "assessment_defer_unavailable") from exc


@router.patch("/preferences")
def update_preferences(body: PreferencesUpdate, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user = identity(request, db, True)
            value = preferences_for(db, user)
            if body.expected_revision != value["revision"]:
                raise HTTPException(409, "preferences_revision_stale")
            row = db.get(UserPreferences, user.id)
            if row is None:
                row = UserPreferences(user_id=user.id, revision=0, settings={})
                db.add(row)
            row.settings = body.model_dump(exclude={"expected_revision"})
            row.revision += 1
            if not body.reminders_consent:
                for reminder in db.scalars(
                    select(Reminder).where(
                        Reminder.user_id == user.id, Reminder.opened_at.is_(None)
                    )
                ):
                    reminder.opened_at = now()
            record_event(db, user.id, "preferences.updated")
            db.flush()
            return preferences_for(db, user)
    except IntegrityError as exc:
        raise HTTPException(409, "preferences_revision_stale") from exc


@router.get("/reminders")
def read_reminders(request: Request):
    with Session(request.app.state.engine) as db:
        user = identity(request, db)
        return (
            inbox(db, user.id, preferences_for(db, user), now())
            if request.app.state.settings.reminders_enabled
            else {"items": []}
        )


@router.post("/reminders/check")
def check_reminders(request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        user = identity(request, db, True)
        if request.app.state.settings.reminders_enabled:
            enqueue(db, user.id, preferences_for(db, user), now())
            db.flush()
            return inbox(db, user.id, preferences_for(db, user), now())
        return {"items": []}


@router.post("/reminders/{reminder_id}/opened", status_code=204)
def open_reminder(reminder_id: str, request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        user = identity(request, db, True)
        row = db.scalar(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user.id)
        )
        if row is None:
            raise HTTPException(404, "not_found")
        if row.opened_at is None:
            row.opened_at = now()
            record_event(db, user.id, "reminder_opened", row.id)


@router.post("/privacy/export")
def export(request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        user = identity(request, db, True)
        result = export_data(db, user)
        record_event(db, user.id, "privacy.exported")
        return result


class DeleteInput(Contract):
    confirmation: Literal["DELETE MY DATA"]
    request_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")
    receipt_token: str | None = Field(default=None, min_length=32, max_length=128)


@router.post("/privacy/delete", status_code=202)
def deletion(body: DeleteInput, request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        if body.request_id and body.receipt_token:
            existing = db.get(PrivacyRequest, body.request_id)
            if existing and secrets.compare_digest(
                existing.token_hash, token_hash(body.receipt_token)
            ):
                return {**receipt(existing), "receipt_token": body.receipt_token}
        user = identity(request, db, True)
        if body.request_id and db.get(PrivacyRequest, body.request_id):
            raise HTTPException(409, "privacy_request_id_reused")
        return request_deletion(
            db, user, now(), request.app.state.settings, body.request_id, body.receipt_token
        )


@router.get("/privacy/requests/{request_id}")
def deletion_receipt(request_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        row = db.get(PrivacyRequest, request_id)
        if row is None or not secrets.compare_digest(
            row.token_hash, token_hash(request.headers.get("X-Privacy-Token", ""))
        ):
            raise HTTPException(404, "not_found")
        return receipt(row)


class CleanupInput(Contract):
    task: Literal["backups_replicas_logs", "provider", "shared_editorial_lineage"]
    evidence_reference: str = Field(pattern=r"^private-review:[a-zA-Z0-9_-]{1,100}$")


@router.get("/admin/privacy/requests")
def cleanup_queue(request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        rows = db.scalars(
            select(PrivacyRequest)
            .where(PrivacyRequest.status != "complete")
            .order_by(PrivacyRequest.deadline_at, PrivacyRequest.id)
            .limit(100)
        )
        return {
            "items": [
                {
                    **receipt(row),
                    "cleanup_context": row.cleanup_context,
                    "overdue": now() > row.deadline_at,
                }
                for row in rows
            ]
        }


@router.post("/admin/privacy/requests/{request_id}/cleanup")
def cleanup(request_id: str, body: CleanupInput, request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        actor = require_admin(request, db, True)
        row = db.scalar(
            select(PrivacyRequest).where(PrivacyRequest.id == request_id).with_for_update()
        )
        if row is None:
            raise HTTPException(404, "not_found")
        if row.status not in {"awaiting_external_cleanup", "complete"}:
            raise HTTPException(409, "database_erasure_pending")
        tasks = dict(row.tasks)
        if tasks[body.task] == "not_applicable":
            raise HTTPException(409, "cleanup_not_applicable")
        tasks[body.task] = {
            "status": "complete",
            "evidence_reference": body.evidence_reference,
            "at": now(),
        }
        row.tasks = tasks
        if all(
            value in {"complete", "not_applicable"}
            if isinstance(value, str)
            else value["status"] == "complete"
            for value in tasks.values()
        ):
            row.status = "complete"
            row.completed_at = now()
            row.cleanup_context = {}
        record_event(db, actor, "privacy.cleanup_verified", row.id)
        return receipt(row)
