"""Transactional internal inbox consumer. External consumers need their own idempotency."""

import logging
import time

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat.accountability.preferences import preferences_for
from socrat.accountability.privacy import erase_once
from socrat.accountability.reminders import enqueue
from socrat.accountability.retention import prune_once
from socrat.config import DatabaseSettings
from socrat.database import make_engine
from socrat.models import DeliveredEvent, OutboxEvent, PrivacyRequest, User, UserPreferences, now


def remind_once(engine: Engine):
    with Session(engine) as db, db.begin():
        users = db.scalars(
            select(User)
            .join(UserPreferences)
            .where(
                ~User.id.in_(
                    select(PrivacyRequest.target_user_id).where(
                        PrivacyRequest.target_user_id.is_not(None)
                    )
                )
            )
            .with_for_update(of=User, skip_locked=True)
        )
        for user in users:
            enqueue(db, user.id, preferences_for(db, user), now())


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
    settings = DatabaseSettings()
    engine = make_engine(settings.database_url_value)
    last_prune = 0
    try:
        while True:
            try:
                erase_once(engine, now())
                if now() - last_prune >= 86400:
                    prune_once(engine, now())
                    last_prune = now()
                if settings.reminders_enabled:
                    remind_once(engine)
                drain_once(engine)
            except Exception:
                logging.error("outbox_batch_failed")  # No payloads, identities or credentials.
            time.sleep(2)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
