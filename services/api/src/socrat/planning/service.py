from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.execution.service import healthy_images
from socrat.learnerstate.policy import digest
from socrat.learnerstate.projector import state_key
from socrat.learnerstate.service import facts_for, project
from socrat.models import (
    CurriculumHead,
    CurriculumRevision,
    DiagnosticSession,
    LearnerGoal,
    LearnerState,
    PlanningCommand,
    SkillPackHead,
    SkillPackVersion,
)
from socrat.planning.contracts import PlanCommand
from socrat.planning.engine import build_plan
from socrat.planning.policy import POLICY, POLICY_DIGEST
from socrat.skillpacks.service import load


class PlanningError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status


def content(db: Session, goal: LearnerGoal, diagnostic: DiagnosticSession):
    # Validate all pins, including the intended target behind a Foundations bridge.
    for pin in sorted(goal.snapshot["pack_versions"], key=lambda x: x["key"]):
        db.scalar(
            select(SkillPackHead).where(SkillPackHead.pack_key == pin["key"]).with_for_update()
        )
        item = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == pin["key"], SkillPackVersion.version == pin["version"]
            )
        )
        if item is None or item.status != "released" or item.digest != pin["digest"]:
            raise PlanningError("goal_content_unavailable")
        db.refresh(item)
        if item.status != "released" or load(item).digest() != pin["digest"]:
            raise PlanningError("goal_content_unavailable")
    record = db.get(SkillPackVersion, diagnostic.pack_id)
    if record is None or record.status != "released":
        raise PlanningError("goal_content_unavailable")
    pack = load(record)
    if pack.purpose != "launch" or pack.digest() != diagnostic.snapshot["pack_digest"]:
        raise PlanningError("goal_content_mismatch")
    return record, pack


def view(head: CurriculumHead, revision: CurriculumRevision) -> dict:
    return dict(
        id=revision.id,
        goal_id=head.goal_id,
        revision=head.revision,
        status=head.status,
        review_digest=revision.digest,
        **{k: v for k, v in revision.snapshot.items() if k != "replay_inputs"},
    )


def current(db: Session, goal: LearnerGoal, validate: bool = True) -> dict:
    head = db.get(CurriculumHead, goal.id)
    if head is None:
        raise PlanningError("plan_not_generated", 404)
    revision = db.get(CurriculumRevision, head.active_id)
    if revision is None:
        raise PlanningError("plan_revision_missing", 503)
    if validate:
        diagnostic = db.scalar(
            select(DiagnosticSession).where(DiagnosticSession.goal_id == goal.id)
        )
        if diagnostic is None:
            raise PlanningError("diagnostic_required")
        content(db, goal, diagnostic)
    return view(head, revision)


def command(db: Session, goal: LearnerGoal, body: PlanCommand, as_of: int) -> dict:
    request_digest = digest(body.model_dump())
    existing = db.scalar(
        select(PlanningCommand).where(
            PlanningCommand.goal_id == goal.id,
            PlanningCommand.idempotency_key == body.idempotency_key,
        )
    )
    if existing:
        if existing.request_digest != request_digest:
            raise PlanningError("idempotency_key_reused")
        return existing.outcome
    if not goal.snapshot["routing_outcome"].startswith("accept_"):
        raise PlanningError("accepted_goal_required", 422)
    diagnostic = db.scalar(select(DiagnosticSession).where(DiagnosticSession.goal_id == goal.id))
    if diagnostic is None or diagnostic.result is None or diagnostic.status == "pending_review":
        raise PlanningError("completed_diagnostic_required")
    record, pack = content(db, goal, diagnostic)
    head = db.get(CurriculumHead, goal.id)
    expected = head.revision if head else 0
    if body.expected_revision != expected:
        raise PlanningError("plan_revision_stale")
    before = current(db, goal, False) if head else None
    state = db.get(LearnerState, goal.user_id)
    policy = state.active_policy if state else diagnostic.policy_version
    projection = project(db, goal.user_id, policy, as_of)
    facts = facts_for(db, goal.user_id)
    if body.action in {"confirm", "pause", "resume"}:
        if head is None or before is None:
            raise PlanningError("plan_not_generated")
        if body.action == "confirm":
            if head.status != "draft" or body.reviewed_digest != before["review_digest"]:
                raise PlanningError("plan_review_stale")
            local_date = (
                datetime.fromtimestamp(as_of, ZoneInfo(before["schedule"]["timezone"]))
                .date()
                .isoformat()
            )
            if (
                projection["watermark"] != before["evidence_watermark"]
                or policy != before["learning_policy_version"]
                or local_date != before["start_date"]
            ):
                raise PlanningError("plan_evidence_stale")
            if before["feasibility"] == "date_unfeasible":
                raise PlanningError("feasible_schedule_confirmation_required")
            if not any(day["blocks"] for day in before["days"]):
                raise PlanningError("no_safe_independent_candidate")
            head.status = "confirmed"
        elif body.action == "pause":
            if head.status != "confirmed":
                raise PlanningError("plan_transition_invalid")
            head.status = "paused"
        else:
            if head.status != "paused":
                raise PlanningError("plan_transition_invalid")
            # Resuming always recalculates calendar capacity and needs fresh review.
            body = body.model_copy(update={"action": "recover"})
    if body.action not in {"confirm", "pause"}:
        if body.action == "generate" and head:
            raise PlanningError("plan_already_generated")
        if body.action != "generate" and not head:
            raise PlanningError("plan_not_generated")
        selected = dict(before["schedule"] if before else goal.snapshot["goal"])
        today = datetime.fromtimestamp(as_of, ZoneInfo(selected["timezone"])).date()
        weekdays = sorted(
            body.weekdays
            if body.weekdays is not None
            else selected.get("weekdays", list(range(selected["days_per_week"])))
        )
        minutes = (
            body.minutes
            if body.minutes is not None
            else selected.get("minutes", selected.get("minutes_per_session", 30))
        )
        if body.action == "lighter" and before and minutes >= before["schedule"]["minutes"]:
            raise PlanningError("lighter_day_must_reduce_minutes", 422)
        target = body.target_date or selected["target_date"]
        invalidated = {f.target_event_id for f in facts if f.kind == "invalidated"}
        history = [
            f.model_dump()
            for f in facts
            if f.kind == "scored"
            and f.event_id not in invalidated
            and f.pack_id == record.id
            and f.language == selected["language"]
        ]
        exposures: dict[str, dict] = {}
        exercises = {x.id: x for x in pack.exercises}
        for fact in history:
            for exercise in exercises.values():
                if exercise.family_id == fact["family_id"]:
                    exposure = exposures.setdefault(exercise.id, dict(count=0, last_date=""))
                    exposure["count"] += 1
                    exposure["last_date"] = max(
                        exposure["last_date"],
                        datetime.fromtimestamp(fact["occurred_at"], ZoneInfo(selected["timezone"]))
                        .date()
                        .isoformat(),
                    )
        missed = 0
        if before:
            for day in before["days"]:
                if day["date"] >= today.isoformat() or not day["blocks"]:
                    continue
                exercise_ids = {key for block in day["blocks"] for key in block["exercise_ids"]}
                families = {exercises[key].family_id for key in exercise_ids}
                completed = any(
                    f["valid"]
                    and f["goal_id"] == goal.id
                    and f["finalized"]
                    and f["mode"] in {"practice", "retention"}
                    and f["hint_level"] == 0
                    and f["family_id"] in families
                    and datetime.fromtimestamp(f["occurred_at"], ZoneInfo(selected["timezone"]))
                    .date()
                    .isoformat()
                    == day["date"]
                    for f in history
                )
                missed += int(not completed)
        states = {
            x.id: projection["concepts"].get(state_key(record.id, selected["language"], x.id), {})
            for x in pack.concepts
        }
        previous_controller = dict(before["controller"]) if before else None
        if previous_controller is not None and body.minutes is not None:
            previous_controller["workload_minutes"] = minutes
        replay_inputs = dict(
            code_execution=bool(
                db.info.get("execution_settings")
                and db.info["execution_settings"].execution_enabled
            ),
            runtime_refs=healthy_images(db, db.info["execution_settings"], as_of)
            if db.info.get("execution_settings")
            else [],
            track=goal.snapshot["active_track"],
            language=selected["language"],
            states=states,
            today=today.isoformat(),
            as_of=as_of,
            weekdays=weekdays,
            minutes=minutes,
            target_date=target,
            history=history,
            exposures=exposures,
            previous=previous_controller,
            missed_days=missed,
        )
        plan = build_plan(pack, **{**replay_inputs, "today": today})
        old_nodes = {x["concept_id"]: x for x in before["nodes"]} if before else {}
        plan.update(
            dict(
                pack_id=record.id,
                pack_digest=record.digest,
                pack_version=pack.version,
                planner_policy_version=POLICY.version,
                planner_policy_digest=POLICY_DIGEST,
                learning_policy_version=policy,
                evidence_watermark=projection["watermark"],
                as_of=as_of,
                start_date=today.isoformat(),
                declared_track=goal.snapshot["declared_track"],
                active_track=goal.snapshot["active_track"],
                replay_inputs=replay_inputs,
                schedule=dict(
                    weekdays=weekdays,
                    days_per_week=len(weekdays),
                    minutes=minutes,
                    language=selected["language"],
                    timezone=selected["timezone"],
                    target_date=target,
                ),
                change=dict(
                    action=body.action,
                    added=[
                        x["concept_id"] for x in plan["nodes"] if x["concept_id"] not in old_nodes
                    ],
                    removed=sorted(set(old_nodes) - {x["concept_id"] for x in plan["nodes"]}),
                    changed=[
                        x["concept_id"]
                        for x in plan["nodes"]
                        if x["concept_id"] in old_nodes and x != old_nodes[x["concept_id"]]
                    ],
                    reason_codes=[body.action] + plan["reason_codes"],
                ),
            )
        )
        revision = CurriculumRevision(
            goal_id=goal.id,
            user_id=goal.user_id,
            revision=expected + 1,
            snapshot=plan,
            digest=digest(plan),
            created_at=as_of,
        )
        db.add(revision)
        db.flush()
        if head is None:
            head = CurriculumHead(
                goal_id=goal.id, active_id=revision.id, revision=1, status="draft"
            )
            db.add(head)
        else:
            head.active_id, head.revision, head.status = revision.id, revision.revision, "draft"
    else:
        # Status changes consume the concurrency revision too.
        assert head is not None
        prior_revision = db.get(CurriculumRevision, head.active_id)
        assert prior_revision is not None
        revision = CurriculumRevision(
            goal_id=goal.id,
            user_id=goal.user_id,
            revision=expected + 1,
            snapshot={
                **before_snapshot(before),
                "replay_inputs": prior_revision.snapshot["replay_inputs"],
                "change": {"action": body.action, "reason_codes": [body.action]},
            },
            created_at=as_of,
        )
        revision.digest = digest(revision.snapshot)
        db.add(revision)
        db.flush()
        head.active_id, head.revision = revision.id, revision.revision
    outcome = view(head, revision)
    db.add(
        PlanningCommand(
            goal_id=goal.id,
            idempotency_key=body.idempotency_key,
            request_digest=request_digest,
            outcome=outcome,
            created_at=as_of,
        )
    )
    record_event(
        db,
        goal.user_id,
        "plan.confirmed" if body.action == "confirm" else "plan.adapted",
        revision.id,
    )
    if not any(x["blocks"] for x in outcome["days"]):
        record_event(db, goal.user_id, "plan.content_gap", revision.id)
    return outcome


def before_snapshot(before: dict | None) -> dict:
    assert before is not None
    return {
        key: value
        for key, value in before.items()
        if key not in {"id", "goal_id", "revision", "status", "review_digest"}
    }
