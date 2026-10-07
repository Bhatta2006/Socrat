import json
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from socrat.accountability.routes import router as accountability_router
from socrat.assessment.routes import router as assessment_router
from socrat.auth import COOKIE, establish_session, require_csrf, require_session
from socrat.config import Settings
from socrat.database import make_engine, record_event
from socrat.diagnostics.routes import router as diagnostic_router
from socrat.execution.routes import router as execution_router
from socrat.learning.routes import router as learning_router
from socrat.models import (
    AdvisorShadow,
    AssessmentSession,
    DiagnosticSession,
    PrivacyRequest,
    TutorTurn,
    User,
    now,
)
from socrat.onboarding.routes import router as onboarding_router
from socrat.planning.routes import router as planning_router
from socrat.schema_revision import SCHEMA_REVISION
from socrat.skillpacks.routes import router as skill_pack_router
from socrat.tutor.routes import router as tutor_router

logger = logging.getLogger("socrat.requests")


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    display_name: str = Field(min_length=1, max_length=80)
    timezone: str = Field(max_length=64)
    adult_confirmed: bool

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Choose an IANA timezone") from exc
        return value


class DevIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


def profile_view(user: User | None, csrf: str) -> dict:
    if user is None:
        raise HTTPException(401, "authentication_required")
    return {
        "id": user.id,
        "display_name": user.display_name,
        "timezone": user.timezone,
        "adult_confirmed": user.adult_confirmed,
        "csrf_token": csrf,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url_value)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(
        title="Socrat API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.secure else "/api/docs",
        openapi_url=None if settings.secure else "/api/openapi.json",
    )
    app.state.engine = engine
    app.state.settings = settings
    if settings.demo_mode:
        from socrat.clock import demo_offset, offset_for
        from socrat.demo.routes import router as demo_router

        app.include_router(demo_router)

        @app.middleware("http")
        async def demo_clock_scope(request: Request, call_next):
            token = demo_offset.set(offset_for(engine))
            try:
                return await call_next(request)
            finally:
                demo_offset.reset(token)

    app.include_router(skill_pack_router)
    app.include_router(onboarding_router)
    app.include_router(diagnostic_router)
    app.include_router(planning_router)
    app.include_router(execution_router)
    app.include_router(learning_router)
    app.include_router(tutor_router)
    app.include_router(assessment_router)
    app.include_router(accountability_router)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
        session_cookie="socrat_oidc",
        same_site="lax",
        https_only=settings.secure,
        max_age=600,
    )
    registry = CollectorRegistry()
    requests = Counter(
        "socrat_http_requests_total",
        "HTTP responses",
        ["method", "route", "status"],
        registry=registry,
    )
    latency = Histogram(
        "socrat_http_duration_seconds", "HTTP latency", ["route"], registry=registry
    )
    diagnostic_sessions = Gauge(
        "socrat_diagnostic_sessions",
        "Diagnostic sessions by track, language and status",
        ["track", "language", "status"],
        registry=registry,
    )
    oauth = OAuth()
    privacy_requests = Gauge(
        "socrat_privacy_requests",
        "Incomplete privacy requests by status",
        ["status"],
        registry=registry,
    )
    privacy_overdue = Gauge(
        "socrat_privacy_overdue_requests",
        "Incomplete erasure requests past the cleanup deadline",
        registry=registry,
    )
    tutor_budget_alerts = Gauge(
        "socrat_tutor_budget_exhaustions",
        "Budget fallbacks in the last 15 minutes",
        registry=registry,
    )
    tutor_reserved = Gauge(
        "socrat_tutor_reserved_microusd",
        "Conservative model spend reservations in the last 24 hours",
        registry=registry,
    )
    assessment_sessions = Gauge(
        "socrat_assessment_sessions",
        "Assessment sessions by kind, track, language and status",
        ["kind", "track", "language", "status"],
        registry=registry,
    )
    if settings.oidc_issuer:
        oauth.register(
            "identity",
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret.get_secret_value(),
            server_metadata_url=f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid", "code_challenge_method": "S256"},
        )

    def error(code: str, status: int, request_id: str = ""):
        return JSONResponse({"error": {"code": code, "request_id": request_id}}, status_code=status)

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        if (
            request.method in {"POST", "PATCH", "PUT", "DELETE"}
            and request.headers.get("origin") != settings.public_origin
        ):
            response = error("origin_rejected", 403, request_id)
        else:
            try:
                response = await call_next(request)
            except Exception:
                logger.error(json.dumps({"event": "request_failed", "request_id": request_id}))
                response = error("internal_error", 500, request_id)
        response.headers.update(
            {
                "X-Request-ID": request_id,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "same-origin",
            }
        )
        if settings.secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        route = getattr(request.scope.get("route"), "path", "unmatched")
        # Use templates, not raw paths: prevents PII leaks and unbounded metric labels.
        requests.labels(request.method, route, str(response.status_code)).inc()
        latency.labels(route).observe(time.perf_counter() - started)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "route": route,
                    "status": response.status_code,
                }
            )
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(str(exc.detail), exc.status_code, request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo submitted profile values or auth credentials in errors.
        if request.url.path.startswith("/api/v1/onboarding/"):
            return error("input_confirmation_required", 422, request.state.request_id)
        return error("validation_failed", 422, request.state.request_id)

    @app.get("/api/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/api/health/ready")
    def ready():
        try:
            with engine.connect() as connection:
                if (
                    connection.scalar(text("SELECT version_num FROM alembic_version"))
                    != SCHEMA_REVISION
                ):
                    raise ValueError("Schema mismatch")
        except Exception as exc:
            raise HTTPException(503, "database_not_ready") from exc
        return {"status": "ready"}

    @app.get("/api/metrics", include_in_schema=False)
    def metrics(request: Request):
        metrics_token = settings.metrics_token.get_secret_value()
        if not metrics_token or not secrets.compare_digest(
            request.headers.get("authorization", ""), f"Bearer {metrics_token}"
        ):
            raise HTTPException(404, "not_found")
        diagnostic_sessions.clear()
        assessment_sessions.clear()
        with Session(engine) as db:
            privacy_requests.clear()
            privacy_rows = list(
                db.scalars(select(PrivacyRequest).where(PrivacyRequest.status != "complete"))
            )
            for status in ("queued", "erasing", "awaiting_external_cleanup"):
                privacy_requests.labels(status).set(
                    sum(row.status == status for row in privacy_rows)
                )
            privacy_overdue.set(sum(row.deadline_at < now() for row in privacy_rows))
            assessment_counts: dict[tuple[str, str, str, str], int] = {}
            for assessment in db.scalars(select(AssessmentSession)):
                cell = (
                    assessment.snapshot["kind"],
                    assessment.snapshot["track"],
                    assessment.snapshot["language"],
                    "expired"
                    if assessment.result is None
                    and assessment.status == "in_progress"
                    and now() >= assessment.deadline_at
                    else assessment.status,
                )
                assessment_counts[cell] = assessment_counts.get(cell, 0) + 1
            for cell, count in assessment_counts.items():
                assessment_sessions.labels(*cell).set(count)
            counts: dict[tuple[str, str, str], int] = {}
            for diagnostic in db.scalars(select(DiagnosticSession)):
                key = (
                    diagnostic.snapshot["declared_track"],
                    diagnostic.snapshot["language"],
                    diagnostic.status,
                )
                counts[key] = counts.get(key, 0) + 1
            for key, count in counts.items():
                diagnostic_sessions.labels(*key).set(count)
            turns = list(db.scalars(select(TutorTurn).where(TutorTurn.created_at >= now() - 86400)))
            shadows = list(
                db.scalars(select(AdvisorShadow).where(AdvisorShadow.created_at >= now() - 86400))
            )
            tutor_budget_alerts.set(
                sum(x.telemetry["budget_alert"] for x in turns if x.created_at >= now() - 900)
            )
            tutor_reserved.set(
                sum(x.telemetry["reserved_microusd"] for x in turns)
                + sum(x.outcome["reserved_microusd"] for x in shadows)
            )
        return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")

    @app.get("/api/v1/features")
    def features():
        return {
            "demo_mode": settings.demo_mode,
            "execution_backend": settings.execution_backend,
            "llm_advisor": False,
            "tutor": settings.tutor_enabled,
            "code_execution": settings.execution_enabled,
            "learning_sessions": settings.learning_sessions_enabled,
            "dev_login": settings.dev_login_enabled,
            "oidc_login": bool(settings.oidc_issuer),
            "onboarding": settings.onboarding_enabled,
            "diagnostics": settings.diagnostics_enabled,
            "planning": settings.planning_enabled,
            "assessments": settings.assessments_enabled,
            "dashboard": settings.dashboard_enabled,
            "reminders": settings.reminders_enabled,
        }

    @app.post("/api/v1/auth/dev-login")
    def dev_login(body: DevIdentity, request: Request):
        if not settings.dev_login_enabled:
            raise HTTPException(404, "not_found")
        return establish_session(
            request, JSONResponse({"authenticated": True}), "local-development", body.subject
        )

    @app.get("/api/v1/auth/login")
    async def oidc_login(request: Request):
        if not settings.oidc_issuer:
            raise HTTPException(503, "identity_provider_not_configured")
        return await oauth.identity.authorize_redirect(
            request, f"{settings.public_origin}/api/v1/auth/callback"
        )

    @app.get("/api/v1/auth/callback")
    async def oidc_callback(request: Request):
        if not settings.oidc_issuer:
            raise HTTPException(503, "identity_provider_not_configured")
        try:
            token = await oauth.identity.authorize_access_token(request)
            identity = token["userinfo"]
            # Authlib validates signature, audience, expiry and nonce; pin issuer explicitly too.
            if identity.get("iss") != settings.oidc_issuer or not identity.get("sub"):
                raise ValueError("Invalid identity")
        except Exception as exc:
            request.session.clear()
            raise HTTPException(401, "identity_verification_failed") from exc
        request.session.clear()
        return establish_session(
            request, RedirectResponse("/", status_code=303), identity["iss"], identity["sub"]
        )

    @app.get("/api/v1/me")
    def me(request: Request):
        with Session(engine) as db:
            session = require_session(request, db)
            return profile_view(db.get(User, session.user_id), session.csrf_token)

    @app.get("/api/v1/auth/status")
    def auth_status(request: Request):
        with Session(engine) as db:
            try:
                session = require_session(request, db)
            except HTTPException as exc:
                if exc.status_code != 401:
                    raise
                return {"profile": None}
            return {"profile": profile_view(db.get(User, session.user_id), session.csrf_token)}

    @app.get("/api/v1/profiles/{user_id}")
    def own_profile(user_id: str, request: Request):
        with Session(engine) as db:
            session = require_session(request, db)
            if user_id != session.user_id:
                raise HTTPException(404, "not_found")
            return profile_view(db.get(User, user_id), session.csrf_token)

    @app.patch("/api/v1/me")
    def update_me(body: ProfileUpdate, request: Request):
        with Session(engine) as db, db.begin():
            session = require_session(request, db)
            require_csrf(request, session)
            user = db.get(User, session.user_id)
            if user is None:
                raise HTTPException(401, "authentication_required")
            for name, value in body.model_dump().items():
                setattr(user, name, value)
            record_event(db, user.id, "profile.updated")
            return profile_view(user, session.csrf_token)

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(request: Request):
        with Session(engine) as db, db.begin():
            session = require_session(request, db)
            require_csrf(request, session)
            record_event(db, session.user_id, "auth.logout")
            db.delete(session)
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE, path="/", secure=settings.secure, httponly=True, samesite="lax"
        )
        return response

    return app
