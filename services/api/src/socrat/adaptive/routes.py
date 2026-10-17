"""Adaptive roadmap API: decide proposals, choose a path style, tell Socrat how a topic
feels, and read the weekly review, nudges and learner profile. Every write is CSRF-checked
and runs in one transaction."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.adaptive import proposals, views
from socrat.database import record_event
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import now
from socrat.planner import goals

router = APIRouter(prefix="/api/v1/adaptive")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StyleInput(Strict):
    style: Literal["thorough", "balanced", "fast_track", "goal_focused"]


class FeelInput(Strict):
    concept: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z0-9-]{1,64}$")
    signal: Literal["too_easy", "too_hard", "know_this", "clear"]


class UndoInput(Strict):
    kind: Literal["defer", "skip", "prioritize", "stretch"]
    concept: str = Field(default="", max_length=130)


@router.get("/proposals")
def list_proposals(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return views.proposals_view(db, active(db, user))


@router.post("/proposals/{proposal_id}/{decision}")
def decide(proposal_id: str, decision: Literal["accept", "decline"], request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        row = proposals.decide(
            db, cat, user, enrollment, proposal_id[:36], decision == "accept", now()
        )
        record_event(db, user.id, f"plan.proposal_{row.status}", row.id)
        return dict(proposal=proposals.view(row), **views.proposals_view(db, enrollment))


@router.post("/overrides/undo")
def undo(body: UndoInput, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        if not proposals.undo(enrollment, body.kind, body.concept):
            raise HTTPException(404, "not_found")
        name = cat.concept(body.concept).title if body.concept in cat.concepts else "stretch"
        words = {
            "defer": f"{name} is back in its usual place",
            "skip": f"{name} is back on your path",
            "prioritize": f"{name} is no longer pinned first",
            "stretch": "weekly stretch problems are off",
        }
        learn.revise(
            db, cat, user, enrollment, now(), f"You changed your plan: {words[body.kind]}."
        )
        return views.proposals_view(db, enrollment)


@router.get("/path-options")
def path_options(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return views.plan_options(db, catalog(), user, active(db, user), now())


@router.post("/path-style")
def path_style(body: StyleInput, request: Request):
    """The learner's own choice, so it applies directly (no proposal needed)."""
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        data = dict(enrollment.adaptive or {})
        if data.get("style", "balanced") != body.style:
            data["style"] = body.style
            enrollment.adaptive = data
            label = goals.STYLE_WORDS[body.style][0]
            learn.revise(db, cat, user, enrollment, now(), f"You chose the {label} path.")
        return views.plan_options(db, cat, user, enrollment, now())


@router.post("/feel")
def feel(body: FeelInput, request: Request):
    """G3: "too easy", "too hard" or "I know this" from the learner, applied directly."""
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        if body.concept not in learn.curriculum(cat, enrollment):
            raise HTTPException(404, "not_found")
        learn.require_unlocked(db, cat, enrollment, body.concept, now())
        data = dict(enrollment.adaptive or {})
        overrides = dict(data.get("overrides", {}))
        feelings = dict(overrides.get("feel", {}))
        title = cat.concept(body.concept).title
        if body.signal == "know_this":
            tests = list(overrides.get("testout", []))
            if body.concept not in tests:
                tests.append(body.concept)
            overrides["testout"] = tests
            reason = f"You said you know {title}: a short test-out is first on your list."
        elif body.signal == "clear":
            feelings.pop(body.concept, None)
            reason = f"{title} is back to the pace your results set."
        else:
            feelings[body.concept] = "easy" if body.signal == "too_easy" else "hard"
            reason = (
                f"You said {title} feels easy, so it moves faster."
                if body.signal == "too_easy"
                else f"You said {title} feels hard, so it gets smaller steps."
            )
        overrides["feel"] = feelings
        data["overrides"] = overrides
        enrollment.adaptive = data
        learn.revise(db, cat, user, enrollment, now(), reason)
        return dict(concept=body.concept, feel=feelings.get(body.concept), reason=reason)


@router.get("/weekly-review")
def weekly_review(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.weekly_review(db, catalog(), user, active(db, user), now())


@router.post("/weekly-review/seen", status_code=204)
def weekly_seen(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        views.mark_weekly_seen(user, active(db, user), now())


@router.get("/nudges")
def nudges(request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        enrollment = active(db, user)
        plan = learn.plan_for(db, cat, user, enrollment, now())
        return {"nudges": views.nudges(db, cat, user, enrollment, plan, now())}


@router.get("/profile")
def profile(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return views.profile_view(db, catalog(), user, active(db, user), now())
