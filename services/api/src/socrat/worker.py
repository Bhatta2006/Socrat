"""Transactional internal inbox consumer. External consumers need their own idempotency."""

import logging
import time

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat.config import Settings
from socrat.database import make_engine
from socrat.models import DeliveredEvent, OutboxEvent, now


def drain_once(engine: Engine) -> int:
    with Session(engine) as db, db.begin():
        events = db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.delivered_at.is_(None))
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(100)
            .with_for_update(skip_locked=True)
        ).all()
        for event in events:
            if db.get(DeliveredEvent, event.id) is None:
                db.add(DeliveredEvent(event_id=event.id))
            event.delivered_at = now()
        return len(events)


def main():
    engine = make_engine(Settings().database_url)
    try:
        while True:
            try:
                drain_once(engine)
            except Exception:
                logging.error("outbox_batch_failed")  # No payloads, identities or credentials.
            time.sleep(2)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
