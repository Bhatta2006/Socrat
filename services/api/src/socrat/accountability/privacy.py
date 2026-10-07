"""Export allowlist and durable erasure with separate external cleanup receipts."""

import secrets
from typing import Any

from sqlalchemy import delete, or_, select

from socrat.auth import token_hash
from socrat.models import Base, LoginSession, PrivacyRequest, User, identifier

# Direct learner ownership plus descendants. Author/reviewer FKs do not imply
# ownership of another learner's work or of published, shared course content.
ROOTS = {
    table.name: table.c.user_id for table in Base.metadata.sorted_tables if "user_id" in table.c
}
ROOTS["audit_events"] = Base.metadata.tables["audit_events"].c.actor_id

EXPORT_FIELDS = {
    "assessment_deferrals": ["goal_id", "cycle", "until_at"],
    "users": [
        "id",
        "issuer",
        "subject",
        "display_name",
        "timezone",
        "adult_confirmed",
        "created_at",
    ],
    "user_preferences": ["revision", "settings"],
    "reminders": ["id", "local_date", "created_at", "opened_at"],
    "learner_goals": ["id", "confirmation_at"],
    "curriculum_revisions": ["id", "goal_id", "revision", "created_at"],
    "learning_sessions": [
        "id",
        "goal_id",
        "local_date",
        "status",
        "progress",
        "created_at",
        "completed_at",
    ],
    "code_attempts": ["id", "goal_id", "exercise_id", "created_at"],
    "code_drafts": ["attempt_id", "source", "revision", "updated_at"],
    "code_runs": ["id", "attempt_id", "status", "created_at"],
    "code_run_sources": ["run_id", "source"],
    "tutor_turns": ["id", "attempt_id", "granted_level", "created_at"],
    "tutor_artifacts": ["turn_id", "reasoning", "response"],
    "diagnostic_sessions": ["id", "goal_id", "status", "started_at", "result"],
    "diagnostic_answers": ["attempt_id", "answer", "created_at"],
    "learning_evidence": ["id", "sequence", "kind", "payload", "created_at"],
    "learner_states": ["active_policy", "projection"],
    "mastery_events": ["evidence_id", "concept_key", "before_state", "after_state", "reason_code"],
    "assessment_sessions": ["id", "goal_id", "status", "started_at", "deadline_at", "result"],
    "assessment_answers": ["item_id", "answer"],
    "assessment_disputes": ["item_id", "rationale", "created_at"],
    "audit_events": ["kind", "created_at"],
}


def owned_filters(user_id):
    """Subqueries remain live until child-first deletion finishes."""
    filters = {name: column == user_id for name, column in ROOTS.items()}
    for table in Base.metadata.sorted_tables:
        parents = []
        for column in table.c:
            for fk in column.foreign_keys:
                parent = fk.column.table
                if parent.name in filters and parent.name != "users":
                    parents.append(column.in_(select(fk.column).where(filters[parent.name])))
        if parents:
            filters[table.name] = or_(
                *parents, *([filters[table.name]] if table.name in filters else [])
            )
    return filters


def export_data(db, user):
    filters = owned_filters(user.id)
    result: dict[str, Any] = {"schema_version": 1, "data": {}}
    for name, fields in EXPORT_FIELDS.items():
        table = Base.metadata.tables[name]
        predicate = table.c.id == user.id if name == "users" else filters[name]
        result["data"][name] = [
            dict(row)
            for row in db.execute(select(*(table.c[x] for x in fields)).where(predicate)).mappings()
        ]
    # Only public goal/schedule information; never private form keys or test manifests.
    for name, keys in (
        ("learner_goals", ["goal", "normalized_statement", "active_track"]),
        ("curriculum_revisions", ["schedule", "feasibility", "milestones"]),
    ):
        table = Base.metadata.tables[name]
        rows = db.execute(select(table.c.id, table.c.snapshot).where(filters[name])).all()
        by_id = {row.id: row.snapshot for row in rows}
        for row in result["data"][name]:
            row["details"] = {key: by_id[row["id"]][key] for key in keys}
    return result


def request_deletion(db, user, stamp, settings, request_id=None, receipt_token=None):
    token = receipt_token or secrets.token_urlsafe(48)
    # All accounts require backup/replica/log verification. Provider deletion is
    # explicitly tracked when learner artifacts ever reached a model gateway.
    turns = Base.metadata.tables["tutor_turns"]
    model_used = any(
        row.get("provider_called", False) or row.get("reserved_microusd", 0) > 0
        for row in db.scalars(select(turns.c.telemetry).where(turns.c.user_id == user.id))
    )
    shadows = Base.metadata.tables["advisor_shadows"]
    model_used |= any(
        row.get("reserved_microusd", 0) > 0
        for row in db.scalars(select(shadows.c.outcome).where(shadows.c.user_id == user.id))
    )
    tasks = {
        "database": "pending",
        "backups_replicas_logs": "pending",
        "provider": "pending" if model_used or settings.tutor_model_enabled else "not_applicable",
        "shared_editorial_lineage": "not_applicable",
    }
    request = PrivacyRequest(
        id=request_id or identifier(),
        target_user_id=user.id,
        token_hash=token_hash(token),
        status="queued",
        tasks=tasks,
        cleanup_context={
            "user_id": user.id,
            "provider_review_window": {
                "start_at": user.created_at,
                "end_at": stamp,
                "configured_provider": settings.tutor_provider
                if tasks["provider"] == "pending"
                else None,
            },
        },
        created_at=stamp,
        deadline_at=stamp + 30 * 86400,
    )
    db.add(request)
    # Revoke every session immediately. The worker serializes on this same user.
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.flush()
    return {**receipt(request), "receipt_token": token}


def receipt(row):
    return {
        "id": row.id,
        "status": row.status,
        "tasks": row.tasks,
        "created_at": row.created_at,
        "deadline_at": row.deadline_at,
        "completed_at": row.completed_at,
    }


def erase(db, request, stamp):
    user_id = request.target_user_id
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise ValueError("erasure_target_missing")
    request.status = "erasing"
    db.flush()  # Trigger authorization exists only inside this transaction.
    filters = owned_filters(user_id)
    outbox = Base.metadata.tables["outbox_events"]
    resource_ids = {user_id}
    for name, predicate in filters.items():
        table = Base.metadata.tables[name]
        if "id" in table.c:
            resource_ids.update(db.scalars(select(table.c.id).where(predicate)))
    request.cleanup_context = {**request.cleanup_context, "resource_ids": sorted(resource_ids)}
    events = or_(
        outbox.c.payload["actor_id"].as_string() == user_id,
        outbox.c.payload["resource_id"].as_string().in_(resource_ids),
    )
    delivered = Base.metadata.tables["delivered_events"]
    db.execute(delete(delivered).where(delivered.c.event_id.in_(select(outbox.c.id).where(events))))
    db.execute(delete(outbox).where(events))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in filters:
            db.execute(delete(table).where(filters[table.name]))
    # Shared editorial records cannot be destroyed with a learner's account.
    # Keep an unlinkable author shell only if those records still reference it;
    # require operator review of free-text editorial data before completion.
    references = []
    for table in Base.metadata.sorted_tables:
        if table.name == "users":
            continue
        for column in table.c:
            if any(fk.target_fullname == "users.id" for fk in column.foreign_keys):
                if db.scalar(select(column).where(column == user_id).limit(1)):
                    references.append(table.name)
    tasks = dict(request.tasks)
    if references:
        user.issuer = "erased"
        user.subject = identifier()
        user.display_name = ""
        user.timezone = "UTC"
        user.adult_confirmed = False
        user.created_at = 0
        tasks["shared_editorial_lineage"] = "pending"
    else:
        db.delete(user)
    tasks["database"] = "complete"
    request.tasks = tasks
    request.target_user_id = None
    request.status = "awaiting_external_cleanup"


def erase_once(engine, stamp):
    from sqlalchemy.orm import Session

    with Session(engine) as db, db.begin():
        row = db.scalar(
            select(PrivacyRequest)
            .where(PrivacyRequest.status == "queued")
            .order_by(PrivacyRequest.created_at, PrivacyRequest.id)
            .with_for_update(skip_locked=True)
        )
        if row is None:
            return 0
        erase(db, row, stamp)
        return 1
