"""Admin API: only users on the SOCRAT_ADMIN_SUBJECTS allow-list may read it."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from socrat.admin import service as admin
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import User, now

router = APIRouter(prefix="/api/v1/admin")


def require_admin(request: Request, db: Session) -> User:
    user = user_of(request, db)
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
