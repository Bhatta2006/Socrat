"""Presenter controls registered only by development demo mode."""

import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.auth import establish_session, require_csrf, require_session
from socrat.clock import now
from socrat.demo.seed import PERSONAS
from socrat.models import DemoClock, LearnerGoal, LearnerState, User, identifier

router = APIRouter(prefix="/api/v1/demo")


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona: Literal["beginner", "interview", "competitive", "fresh"]


class ControlInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["advance", "missed_days", "weekly", "retention", "reset"]
    days: int = Field(default=7, ge=1, le=30)


def boundary(request):
    if (
        not request.app.state.settings.demo_mode
        or request.app.state.settings.environment != "development"
    ):
        raise HTTPException(404, "not_found")


@router.post("/login")
def login(body: LoginInput, request: Request):
    boundary(request)
    # Same exact-origin boundary as local sign-in, checked independently of sessions.
    if request.headers.get("origin") != request.app.state.settings.public_origin:
        raise HTTPException(403, "origin_rejected")
    subject = "demo-fresh-" + identifier() if body.persona == "fresh" else "demo-" + body.persona
    with Session(request.app.state.engine) as db, db.begin():
        user = db.scalar(
            select(User).where(User.issuer == "local-development", User.subject == subject)
        )
        if user is None:
            user = User(
                issuer="local-development",
                subject=subject,
                display_name="New learner"
                if body.persona == "fresh"
                else PERSONAS[body.persona][0],
                timezone="Asia/Kolkata",
            )
            db.add(user)
            db.flush()
        if db.get(LearnerState, user.id) is None:
            # Sample-policy activation is isolated to the demo. Production still
            # requires its existing independent review and projection digest.
            from socrat.learnerstate.policy import digest
            from socrat.learnerstate.service import project, promote_policy

            projection = project(db, user.id, "1.1.0", now())
            promote_policy(
                db,
                user.id,
                user.id,
                "1.1.0",
                now(),
                "Development demo sample-policy activation; not release approval",
                digest(projection),
            )
    return establish_session(
        request, JSONResponse({"persona": body.persona}), "local-development", subject
    )


@router.get("/clock")
def clock(request: Request):
    boundary(request)
    with Session(request.app.state.engine) as db:
        require_session(request, db)
        row = db.get(DemoClock, "demo")
        return {
            "server_now": now(),
            "offset_days": (row.offset_seconds if row else 0) // 86400,
            "scope": "All learners in this isolated demo database",
        }


@router.post("/controls")
def controls(body: ControlInput, request: Request):
    boundary(request)
    with Session(request.app.state.engine) as db, db.begin():
        session = require_session(request, db)
        require_csrf(request, session)
        user = db.get(User, session.user_id)
        if user is None or not user.subject.startswith("demo-"):
            raise HTTPException(403, "demo_learner_required")
        if body.action == "reset":
            from socrat.accountability.privacy import erase, request_deletion

            receipt = request_deletion(db, user, now(), request.app.state.settings)
            from socrat.models import PrivacyRequest

            erase(db, db.get(PrivacyRequest, receipt["id"]), now())
        else:
            row = db.scalar(select(DemoClock).where(DemoClock.id == "demo").with_for_update())
            if row is None:
                row = DemoClock(id="demo", offset_seconds=0)
                db.add(row)
            days = 7 if body.action in {"weekly", "retention"} else body.days
            row.offset_seconds += days * 86400
            db.flush()
            goal = db.scalar(
                select(LearnerGoal)
                .where(LearnerGoal.user_id == user.id)
                .order_by(LearnerGoal.confirmation_at.desc())
            )
            return {
                "server_now": int(time.time()) + row.offset_seconds,
                "offset_days": row.offset_seconds // 86400,
                "goal_id": goal.id if goal else None,
                "message": "The clock moved forward. Due checks and recovery follow your actual saved evidence; no scores or mastery were fabricated.",
            }
    response = login(LoginInput(persona="fresh"), request)
    # Reuse fresh-login policy activation after erasure; keep the UI reset receipt.
    response.body = b'{"reset":true}'
    response.headers["content-length"] = str(len(response.body))
    return response
