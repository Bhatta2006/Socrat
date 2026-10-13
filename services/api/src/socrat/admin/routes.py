"""Admin API: only users on the SOCRAT_ADMIN_SUBJECTS allow-list may read it."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from socrat.admin import drafts
from socrat.admin import service as admin
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import User, now

router = APIRouter(prefix="/api/v1/admin")


def require_admin(request: Request, db: Session, write: bool = False) -> User:
    """Allow-listed accounts only; `write` also enforces the CSRF token."""
    user = user_of(request, db, write=write)
    allowed = request.app.state.settings.admin_subjects
    if f"{user.issuer}|{user.subject}" not in allowed and user.subject not in allowed:
        raise HTTPException(403, "forbidden")
    return user


@router.get("/overview")
def overview(request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        require_admin(request, db)
        return admin.overview(db, cat, now())


# ---------------------------------------------------------------- content review queue


class Decision(BaseModel):
    notes: str = Field(default="", max_length=2000)


def _roots(request: Request) -> drafts.Roots:
    return drafts.Roots.from_settings(request.app.state.settings)


def _reviewer(user: User) -> str:
    return user.display_name or user.subject


@router.get("/drafts")
def draft_queue(request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
    return drafts.queue(_roots(request))


@router.get("/drafts/{draft_id}")
def draft_detail(draft_id: str, request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
    return drafts.detail(_roots(request), draft_id)


@router.post("/drafts/{draft_id}/validate")
def draft_validate(draft_id: str, request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db, write=True)
    return drafts.run_validation(_roots(request), catalog(), draft_id)


@router.post("/drafts/{draft_id}/approve")
def draft_approve(draft_id: str, body: Decision, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        result = drafts.approve(_roots(request), draft_id, _reviewer(user), body.notes.strip())
        record_event(db, user.id, "content.draft_approved", draft_id)
    return result


@router.post("/drafts/{draft_id}/request-changes")
def draft_request_changes(draft_id: str, body: Decision, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        result = drafts.request_changes(_roots(request), draft_id, _reviewer(user), body.notes)
        record_event(db, user.id, "content.draft_changes_requested", draft_id)
    return result
