"""Read-only goal-scoped dashboard. Participation never creates learning evidence."""

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from socrat.accountability.assessment_due import assessment_due
from socrat.learnerstate.projector import state_key
from socrat.learnerstate.service import facts_for, project
from socrat.models import (
    AssessmentItem,
    AssessmentSession,
    CurriculumHead,
    CurriculumRevision,
    DiagnosticSession,
    LearnerState,
    LearningEvidence,
    LearningSession,
    MasteryEvent,
    SkillPackVersion,
)
from socrat.skillpacks.service import load


def progress(db, goal, stamp, settings):
    selected = goal.snapshot["goal"]
    state = db.get(LearnerState, goal.user_id)
    projection = project(db, goal.user_id, state.active_policy if state else "1.0.0", stamp)
    head = db.get(CurriculumHead, goal.id)
    revision = db.get(CurriculumRevision, head.active_id) if head else None
    plan = revision.snapshot if revision else None
    schedule = plan["schedule"] if plan else selected
    zone = ZoneInfo(schedule["timezone"])
    today = datetime.fromtimestamp(stamp, zone).date()
    diagnostic = db.scalar(select(DiagnosticSession).where(DiagnosticSession.goal_id == goal.id))
    pack_id = plan["pack_id"] if plan else diagnostic.pack_id if diagnostic else None
    concepts = []
    record = db.get(SkillPackVersion, pack_id) if pack_id else None
    content_available = record is None or record.status == "released"
    for pin in goal.snapshot["pack_versions"]:
        pinned = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == pin["key"], SkillPackVersion.version == pin["version"]
            )
        )
        content_available &= bool(
            pinned and pinned.status == "released" and pinned.digest == pin["digest"]
        )
    if record:
        pack = load(record)
        track = next((x for x in pack.tracks if x.id == goal.snapshot["active_track"]), None)
        scope = set(track.concept_ids) if track else set()
        for concept in pack.concepts:
            if scope and concept.id not in scope:
                continue
            value = projection["concepts"].get(
                state_key(record.id, selected["language"], concept.id)
            )
            concepts.append(
                {
                    "id": concept.id,
                    "title": concept.title,
                    "band": value["band"] if value else "insufficient_evidence",
                    "confidence": value["confidence"] if value else 0,
                    "retention_due": bool(
                        value and value.get("due_at") is not None and value["due_at"] <= stamp
                    ),
                    "estimate": value["mastery_mean"] if value else None,
                    "reason_codes": value["reason_codes"] if value else ["insufficient_evidence"],
                }
            )
    facts = facts_for(db, goal.user_id)
    invalidated = {x.target_event_id for x in facts if x.kind == "invalidated"}
    effective = [
        x
        for x in facts
        if x.goal_id == goal.id
        and x.kind == "scored"
        and x.event_id not in invalidated
        and x.valid
        and x.finalized
        and x.quality > 0
        and x.mode != "passive"
        and (not pack_id or x.pack_id == pack_id)
        and x.language == selected["language"]
    ]
    trend = []
    for offset in range(3, -1, -1):
        end = today - timedelta(days=offset * 7)
        start = end - timedelta(days=6)
        week = [
            x
            for x in effective
            if start <= datetime.fromtimestamp(x.occurred_at, zone).date() <= end
            and x.mode in {"practice", "assessment", "retention"}
        ]
        entry: dict[str, Any] = {"start": start.isoformat(), "end": end.isoformat()}
        for name, group in (
            ("independent", [x for x in week if x.hint_level == 0]),
            ("assisted", [x for x in week if x.hint_level > 0]),
        ):
            entry[name] = {
                "count": len(group),
                "solve_rate": sum(x.score >= 0.8 for x in group) / len(group) if group else None,
            }
        trend.append(entry)
    sessions = list(db.scalars(select(LearningSession).where(LearningSession.goal_id == goal.id)))
    by_day = {x.local_date: x for x in sessions}
    days = []
    if plan:
        for day in plan["days"]:
            session = by_day.get(day["date"])
            status = (
                "rest" if not day["blocks"] else "paused" if head.status == "paused" else "planned"
            )
            if session:
                status = (
                    "completed"
                    if session.status == "completed"
                    else "paused"
                    if head.status == "paused"
                    else "missed"
                    if day["date"] < today.isoformat()
                    else "in_progress"
                )
            elif day["blocks"] and day["date"] < today.isoformat() and head.status != "paused":
                status = "missed"
            days.append({"date": day["date"], "status": status, "minutes": day["capacity_minutes"]})
    assessments = list(
        db.scalars(
            select(AssessmentSession)
            .where(AssessmentSession.goal_id == goal.id)
            .order_by(AssessmentSession.started_at.desc())
        )
    )

    def assessment_current(session):
        sources = set(
            db.scalars(select(AssessmentItem.id).where(AssessmentItem.session_id == session.id))
        )
        return not any(x.source_id in sources and x.event_id in invalidated for x in facts)

    current_assessments = [x for x in assessments if assessment_current(x)]
    active_assessment = next(
        (
            x
            for x in assessments
            if x.result is None
            and (
                x.status == "pending_review"
                or (x.status == "in_progress" and x.deadline_at > stamp)
            )
        ),
        None,
    )
    final = next(
        (
            x
            for x in current_assessments
            if x.snapshot["kind"] == "final" and x.status == "completed"
        ),
        None,
    )
    due = (
        assessment_due(db, goal, pack, concepts, assessments, stamp)
        if record and settings.assessments_enabled
        else None
    )
    current_day = next((x for x in days if x["date"] == today.isoformat()), None)
    stale = bool(
        plan
        and (
            projection["watermark"] != plan["evidence_watermark"]
            or projection["model_version"] != plan["learning_policy_version"]
        )
    )
    if plan:
        from socrat.tutor.service import exposure_watermark

        stale |= exposure_watermark(db, goal.user_id) != plan.get("tutor_watermark", 0)
    if not content_available:
        action = "content_unavailable"
    elif diagnostic and diagnostic.status == "pending_review":
        action = "review_pending"
    elif not diagnostic or diagnostic.result is None:
        action = "diagnostic" if settings.diagnostics_enabled else "learning_unavailable"
    elif not plan:
        action = "generate_plan" if settings.planning_enabled else "learning_unavailable"
    elif head.status == "paused":
        action = "resume_plan"
    elif final:
        action = "program_complete"
    elif active_assessment and active_assessment.status == "pending_review":
        action = "assessment_review_pending"
    elif active_assessment and settings.assessments_enabled:
        action = "assessment"
    elif head.status == "draft":
        action = "confirm_plan"
    elif due and due["actionable"] and not active_assessment:
        action = "assessment"
    elif today.isoformat() in by_day and by_day[today.isoformat()].status in {
        "in_progress",
        "paused",
    }:
        action = "resume_session" if settings.learning_sessions_enabled else "learning_unavailable"
    elif stale:
        action = "refresh_plan"
    elif any(x["status"] == "missed" for x in days) or not current_day:
        action = "recover"
    elif current_day["status"] == "rest":
        action = "rest"
    elif current_day["status"] == "completed":
        action = "today_complete"
    else:
        action = "resume_session" if current_day["status"] == "in_progress" else "start_session"
        if not settings.learning_sessions_enabled:
            action = "learning_unavailable"

    # Safe summaries only: protected forms and private rubrics never enter this view.
    def outcome(x):
        result = {**x.result, "evidence_current": assessment_current(x)} if x and x.result else None
        return (
            {
                "id": x.id,
                "kind": x.snapshot["kind"],
                "status": "expired" if x.result is None and x.deadline_at <= stamp else x.status,
                "result": result,
            }
            if x
            else None
        )

    evidence_ids = {x.event_id for x in effective}
    changes = list(
        db.scalars(
            select(MasteryEvent)
            .join(LearningEvidence, MasteryEvent.evidence_id == LearningEvidence.id)
            .where(MasteryEvent.user_id == goal.user_id, MasteryEvent.evidence_id.in_(evidence_ids))
            .order_by(LearningEvidence.sequence, MasteryEvent.concept_key)
        )
    )
    return {
        "goal_id": goal.id,
        "statement": goal.snapshot["normalized_statement"],
        "track": goal.snapshot["active_track"],
        "language": selected["language"],
        "target_date": schedule["target_date"],
        "local_date": today.isoformat(),
        "timezone": schedule["timezone"],
        "today": {
            "action": action,
            "minutes": current_day["minutes"] if current_day else 0,
            "session_id": by_day[today.isoformat()].id if today.isoformat() in by_day else None,
        },
        "plan": {
            "revision": head.revision,
            "status": head.status,
            "review_digest": revision.digest if revision else None,
            "feasibility": plan["feasibility"],
            "milestones": plan["milestones"],
            "needs_refresh": stale,
        }
        if plan
        else None,
        "concepts": concepts,
        "trend": trend,
        "schedule": [
            x
            for x in days
            if today.isoformat() <= x["date"] <= (today + timedelta(days=6)).isoformat()
        ],
        "missed_days": sum(x["status"] == "missed" for x in days),
        "assessment": outcome(active_assessment),
        "assessment_due": due if not active_assessment else None,
        "assessments": [outcome(x) for x in assessments[:10]],
        "evidence": [
            {
                "id": x.event_id,
                "concept_ids": x.concept_ids,
                "score": x.score,
                "mode": x.mode,
                "hint_level": x.hint_level,
                "occurred_at": x.occurred_at,
                "reason_code": x.reason_code,
            }
            for x in effective[-100:]
        ],
        "mastery_changes": [
            {
                "concept": x.concept_key.split(":")[-1],
                "before": x.before_state["band"],
                "after": x.after_state["band"],
                "reason": x.reason_code,
            }
            for x in changes[-10:]
        ],
        "uncertainty": "These estimates summarize reviewed evidence. Confidence depends on independent, varied work and delayed checks; they are not credentials.",
    }
