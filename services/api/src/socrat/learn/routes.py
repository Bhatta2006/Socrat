"""Learner API. Every write is CSRF-checked and runs in one transaction."""

import secrets
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from socrat.assistant import service as assistant
from socrat.assistant.gateway import make_provider
from socrat.auth import COOKIE, require_csrf, require_session
from socrat.catalog.registry import Catalog, CatalogError, default_catalog
from socrat.database import record_event
from socrat.execution.protocol import ResultEnvelope
from socrat.judge import service as judge
from socrat.learn import placement, quizzes, views
from socrat.learn import service as learn
from socrat.models import (
    AuditEvent,
    DeliveredEvent,
    Draft,
    Enrollment,
    OutboxEvent,
    Submission,
    User,
    now,
)

router = APIRouter(prefix="/api/v1")
MIN_AGE = 13


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileUpdate(Strict):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    birthday_passed: bool = True
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        if value is None:
            return value
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Choose an IANA timezone") from exc
        return value


class EnrollInput(Strict):
    course: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    language: Literal["python", "cpp", "java"]
    level: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    minutes_per_day: Literal[15, 20, 30, 45, 60, 90, 120]
    weekdays: list[int] = Field(min_length=1, max_length=7)
    target_date: date | None = None
    target_role: Literal["internship", "new-grad", "mid-level", "senior"] | None = None
    target_rating: int | None = Field(default=None, ge=0, le=4000)
    motivation: str | None = Field(default=None, max_length=280)

    @field_validator("weekdays")
    @classmethod
    def valid_days(cls, value):
        if any(d not in range(7) for d in value):
            raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
        return value


class PlacementAnswer(Strict):
    item: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    choice: int | None = Field(default=None, ge=0, le=9)


class QuizAnswer(Strict):
    item: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    choice: int = Field(ge=0, le=9)


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(max_length=64_000)
    language: Literal["python", "cpp", "java"] | None = None


class RunInput(SourceInput):
    custom_input: str | None = Field(default=None, max_length=20_000)


class ExplainInput(Strict):
    style: Literal["simpler", "example", "deeper"]


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: str = Field(max_length=200)
    message: str = Field(default="", max_length=4000)
    intent: Literal["chat", "hint", "reveal", "reveal_confirmed"] = "chat"
    code: str = Field(default="", max_length=64_000)
    new_attempt: bool = False


class WorkerInput(Strict):
    worker_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class Heartbeat(WorkerInput):
    images: list[str] = Field(min_length=1, max_length=3)


class Callback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    envelope: ResultEnvelope


def catalog() -> Catalog:
    try:
        return default_catalog()
    except CatalogError as exc:
        raise HTTPException(503, "content_unavailable") from exc


def engine(request: Request):
    return request.app.state.engine


def user_of(request: Request, db: Session, write: bool = False) -> User:
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "authentication_required")
    return user


def age_ok(birth_year: int | None, birthday_passed: bool, today: date) -> bool:
    if birth_year is None:
        return False
    age = today.year - birth_year - (0 if birthday_passed else 1)
    return age >= MIN_AGE


def profile_view(db: Session, user: User, csrf: str) -> dict:
    enrollment = learn.active_enrollment(db, user.id)
    return dict(
        id=user.id,
        display_name=user.display_name,
        birth_year=user.birth_year,
        timezone=user.timezone,
        csrf_token=csrf,
        onboarded=enrollment is not None,
        enrollment=None
        if enrollment is None
        else dict(
            id=enrollment.id,
            course=enrollment.course_id,
            language=enrollment.language,
            status=enrollment.status,
            minutes_per_day=enrollment.minutes_per_day,
            weekdays=enrollment.weekdays,
            goal=enrollment.goal,
            level=enrollment.level_id,
        ),
    )


# ---------------------------------------------------------------- account


@router.get("/auth/status")
def auth_status(request: Request):
    with Session(engine(request)) as db:
        try:
            session = require_session(request, db)
        except HTTPException:
            return {"profile": None}
        user = db.get(User, session.user_id)
        return {"profile": profile_view(db, user, session.csrf_token) if user else None}


@router.get("/me")
def me(request: Request):
    with Session(engine(request)) as db:
        session = require_session(request, db)
        user = db.get(User, session.user_id)
        if user is None:
            raise HTTPException(401, "authentication_required")
        return profile_view(db, user, session.csrf_token)


@router.patch("/me")
def update_me(body: ProfileUpdate, request: Request):
    with Session(engine(request)) as db, db.begin():
        session = require_session(request, db)
        require_csrf(request, session)
        user = db.get(User, session.user_id)
        if user is None:
            raise HTTPException(401, "authentication_required")
        if body.birth_year is not None:
            if not age_ok(body.birth_year, body.birthday_passed, date.today()):
                raise HTTPException(403, "minimum_age")
            user.birth_year = body.birth_year
        if body.display_name is not None:
            user.display_name = body.display_name
        if body.timezone is not None:
            user.timezone = body.timezone
        record_event(db, user.id, "profile.updated")
        return profile_view(db, user, session.csrf_token)


@router.get("/me/export")
def export_me(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return views.export(db, user)


@router.delete("/me", status_code=204)
def delete_me(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        events = select(OutboxEvent.id).where(
            OutboxEvent.payload["actor_id"].as_string() == user.id
        )
        db.execute(delete(DeliveredEvent).where(DeliveredEvent.event_id.in_(events)))
        db.execute(
            delete(OutboxEvent).where(OutboxEvent.payload["actor_id"].as_string() == user.id)
        )
        db.execute(delete(AuditEvent).where(AuditEvent.actor_id == user.id))
        db.delete(user)  # Everything else cascades from the user row.
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response


# ---------------------------------------------------------------- catalog & enrollment


@router.get("/courses")
def courses():
    cat = catalog()
    return {
        "items": [
            views.course_card(cat, cid) for cid in ("zero", "dsa", "cp") if cid in cat.courses
        ]
        + [
            views.course_card(cat, cid)
            for cid in sorted(cat.courses)
            if cid not in {"zero", "dsa", "cp"}
        ]
    }


@router.post("/enrollments")
def enroll(body: EnrollInput, request: Request):
    cat = catalog()
    if body.course not in cat.courses:
        raise HTTPException(404, "unknown_course")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        if user.birth_year is None:
            raise HTTPException(409, "profile_incomplete")
        goal = {
            k: v
            for k, v in dict(
                target_date=body.target_date.isoformat() if body.target_date else None,
                target_role=body.target_role,
                target_rating=body.target_rating,
                motivation=body.motivation,
            ).items()
            if v is not None
        }
        enrollment = placement.enroll(
            db,
            cat,
            user,
            body.course,
            body.language,
            body.level,
            goal,
            body.minutes_per_day,
            body.weekdays,
            now(),
        )
        record_event(db, user.id, "enrollment.created", enrollment.id)
        return dict(id=enrollment.id, status=enrollment.status)


@router.get("/placement")
def placement_question(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return placement.question_view(catalog(), learn.require_enrollment(db, user.id))


@router.post("/placement/answer")
def placement_answer(body: PlacementAnswer, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.require_enrollment(db, user.id)
        return placement.answer(db, catalog(), enrollment, body.item, body.choice, now())


@router.get("/placement/summary")
def placement_summary(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return placement.summary(catalog(), learn.require_enrollment(db, user.id))


# ---------------------------------------------------------------- plan & today


def active(db: Session, user: User) -> Enrollment:
    enrollment = learn.require_enrollment(db, user.id)
    if enrollment.status != "active":
        raise HTTPException(409, "placement_in_progress")
    return enrollment


@router.get("/today")
def today(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.today_view(db, catalog(), user, active(db, user), now())


@router.get("/plan")
def plan(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.plan_view(db, catalog(), user, active(db, user), now())


@router.get("/progress")
def progress(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.progress_view(db, catalog(), user, active(db, user), now())


# ---------------------------------------------------------------- lessons & quizzes


@router.get("/concepts/{qualified}")
def concept(qualified: str, request: Request):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return views.concept_view(
            db, cat, user, learn.active_enrollment(db, user.id), qualified, now()
        )


@router.post("/concepts/{qualified}/explain")
async def explain(qualified: str, body: ExplainInput, request: Request):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.active_enrollment(db, user.id)
        language = enrollment.language if enrollment else "python"
        text, provider = await assistant.lesson_variant(
            db, make_provider(settings), cat, settings, qualified, language, body.style
        )
        return {"content": text, "provider": provider}


ACTIVITY = r"^(lesson|quiz|review|remedial|problem|checkpoint):[a-z0-9:-]{1,160}$"


def valid_activity(cat: Catalog, activity_id: str) -> str:
    import re

    if not re.match(ACTIVITY, activity_id):
        raise HTTPException(404, "not_found")
    kind, _, target = activity_id.partition(":")
    if kind == "problem" and target in cat.problems:
        return activity_id
    if kind == "checkpoint":
        course_id, _, module_id = target.partition(":")
        if course_id in cat.courses and any(
            m.id == module_id for m in cat.course(course_id).modules
        ):
            return activity_id
        raise HTTPException(404, "not_found")
    if target in cat.concepts:
        return activity_id
    raise HTTPException(404, "not_found")


@router.post("/activities/{activity_id}/start")
def start_activity(activity_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        learn.start_activity(db, enrollment, valid_activity(cat, activity_id), now())
        return {"started": True}


@router.post("/activities/{activity_id}/complete")
def complete_lesson(activity_id: str, request: Request):
    cat = catalog()
    if not activity_id.startswith("lesson:"):
        raise HTTPException(409, "only_lessons_complete_directly")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        changed = learn.complete_activity(
            db, user, enrollment, valid_activity(cat, activity_id), now()
        )
        return {"completed": True, "first_time": changed}


@router.get("/quiz/{activity_id}")
def quiz(activity_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        enrollment = active(db, user)
        session = quizzes.open_session(db, cat, enrollment, valid_activity(cat, activity_id), now())
        return quizzes.session_view(cat, session, enrollment.language)


@router.post("/quiz/{activity_id}/answer")
def quiz_answer(activity_id: str, body: QuizAnswer, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        session = quizzes.open_session(db, cat, enrollment, valid_activity(cat, activity_id), now())
        quizzes.answer(db, cat, user, enrollment, session, body.item, body.choice, now())
        return quizzes.session_view(cat, session, enrollment.language)


# ---------------------------------------------------------------- practice


def problem_or_404(cat: Catalog, problem_id: str):
    if problem_id not in cat.problems:
        raise HTTPException(404, "not_found")
    return cat.problem(problem_id)


@router.get("/runtimes")
def runtimes(request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db:
        return {
            "backend": settings.execution_backend,
            "languages": judge.runtimes(db, settings, now()),
        }


@router.get("/problems/{problem_id}")
def problem(problem_id: str, request: Request, language: str | None = None):
    cat = catalog()
    problem_or_404(cat, problem_id)
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = learn.active_enrollment(db, user.id)
        lang = (
            language
            if language in {"python", "cpp", "java"}
            else (enrollment.language if enrollment else "python")
        )
        return views.problem_view(db, cat, user, enrollment, problem_id, lang)


@router.put("/problems/{problem_id}/draft")
def save_draft(problem_id: str, body: SourceInput, request: Request):
    cat = catalog()
    problem_or_404(cat, problem_id)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.active_enrollment(db, user.id)
        language = body.language or (enrollment.language if enrollment else "python")
        draft = db.get(Draft, (user.id, problem_id, language))
        if draft is None:
            db.add(
                Draft(
                    user_id=user.id,
                    problem_id=problem_id,
                    language=language,
                    source=body.source,
                    updated_at=now(),
                )
            )
        else:
            draft.source, draft.updated_at = body.source, now()
        return {"saved": True}


def queue(problem_id: str, body: RunInput, request: Request, mode: str):
    cat = catalog()
    problem_obj = problem_or_404(cat, problem_id)
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.active_enrollment(db, user.id)
        language = body.language or (enrollment.language if enrollment else "python")
        if enrollment is not None and enrollment.status == "active" and mode == "submit":
            learn.start_activity(db, enrollment, f"problem:{problem_id}", now())
        job = judge.create(
            db,
            settings,
            user.id,
            enrollment.id if enrollment else None,
            problem_obj,
            language,
            body.source,
            mode,
            body.custom_input if mode == "run" else None,
            assistant.assistance_for(db, user.id, problem_id),
            now(),
        )
        draft = db.get(Draft, (user.id, problem_id, language))
        if draft is None:
            db.add(
                Draft(
                    user_id=user.id,
                    problem_id=problem_id,
                    language=language,
                    source=body.source,
                    updated_at=now(),
                )
            )
        else:
            draft.source, draft.updated_at = body.source, now()
        return judge.view(job)


@router.post("/problems/{problem_id}/run")
def run(problem_id: str, body: RunInput, request: Request):
    return queue(problem_id, body, request, "run")


@router.post("/problems/{problem_id}/submit")
def submit(problem_id: str, body: SourceInput, request: Request):
    return queue(
        problem_id, RunInput(source=body.source, language=body.language), request, "submit"
    )


@router.get("/submissions/{submission_id}")
def submission(submission_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        job = db.get(Submission, submission_id)
        if job is None or job.user_id != user.id:
            raise HTTPException(404, "not_found")
        return judge.view(job)


def worker_auth(request: Request):
    settings = request.app.state.settings
    token = settings.execution_worker_secret.get_secret_value()
    if (
        not settings.execution_enabled
        or not token
        or not secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + token)
    ):
        raise HTTPException(404, "not_found")


@router.post("/execution/worker/heartbeat")
def worker_heartbeat(body: Heartbeat, request: Request):
    worker_auth(request)
    with Session(engine(request)) as db, db.begin():
        judge.heartbeat(db, request.app.state.settings, body.worker_id, body.images, now())
    return {"ready": True, "server_now": now()}


@router.post("/execution/worker/claim")
def worker_claim(body: WorkerInput, request: Request):
    worker_auth(request)
    with Session(engine(request)) as db, db.begin():
        return {"job": judge.claim(db, body.worker_id, now())}


@router.post("/execution/worker/result")
def worker_result(body: Callback, request: Request):
    worker_auth(request)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        job, fresh = judge.finalize(
            db, request.app.state.settings, body.worker_id, body.envelope, now()
        )
        if fresh:
            on_submission(db, cat, job, now())
        return judge.view(job)


def on_submission(db: Session, cat: Catalog, job: Submission, stamp: int):
    """Submit results become learning evidence; Runs never change mastery."""
    if job.mode != "submit" or job.status != "done" or job.enrollment_id is None:
        return
    enrollment = db.get(Enrollment, job.enrollment_id)
    user = db.get(User, job.user_id)
    if enrollment is None or user is None or job.problem_id not in cat.problems:
        return
    course_id, problem_obj = cat.problems[job.problem_id]
    concept = f"{course_id}:{problem_obj.concepts[0]}"
    activity = f"problem:{job.problem_id}"
    elapsed = learn.elapsed(db, enrollment, activity, stamp)
    expected = learn.expected_seconds(cat, activity, enrollment)
    if job.verdict == "accepted":
        already = activity in learn.completed_for(db, enrollment)
        if not already:
            learn.record_evidence(
                db,
                enrollment,
                concept,
                "code",
                1.0,
                activity,
                stamp,
                min(job.assistance, 5),
                elapsed,
                expected,
            )
            learn.complete_activity(
                db,
                user,
                enrollment,
                activity,
                stamp,
                outcome={"assistance": job.assistance},
                solved=True,
            )
        return
    if job.verdict in {"system_error", ""}:
        return
    today_start = stamp - 86400
    from socrat.models import Evidence

    earlier = db.scalar(
        select(Evidence.id).where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.activity_id == activity,
            Evidence.created_at >= today_start,
        )
    )
    if earlier is None and activity not in learn.completed_for(db, enrollment):
        partial = 0.5 * job.passed / job.total if job.total else 0.0
        learn.record_evidence(
            db, enrollment, concept, "code", partial, activity, stamp, 0, elapsed, expected
        )


# ---------------------------------------------------------------- assistant


@router.get("/assistant/thread")
def assistant_thread(scope: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return assistant.thread_view(db, user.id, scope)


@router.post("/assistant/messages")
async def assistant_message(body: MessageInput, request: Request):
    cat = catalog()
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        turn = assistant.prepare(
            db,
            cat,
            settings,
            user,
            body.scope,
            body.message,
            body.intent,
            body.code,
            body.new_attempt,
            now(),
        )
    provider = make_provider(settings)
    bind = engine(request)

    async def events():
        async for event, data in assistant.stream_reply(provider, turn, settings):
            if event == "done":
                with Session(bind) as db, db.begin():
                    message = assistant.persist_reply(
                        db, turn.thread_id, data["text"], data["level"], data["provider"], now()
                    )
                    data = {**data, "message_id": message.id if message else None}
            yield assistant.sse(event, data)

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
    )
