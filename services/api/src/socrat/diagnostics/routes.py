"""Owned diagnostic commands and protected replay/calibration operations."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.database import record_event
from socrat.diagnostics.calibration import outcome_pairs, summarize
from socrat.diagnostics.service import (
    DiagnosticError,
    complete,
    create_diagnostic,
    public_view,
    respond,
    result_view,
)
from socrat.learnerstate.policy import POLICIES, digest
from socrat.learnerstate.projector import EvidenceFact
from socrat.learnerstate.service import append_fact, facts_for, project, promote_policy
from socrat.models import (
    DiagnosticResponse,
    DiagnosticSession,
    LearnerGoal,
    LearnerState,
    LearningEvidence,
    User,
    identifier,
    now,
)
from socrat.skillpacks.routes import require_admin
from socrat.skillpacks.schema import Contract
from socrat.skillpacks.service import PackError

router = APIRouter(prefix="/api/v1")


class ResponseInput(Contract):
    attempt_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    revision: int = Field(ge=0)
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    answer: str = Field(max_length=2000)
    report_problem: bool = False


class ReplayInput(Contract):
    policy_version: Literal["1.0.0", "1.0.1"]
    as_of: int = Field(ge=0)


class PromotionInput(ReplayInput):
    projection_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_reference: str = Field(min_length=1, max_length=512)


class CorrectionInput(Contract):
    event_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    evidence_reference: str = Field(min_length=1, max_length=512)


def identity(request: Request, db: Session, write: bool = False) -> str:
    session = require_session(request, db)
    if write:
        if not request.app.state.settings.diagnostics_enabled:
            raise HTTPException(404, "not_found")
        require_csrf(request, session)
        # All learning writes serialize on the canonical learner, not delivery time.
        db.scalar(select(User).where(User.id == session.user_id).with_for_update())
    return session.user_id


def owned(db: Session, user_id: str, diagnostic_id: str) -> DiagnosticSession:
    session = db.scalar(
        select(DiagnosticSession).where(
            DiagnosticSession.id == diagnostic_id, DiagnosticSession.user_id == user_id
        )
    )
    if session is None:
        raise HTTPException(404, "not_found")
    return session


def boundary(exc):
    if isinstance(exc, IntegrityError):
        raise HTTPException(409, "concurrent_diagnostic_retry") from exc
    raise HTTPException(exc.status, exc.code) from exc


@router.post("/goals/{goal_id}/diagnostics")
def start(goal_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            goal = db.scalar(
                select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
            )
            if goal is None:
                raise HTTPException(404, "not_found")
            session = create_diagnostic(db, goal, now())
            return public_view(db, session, now())
    except (DiagnosticError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/goals/{goal_id}/diagnostics")
def sessions(goal_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        goal = db.scalar(
            select(LearnerGoal).where(LearnerGoal.id == goal_id, LearnerGoal.user_id == user_id)
        )
        if goal is None:
            raise HTTPException(404, "not_found")
        records = db.scalars(select(DiagnosticSession).where(DiagnosticSession.goal_id == goal_id))
        try:
            return {"items": [public_view(db, item, now()) for item in records]}
        except (DiagnosticError, PackError) as exc:
            boundary(exc)


@router.get("/diagnostics/{diagnostic_id}")
@router.get("/diagnostics/{diagnostic_id}/next")
def read(diagnostic_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        try:
            return public_view(db, owned(db, user_id, diagnostic_id), now())
        except (DiagnosticError, PackError) as exc:
            boundary(exc)


@router.post("/diagnostics/{diagnostic_id}/responses")
def response(diagnostic_id: str, body: ResponseInput, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            return respond(db, owned(db, user_id, diagnostic_id), body.model_dump(), now())
    except (DiagnosticError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.post("/diagnostics/{diagnostic_id}/complete")
def completion(diagnostic_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            return complete(db, owned(db, user_id, diagnostic_id), now())
    except (DiagnosticError, PackError, IntegrityError) as exc:
        boundary(exc)


@router.get("/diagnostics/{diagnostic_id}/result")
def result(diagnostic_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        session = owned(db, user_id, diagnostic_id)
        if session.result is None:
            raise HTTPException(409, "diagnostic_result_pending")
        return result_view(db, session)


@router.get("/learner-state")
def learner_state(request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        state = db.get(LearnerState, user_id)
        return project(db, user_id, state.active_policy if state else "1.0.0", now())


@router.get("/learner-state/evidence")
def learner_evidence(request: Request):
    with Session(request.app.state.engine) as db:
        user_id = identity(request, db)
        facts = facts_for(db, user_id)
        return {"items": [fact.model_dump() for fact in facts[-100:]], "total": len(facts)}


def admin_learner(request: Request, db: Session, user_id: str, write: bool = False) -> str:
    actor = require_admin(request, db, write)
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(404, "not_found")
    return actor


@router.post("/admin/learner-state/{user_id}/replay")
def replay_state(user_id: str, body: ReplayInput, request: Request):
    with Session(request.app.state.engine) as db:
        admin_learner(request, db, user_id, True)
        try:
            projection = project(db, user_id, body.policy_version, body.as_of)
        except ValueError as exc:
            raise HTTPException(409, "learning_replay_invalid") from exc
        stored = db.get(LearnerState, user_id)
        return {
            "projection": projection,
            "projection_digest": digest(projection),
            "stored_matches": bool(stored and stored.projection == projection),
            "policy_digest": digest(POLICIES[body.policy_version].model_dump()),
        }


@router.post("/admin/learner-state/{user_id}/policy")
def policy(user_id: str, body: PromotionInput, request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        actor = admin_learner(request, db, user_id, True)
        active = db.scalar(
            select(DiagnosticSession).where(
                DiagnosticSession.user_id == user_id, DiagnosticSession.result.is_(None)
            )
        )
        if active is not None:
            raise HTTPException(409, "diagnostic_policy_pinned")
        try:
            return promote_policy(
                db,
                user_id,
                actor,
                body.policy_version,
                body.as_of,
                body.evidence_reference,
                body.projection_digest,
            )
        except ValueError as exc:
            raise HTTPException(409, "policy_review_stale") from exc


@router.post("/admin/learner-state/{user_id}/corrections")
def correction(user_id: str, body: CorrectionInput, request: Request):
    with Session(request.app.state.engine) as db, db.begin():
        actor = admin_learner(request, db, user_id, True)
        facts = facts_for(db, user_id)
        target = next(
            (fact for fact in facts if fact.event_id == body.event_id and fact.kind == "scored"),
            None,
        )
        if target is None:
            raise HTTPException(404, "not_found")
        previous = next((fact for fact in facts if fact.target_event_id == target.event_id), None)
        if previous:
            return {"event_id": previous.event_id, "already_corrected": True}
        timestamp = now()
        state = db.get(LearnerState, user_id)
        fact = EvidenceFact.model_validate(
            {
                **target.model_dump(),
                "event_id": identifier(),
                "sequence": len(facts) + 1,
                "kind": "invalidated",
                "target_event_id": target.event_id,
                "score": 0.0,
                "quality": 0.0,
                "valid": False,
                "occurred_at": timestamp,
                "policy_version": state.active_policy if state else "1.0.0",
                "policy_digest": digest(
                    POLICIES[state.active_policy if state else "1.0.0"].model_dump()
                ),
                "reason_code": "operator_evidence_invalidated",
            }
        )
        append_fact(db, user_id, fact)
        # Completed results are historical snapshots; expose that a correction requires fresh placement.
        record_event(db, actor, "learning.correction_reviewed", fact.event_id)
        return {
            "event_id": fact.event_id,
            "already_corrected": False,
            "affected_diagnostic_ids": [
                item.id
                for item in db.scalars(
                    select(DiagnosticSession)
                    .join(
                        DiagnosticResponse, DiagnosticResponse.diagnostic_id == DiagnosticSession.id
                    )
                    .where(DiagnosticResponse.attempt_id == target.source_id)
                )
            ],
        }


@router.get("/admin/diagnostics/calibration")
def calibration(request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        records = db.scalars(
            select(DiagnosticSession).order_by(
                DiagnosticSession.started_at.desc(), DiagnosticSession.id
            )
        ).all()
        segments: dict[str, dict] = {}
        pairs_by_segment: dict[str, list] = {}
        for item in records:
            key = f"{item.snapshot['declared_track']}:{item.snapshot['language']}"
            cell = segments.setdefault(
                key,
                {
                    "track": item.snapshot["declared_track"],
                    "language": item.snapshot["language"],
                    "started": 0,
                    "completed": 0,
                    "limited": 0,
                    "pending_review": 0,
                    "synthetic": request.app.state.settings.environment in {"development", "test"},
                    "outcome_pairs": 0,
                    "calibration": "insufficient_data",
                },
            )
            cell["started"] += 1
            current_result = result_view(db, item)
            cell["completed"] += int(
                bool(current_result and current_result["placement_sufficient"])
            )
            cell["limited"] += int(
                bool(current_result and not current_result["placement_sufficient"])
            )
            cell["pending_review"] += int(item.status == "pending_review")
            if current_result and current_result["placement_sufficient"]:
                pairs_by_segment.setdefault(key, []).extend(
                    outcome_pairs(
                        current_result,
                        item.pack_id,
                        item.snapshot["language"],
                        facts_for(db, item.user_id),
                    )
                )
        for key, cell in segments.items():
            cell.update(summarize(pairs_by_segment.get(key, [])))
        evidence = db.scalars(select(LearningEvidence)).all()
        return {
            "query_version": "1.0.0",
            "items": list(segments.values()),
            "evidence_events": len(evidence),
            "excluded_events": sum(not record.payload["valid"] for record in evidence),
            "note": "Calibration needs subsequent eligible independent outcomes; diagnostic completion is not activation.",
        }
