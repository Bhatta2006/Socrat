from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from socrat.models import AuditEvent, OutboxEvent


def make_engine(url: str):
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


def record_event(db: Session, actor_id: str, kind: str):
    """No commit here: event and domain mutation share their caller's transaction."""
    db.add(AuditEvent(actor_id=actor_id, kind=kind))
    db.add(OutboxEvent(kind=kind, payload={"schema_version": 1, "actor_id": actor_id}))
