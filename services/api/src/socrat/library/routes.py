"""Practice library API: browse, recommendations, marks and the Codeforces link."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.catalog import practice
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.library import codeforces
from socrat.library import service as library
from socrat.models import LinkedAccount, now

router = APIRouter(prefix="/api/v1/library")
SYNC_COOLDOWN_SECONDS = 600


class MarkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["todo", "attempted", "solved"] | None = None
    bookmarked: bool | None = None


class LinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    handle: str = Field(pattern=codeforces.HANDLE.pattern)


def problem_or_404(problem_id: str) -> str:
    if problem_id not in practice.default_index().problems:
        raise HTTPException(404, "not_found")
    return problem_id


@router.get("")
def browse(
    request: Request,
    q: str = "",
    platform: str = "",
    concept: str = "",
    difficulty: Literal["", "easy", "medium", "hard"] = "",
    rating_min: int = 0,
    rating_max: int = 0,
    sheet: str = "",
    status: Literal["all", "unsolved", "todo", "attempted", "solved", "bookmarked"] = "all",
    sort: Literal["recommended", "easiest", "hardest", "popular", "title"] = "recommended",
    offset: int = 0,
    limit: int = 30,
):
    platforms = tuple(p for p in platform.split(",") if p in practice.PLATFORMS)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return library.listing(
            db,
            cat,
            user,
            now(),
            q=q[:80],
            platforms=platforms,
            concept=concept,
            difficulty=difficulty,
            rating_min=rating_min,
            rating_max=rating_max,
            sheet=sheet,
            status=status,
            sort=sort,
            offset=offset,
            limit=limit,
        )


@router.get("/meta")
def library_meta(request: Request):
    with Session(engine(request)) as db:
        user_of(request, db)
    return library.meta(catalog())


@router.get("/recommendations")
def recommendations(request: Request, limit: int = 6):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return library.recommendations(db, cat, user, now(), max(1, min(limit, 12)))


@router.put("/problems/{problem_id}")
def set_mark(problem_id: str, body: MarkInput, request: Request):
    problem_or_404(problem_id)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return library.mark(db, cat, user, problem_id, now(), body.status, body.bookmarked)


@router.post("/problems/{problem_id}/opened")
def opened(problem_id: str, request: Request):
    problem_or_404(problem_id)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return library.mark(db, cat, user, problem_id, now(), opened=True)


@router.get("/codeforces")
def codeforces_account(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return {"account": library.account_view(library.account_for(db, user.id))}


async def _sync(request: Request, handle: str | None) -> dict:
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        user_id = user.id
        account = library.account_for(db, user.id)
        if handle is None:
            if account is None:
                raise HTTPException(404, "not_linked")
            if account.synced_at and now() - account.synced_at < SYNC_COOLDOWN_SECONDS:
                return {"account": library.account_view(account), "synced": False}
            handle = account.handle
    try:
        profile = await codeforces.fetch_profile(handle)
    except codeforces.CodeforcesError as exc:
        code = str(exc)
        if code in {"handle_not_found", "invalid_handle"}:
            raise HTTPException(422, f"codeforces_{code}") from exc
        with Session(engine(request)) as db, db.begin():
            account = db.get(LinkedAccount, (user_id, "codeforces"))
            if account is not None:
                account.sync_error = code
        raise HTTPException(503, "codeforces_unavailable") from exc
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        account = library.apply_profile(db, catalog(), user, profile, now())
        record_event(db, user.id, "library.codeforces_synced")
        return {"account": library.account_view(account), "synced": True}


@router.post("/codeforces")
async def link_codeforces(body: LinkInput, request: Request):
    return await _sync(request, body.handle)


@router.post("/codeforces/sync")
async def sync_codeforces(request: Request):
    return await _sync(request, None)


@router.delete("/codeforces", status_code=204)
def unlink_codeforces(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        account = library.account_for(db, user.id)
        if account is not None:
            db.delete(account)
