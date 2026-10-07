"""Presentation of reviewed checks; protected assessment service owns admission."""

from sqlalchemy import select

from socrat.models import AssessmentDeferral


def assessment_due(db, goal, pack, concepts, assessments, stamp):
    completed = [x for x in assessments if x.status == "completed" and x.result]
    baseline = next((x for x in completed if x.snapshot["kind"] == "baseline"), None)
    final = next((x for x in completed if x.snapshot["kind"] == "final"), None)
    if final:
        return None
    if not baseline:
        kind, cycle, due_at = "baseline", "baseline", goal.confirmation_at
    elif concepts and all(x["band"] == "mastered" for x in concepts):
        kind, cycle, due_at = "final", "final", stamp
    else:
        from socrat.assessment.service import retention_due

        due = retention_due(db, goal, stamp) if any(x["retention_due"] for x in concepts) else []
        if due:
            kind, due_at = "retention", min(x["due_at"] for x in due)
            cycle = f"retention:{due_at}"
        else:
            # An unpromoted retention policy must not suppress a due weekly check.
            weekly = next((x for x in completed if x.snapshot["kind"] == "weekly"), baseline)
            due_at = weekly.result["completed_at"] + 7 * 86400
            if stamp < due_at:
                return None
            kind, cycle = "weekly", f"weekly:{due_at}"
    forms = [
        x
        for x in pack.assessment_forms
        if x.track == goal.snapshot["active_track"]
        and goal.snapshot["goal"]["language"] in x.languages
    ]
    blueprint_ids = {x.id for x in pack.blueprints if x.kind == kind}
    if not any(x.blueprint_id in blueprint_ids for x in forms):
        return None
    deferred = db.scalar(
        select(AssessmentDeferral).where(
            AssessmentDeferral.goal_id == goal.id, AssessmentDeferral.cycle == cycle
        )
    )
    return {
        "kind": kind,
        "cycle": cycle,
        "due_at": due_at,
        "deferred_until": deferred.until_at if deferred else None,
        "can_defer": deferred is None,
        "actionable": deferred is None or stamp >= deferred.until_at,
    }
