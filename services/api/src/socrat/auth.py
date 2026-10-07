import hashlib
import secrets
import time

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.models import LoginSession, PrivacyRequest, User

COOKIE = "socrat_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_session(request: Request, db: Session) -> LoginSession:
    session = db.get(LoginSession, token_hash(request.cookies.get(COOKIE, "")))
    if session is None or session.expires_at <= int(time.time()):
        raise HTTPException(401, "authentication_required")
    if request.method in {"POST", "PATCH", "PUT", "DELETE"} and not request.url.path.startswith(
        "/api/v1/admin/"
    ):
        # Check again after acquiring the learner lock: deletion may have revoked
        # this session while a concurrent write was waiting for the same lock.
        # Editorial operations lock their target learner in the admin service;
        # serializing on the reviewer would interfere with those lock semantics.
        db.scalar(select(User).where(User.id == session.user_id).with_for_update())
        refreshed = db.scalar(
            select(LoginSession)
            .where(LoginSession.token_hash == session.token_hash)
            .execution_options(populate_existing=True)
        )
        if refreshed is None or refreshed.expires_at <= int(time.time()):
            raise HTTPException(401, "authentication_required")
        session = refreshed
    if db.scalar(select(PrivacyRequest.id).where(PrivacyRequest.target_user_id == session.user_id)):
        raise HTTPException(401, "account_deletion_pending")
    return session


def require_csrf(request: Request, session: LoginSession):
    if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), session.csrf_token):
        raise HTTPException(403, "csrf_rejected")


def establish_session(request: Request, response, issuer: str, subject: str):
    settings = request.app.state.settings
    with Session(request.app.state.engine) as db, db.begin():
        user = db.scalar(
            select(User).where(User.issuer == issuer, User.subject == subject).with_for_update()
        )
        if user is None:
            user = User(issuer=issuer, subject=subject)
            db.add(user)
            db.flush()
        if db.scalar(select(PrivacyRequest.id).where(PrivacyRequest.target_user_id == user.id)):
            raise HTTPException(403, "account_deletion_pending")
        old = db.get(LoginSession, token_hash(request.cookies.get(COOKIE, "")))
        if old:
            db.delete(old)
        token = secrets.token_urlsafe(48)
        db.add(
            LoginSession(
                token_hash=token_hash(token),
                user_id=user.id,
                csrf_token=secrets.token_urlsafe(32),
                expires_at=int(time.time()) + settings.session_ttl_seconds,
            )
        )
        record_event(db, user.id, "auth.login")
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.secure,
        samesite="lax",
        path="/",
    )
    return response
