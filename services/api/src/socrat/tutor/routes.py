from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.execution.routes import owned
from socrat.execution.service import ExecutionError, content
from socrat.learnerstate.policy import digest
from socrat.models import (
    AdvisorShadow,
    CurriculumHead,
    CurriculumRevision,
    DiagnosticSession,
    LearnerGoal,
    TutorTurn,
    User,
    now,
)
from socrat.planning.service import PlanningError
from socrat.skillpacks.routes import require_admin
from socrat.skillpacks.service import PackError
from socrat.tutor import gateway, service
from socrat.tutor.contracts import HintRequest, ShadowOutput, ShadowRequest

router = APIRouter(prefix="/api/v1")


def identity(request, db, write=False):
    if not request.app.state.settings.tutor_enabled:
        raise HTTPException(404, "not_found")
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
        db.scalar(select(User).where(User.id == session.user_id).with_for_update())
    return session.user_id


@router.post("/attempts/{attempt_id}/tutor")
def hint(attempt_id: str, body: HintRequest, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            user_id = identity(request, db, True)
            return service.request_hint(
                db, owned(db, attempt_id, user_id), body, request.app.state.settings, now()
            )
    except IntegrityError as exc:
        raise HTTPException(409, "concurrent_tutor_retry") from exc
    except (ExecutionError, PackError) as exc:
        raise HTTPException(exc.status, exc.code) from exc


@router.get("/attempts/{attempt_id}/tutor")
def hints(attempt_id: str, request: Request):
    try:
        with Session(request.app.state.engine) as db:
            user_id = identity(request, db)
            attempt = owned(db, attempt_id, user_id)
            if db.scalar(
                select(DiagnosticSession.id).where(
                    DiagnosticSession.user_id == user_id,
                    DiagnosticSession.status == "in_progress",
                    DiagnosticSession.deadline_at > now(),
                )
            ):
                raise HTTPException(403, "tutor_assessment_forbidden")
            _, exercise = content(db, attempt)
            if attempt.snapshot["mode"] != "practice" or exercise.inventory != "practice":
                raise HTTPException(403, "tutor_assessment_forbidden")
            return dict(
                items=[service.view(db, turn) for turn in service.history(db, attempt)],
                assistance_level=service.assistance_level(db, attempt),
                dependency=service.dependency(db, user_id),
            )
    except (ExecutionError, PackError) as exc:
        raise HTTPException(exc.status, exc.code) from exc


@router.post("/admin/goals/{goal_id}/advisor-shadow")
def advisor(goal_id: str, body: ShadowRequest, request: Request):
    settings = request.app.state.settings
    if not settings.tutor_advisor_shadow_enabled:
        raise HTTPException(404, "not_found")
    try:
        with Session(request.app.state.engine) as db, db.begin():
            require_admin(request, db, True)
            goal = db.get(LearnerGoal, goal_id)
            if goal is None:
                raise HTTPException(404, "not_found")
            db.scalar(select(User).where(User.id == goal.user_id).with_for_update())
            head = db.get(CurriculumHead, goal.id)
            if head is None or head.revision != body.expected_revision:
                raise HTTPException(409, "plan_revision_stale")
            revision = db.get(CurriculumRevision, head.active_id)
            if revision is None:
                raise HTTPException(409, "plan_revision_missing")
            old = db.scalar(
                select(AdvisorShadow).where(
                    AdvisorShadow.curriculum_id == revision.id,
                    AdvisorShadow.idempotency_key == body.idempotency_key,
                )
            )
            if old:
                return old.outcome
            # Reuse deterministic filtering/ranking. Never let the model select its envelope.
            decisions = revision.snapshot["decisions"]
            exposures = revision.snapshot["replay_inputs"]["exposures"]
            day = next((x["date"] for x in revision.snapshot["days"] if x["blocks"]), None)
            eligible = sorted(
                [x for x in decisions if x["date"] == day and not x["rejected_by"]],
                key=lambda x: (
                    -x["score"],
                    exposures.get(x["exercise_id"], {}).get("count", 0),
                    exposures.get(x["exercise_id"], {}).get("last_date", ""),
                    x["exercise_id"],
                ),
            )[:8]
            if len(eligible) < 3:
                raise HTTPException(409, "shadow_envelope_unavailable")
            ids = [x["exercise_id"] for x in eligible]
            # Validate pinned content remains released before any call.
            from socrat.planning.service import content as plan_content

            diagnostic = db.scalar(
                select(DiagnosticSession).where(DiagnosticSession.goal_id == goal.id)
            )
            if diagnostic is None:
                raise HTTPException(409, "completed_diagnostic_required")
            plan_content(db, goal, diagnostic)
            context = dict(
                candidates=eligible,
                policy_version=revision.snapshot["planner_policy_version"],
                input_snapshot_hash=revision.digest,
            )
            result = gateway.generate(
                settings,
                prompt="advisor_1.0.0",
                context=context,
                schema=ShadowOutput.model_json_schema(),
                budget_available=service.budget(db, goal.user_id, revision.id, settings, now()),
                rollout_key=goal.user_id,
            )
            proposal, accepted = ids, False
            if result.output is not None:
                try:
                    parsed = ShadowOutput.model_validate(result.output)
                    if (
                        len(parsed.candidate_ids) != len(ids)
                        or len(set(parsed.candidate_ids)) != len(ids)
                        or set(parsed.candidate_ids) != set(ids)
                    ):
                        raise ValueError("outside_envelope")
                    proposal, accepted = parsed.candidate_ids, True
                except ValueError:
                    result.reason = "rejected_output"
            outcome = dict(
                shadow_only=True,
                applied=False,
                baseline=ids,
                proposal=proposal,
                accepted=accepted,
                changed_order=proposal != ids,
                reason=result.reason,
                curriculum_id=revision.id,
                input_snapshot_hash=revision.digest,
                policy_version=revision.snapshot["planner_policy_version"],
                prompt_version="advisor_1.0.0",
                model=settings.tutor_model,
                context_digest=digest(context),
                latency_ms=result.latency_ms,
                reserved_microusd=result.reserved_microusd,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            db.add(
                AdvisorShadow(
                    user_id=goal.user_id,
                    curriculum_id=revision.id,
                    idempotency_key=body.idempotency_key,
                    outcome=outcome,
                    created_at=now(),
                )
            )
            return outcome
    except IntegrityError as exc:
        raise HTTPException(409, "concurrent_shadow_retry") from exc
    except (PackError, PlanningError) as exc:
        raise HTTPException(exc.status, exc.code) from exc


@router.get("/admin/tutor/monitor")
def monitor(request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        turns = list(db.scalars(select(TutorTurn).where(TutorTurn.created_at >= now() - 86400)))
        shadows = list(
            db.scalars(select(AdvisorShadow).where(AdvisorShadow.created_at >= now() - 86400))
        )
        return dict(
            window_seconds=86400,
            turns=len(turns),
            rejected=sum(x.telemetry["reason"] == "rejected_output" for x in turns),
            review_queue=[
                dict(
                    turn_id=x.id,
                    attempt_id=x.attempt_id,
                    track=x.telemetry["track"],
                    language=x.telemetry["language"],
                )
                for x in turns
                if x.outcome["review_required"]
            ],
            latency_alerts=sum(x.telemetry["latency_alert"] for x in turns),
            budget_alerts=sum(x.telemetry["budget_alert"] for x in turns),
            reserved_microusd=sum(x.telemetry["reserved_microusd"] for x in turns)
            + sum(x.outcome["reserved_microusd"] for x in shadows),
            shadow_decisions=len(shadows),
            shadow_disagreements=sum(x.outcome["changed_order"] for x in shadows),
        )
