import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.execution.protocol import ResultEnvelope, Source, sign
from socrat.execution.service import (
    ExecutionError,
    attempt_view,
    claim,
    create_attempt,
    enqueue,
    finalize,
    healthy_images,
    run_view,
)
from socrat.models import CodeAttempt, CodeDraft, CodeRun, ExecutionWorker, LearnerGoal, User, now
from socrat.skillpacks.service import PackError
from socrat.skillpacks.types import Contract, Key

router = APIRouter(prefix="/api/v1")


class AttemptInput(Contract):
    exercise_id: Key
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    diagnostic_attempt_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")
    assessment_item_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")


class DraftInput(Contract):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)
    source: Source
    expected_revision: int = Field(ge=0)


class RunInput(Contract):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    draft_revision: int = Field(ge=0)
    stdin: str | None = Field(default=None, max_length=8000)


class WorkerInput(Contract):
    worker_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class Heartbeat(WorkerInput):
    images: list[str] = Field(min_length=1, max_length=3)


class Callback(WorkerInput):
    envelope: ResultEnvelope


def identity(request, db, write=False):
    if not request.app.state.settings.execution_enabled:
        raise HTTPException(404, "not_found")
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
        db.scalar(select(User).where(User.id == session.user_id).with_for_update())
    return session.user_id


def worker_auth(request):
    settings = request.app.state.settings
    token = settings.execution_worker_secret.get_secret_value()
    if (
        not settings.execution_enabled
        or not token
        or not secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + token)
    ):
        raise HTTPException(404, "not_found")


def owned(db, attempt_id, user_id):
    attempt = db.scalar(
        select(CodeAttempt).where(CodeAttempt.id == attempt_id, CodeAttempt.user_id == user_id)
    )
    if attempt is None:
        raise HTTPException(404, "not_found")
    return attempt


def boundary(exc):
    if isinstance(exc, IntegrityError):
        raise HTTPException(409, "concurrent_execution_retry") from exc
    if isinstance(exc, ValueError):
        raise HTTPException(409, "execution_signature_invalid") from exc
    raise HTTPException(exc.status, exc.code) from exc


@router.get("/execution/capabilities")
def capabilities(request: Request):
    with Session(request.app.state.engine) as db:
        identity(request, db)
        images = healthy_images(db, request.app.state.settings, now())
        return {
            "items": [
                {"language": x["language"], "runtime_id": x["id"], "healthy": x["image"] in images}
                for x in request.app.state.settings.execution_profiles
            ]
        }


@router.post("/goals/{goal_id}/code-attempts")
def start(goal_id: str, body: AttemptInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            goal = db.scalar(
                select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
            )
            if goal is None:
                raise HTTPException(404, "not_found")
            return attempt_view(
                db,
                create_attempt(
                    db,
                    goal,
                    body.exercise_id,
                    body.idempotency_key,
                    body.diagnostic_attempt_id,
                    request.app.state.settings,
                    now(),
                    assessment_item_id=body.assessment_item_id,
                ),
            )
    except (ExecutionError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/goals/{goal_id}/code-attempts")
def attempts(goal_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        goal = db.scalar(
            select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
        )
        if goal is None:
            raise HTTPException(404, "not_found")
        return {
            "items": [
                {
                    "id": x.id,
                    "exercise_id": x.exercise_id,
                    "language": x.snapshot["language"],
                    "diagnostic_attempt_id": x.snapshot["diagnostic_attempt_id"],
                    "assessment_item_id": x.snapshot.get("assessment_item_id"),
                    "created_at": x.created_at,
                }
                for x in db.scalars(
                    select(CodeAttempt)
                    .where(CodeAttempt.goal_id == goal_id)
                    .order_by(CodeAttempt.created_at.desc(), CodeAttempt.id)
                    .limit(100)
                )
            ]
        }


@router.get("/attempts/{attempt_id}")
def read(attempt_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db:
            return attempt_view(db, owned(db, attempt_id, identity(request, db)))
    except (ExecutionError, PackError) as exc:
        boundary(exc)


@router.patch("/attempts/{attempt_id}/draft")
def autosave(attempt_id: str, body: DraftInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            attempt = owned(db, attempt_id, identity(request, db, True))
            draft = db.get(CodeDraft, attempt.id)
            assert draft is not None
            if draft.revision != body.expected_revision:
                if draft.revision == body.expected_revision + 1 and draft.source == body.source:
                    return dict(revision=draft.revision, saved=True)
                raise ExecutionError("code_draft_stale")
            draft.source, draft.revision, draft.updated_at = body.source, draft.revision + 1, now()
            return dict(revision=draft.revision, saved=True)
    except ExecutionError as exc:
        boundary(exc)


@router.post("/attempts/{attempt_id}/runs")
@router.post("/attempts/{attempt_id}/submit")
def queue(attempt_id: str, body: RunInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            attempt = owned(db, attempt_id, identity(request, db, True))
            mode: Literal["run", "submit"] = (
                "submit" if request.url.path.endswith("/submit") else "run"
            )
            return run_view(
                enqueue(
                    db,
                    attempt,
                    mode,
                    body.model_dump(),
                    request.app.state.settings,
                    now(),
                    sign(
                        {"peer": request.client.host if request.client else "unknown"},
                        request.app.state.settings.execution_signing_secret.get_secret_value(),
                    ),
                )
            )
    except (ExecutionError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/attempts/{attempt_id}/runs")
def history(attempt_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        attempt = owned(db, attempt_id, identity(request, db))
        return {
            "items": [
                run_view(x)
                for x in db.scalars(
                    select(CodeRun)
                    .where(CodeRun.attempt_id == attempt.id)
                    .order_by(CodeRun.created_at.desc(), CodeRun.id)
                    .limit(100)
                )
            ]
        }


@router.get("/code-runs/{run_id}")
def result(run_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        run = db.scalar(select(CodeRun).where(CodeRun.id == run_id, CodeRun.user_id == user_id))
        if run is None:
            raise HTTPException(404, "not_found")
        return run_view(run)


@router.post("/execution/worker/heartbeat")
def heartbeat(body: Heartbeat, request: Request):
    worker_auth(request)
    allowed = {x["image"] for x in request.app.state.settings.execution_profiles}
    if len(body.images) != len(set(body.images)) or not set(body.images) <= allowed:
        raise HTTPException(422, "worker_runtime_mismatch")
    with Session(request.app.state.engine) as db, db.begin():
        worker = db.get(ExecutionWorker, body.worker_id)
        if worker is None:
            db.add(ExecutionWorker(id=body.worker_id, images=body.images, seen_at=now()))
        else:
            worker.images, worker.seen_at = body.images, now()
    return {"ready": True}


@router.post("/execution/worker/claim")
def dispatch(body: WorkerInput, request: Request):
    worker_auth(request)
    try:
        with Session(request.app.state.engine) as db, db.begin():
            return {"job": claim(db, body.worker_id, request.app.state.settings, now())}
    except ExecutionError as exc:
        boundary(exc)


@router.post("/execution/worker/result")
def callback(body: Callback, request: Request):
    worker_auth(request)
    try:
        with Session(request.app.state.engine) as db, db.begin():
            run = db.get(CodeRun, body.envelope.result.job_id)
            if run is None:
                raise HTTPException(404, "not_found")
            db.scalar(select(User).where(User.id == run.user_id).with_for_update())
            db.scalar(select(CodeRun).where(CodeRun.id == run.id).with_for_update())
            db.refresh(run)
            return run_view(
                finalize(db, body.worker_id, body.envelope, request.app.state.settings, now())
            )
    except (ExecutionError, PackError, ValueError, IntegrityError) as exc:
        boundary(exc)
