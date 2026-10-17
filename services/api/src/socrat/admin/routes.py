"""Admin API: only users on the SOCRAT_ADMIN_SUBJECTS allow-list may read it."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.admin import drafts
from socrat.admin import service as admin
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import ContentIssue, Evidence, LearningSession, User, now

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


@router.get("/ai-costs")
def ai_costs(request: Request):
    from socrat.assistant import budget

    with Session(engine(request)) as db:
        require_admin(request, db)
        return budget.summary(db, request.app.state.settings, now())


@router.get("/errors")
def error_reports(request: Request):
    from socrat import errors

    with Session(engine(request)) as db:
        require_admin(request, db)
        return {"items": errors.recent(db)}


@router.post("/errors/{report_id}/resolve")
def resolve_error(report_id: str, request: Request):
    from socrat.models import ErrorReport

    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = db.get(ErrorReport, report_id)
        if row is None:
            raise HTTPException(404, "not_found")
        row.status = "resolved"
        record_event(db, user.id, "admin.error_resolved", report_id)
        return {"resolved": True}


@router.get("/learning-quality")
def learning_quality(request: Request):
    """Learning guardrails and closure, without optimizing time spent or reward clicks."""
    with Session(engine(request)) as db:
        require_admin(request, db)
        since = now() - 7 * 86400
        rows = list(db.scalars(select(LearningSession).where(LearningSession.created_at >= since)))
        evidence = list(db.scalars(select(Evidence).where(Evidence.created_at >= since)))
        code = [e for e in evidence if e.kind == "code"]
        completed = [s for s in rows if s.finished_at is not None]
        return dict(
            window_days=7,
            sessions_started=len(rows),
            sessions_completed=len(completed),
            summaries_viewed=sum(bool(s.payload.get("summary_viewed")) for s in completed),
            independent_code_successes=sum(e.score == 1 and e.assistance == 0 for e in code),
            code_evidence_items=len(code),
            high_hint_evidence_items=sum(e.assistance >= 3 for e in code),
            retention_checks=sum(e.kind == "review" for e in evidence),
            retention_successes=sum(e.kind == "review" and e.score >= 0.7 for e in evidence),
            content_issues=[
                dict(
                    concept=i.concept,
                    atom=i.atom_id,
                    version=i.version,
                    reason=i.reason,
                    note=i.note,
                    at=i.created_at,
                )
                for i in db.scalars(select(ContentIssue).where(ContentIssue.created_at >= since))
            ],
        )


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
