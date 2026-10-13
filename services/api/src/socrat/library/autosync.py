"""Keep linked Codeforces profiles fresh without anyone pressing "Sync".

Runs inside the API process: every few hours it re-syncs accounts not synced for a day,
one at a time, so the shared one-request-per-two-seconds budget is never exceeded.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from socrat.catalog.registry import default_catalog
from socrat.library import codeforces
from socrat.library import service as library
from socrat.models import LinkedAccount, User, now

logger = logging.getLogger("socrat.autosync")
STALE_SECONDS = 24 * 3600
INTERVAL_SECONDS = 6 * 3600
BATCH = 50


async def sync_stale(engine: Engine, limit: int = BATCH) -> int:
    with Session(engine) as db:
        due = [
            (a.user_id, a.handle)
            for a in db.scalars(
                select(LinkedAccount)
                .where(
                    LinkedAccount.platform == "codeforces",
                    (LinkedAccount.synced_at.is_(None))
                    | (LinkedAccount.synced_at < now() - STALE_SECONDS),
                )
                .order_by(LinkedAccount.synced_at)
                .limit(limit)
            )
        ]
    synced = 0
    for user_id, handle in due:
        try:
            profile = await codeforces.fetch_profile(handle)
        except codeforces.CodeforcesError as exc:
            with Session(engine) as db, db.begin():
                account = db.get(LinkedAccount, (user_id, "codeforces"))
                if account is not None:
                    account.sync_error = str(exc)
            continue
        with Session(engine) as db, db.begin():
            user = db.get(User, user_id)
            if user is not None:
                library.apply_profile(db, default_catalog(), user, profile, now())
                synced += 1
    return synced


async def run_forever(engine: Engine) -> None:
    while True:
        try:
            count = await sync_stale(engine)
            if count:
                logger.info('{"event": "codeforces_autosync", "synced": %d}', count)
        except Exception:  # never let a bad sync take down the API
            logger.exception('{"event": "codeforces_autosync_failed"}')
        await asyncio.sleep(INTERVAL_SECONDS)
