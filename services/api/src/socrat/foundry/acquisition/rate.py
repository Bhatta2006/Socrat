import math
import time
from contextlib import contextmanager
from email.utils import parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.foundry.compliance import PolicyBlocked
from socrat.foundry.jobs import RetryableError
from socrat.foundry.models import DomainPolicy
from socrat.models import identifier


def policy(db, host: str, *, api: bool = False) -> DomainPolicy:
    row = db.scalar(select(DomainPolicy).where(DomainPolicy.domain == host).with_for_update())
    if row is not None and row.mode == "blocked":
        raise PolicyBlocked("domain_blocked")
    if row is None or row.mode in {"blocked", "link_only"} or row.tos_reviewed_at is None:
        raise PolicyBlocked("domain_not_permitted")
    if row.mode == "api_only" and not api:
        raise PolicyBlocked("api_only")
    return row


class Limiter:
    def __init__(self, engine, *, clock=time.time, sleep=time.sleep):
        self.engine, self.clock, self.sleep = engine, clock, sleep

    @contextmanager
    def slot(self, host: str, context, *, api=False, delay=0):
        token = identifier()
        while True:
            context.reserve()
            with Session(self.engine) as db, db.begin():
                row = policy(db, host, api=api)
                stamp = self.clock()
                leases = {k: v for k, v in row.leases.items() if v > stamp}
                wait = max(row.next_allowed_at, row.blocked_until) - stamp
                if len(leases) >= min(
                    row.max_concurrency, context.settings.max_concurrency_per_domain
                ):
                    wait = max(wait, min(leases.values()) - stamp)
                if wait <= 0:
                    leases[token] = stamp + context.settings.request_timeout_seconds + 1
                    row.leases = leases
                    row.next_allowed_at = stamp + max(
                        row.min_delay_ms / 1000, context.settings.min_delay_ms / 1000, delay
                    )
                    break
            if wait >= context.remaining_seconds():
                raise RetryableError("rate_limit_wait")
            self.sleep(min(wait, 0.25))
        try:
            yield
        finally:
            with Session(self.engine) as db, db.begin():
                released = db.scalar(
                    select(DomainPolicy).where(DomainPolicy.domain == host).with_for_update()
                )
                if released is not None:
                    released.leases = {k: v for k, v in released.leases.items() if k != token}

    def feedback(self, host: str, response):
        with Session(self.engine) as db, db.begin():
            row = db.scalar(
                select(DomainPolicy).where(DomainPolicy.domain == host).with_for_update()
            )
            if row is None:
                return
            stamp = self.clock()
            if response.status in {429, 403} or response.status >= 500:
                row.failures += 1
                wait = min(300, 2 ** min(row.failures, 8))
                value = response.headers.get("retry-after", "")
                try:
                    wait = max(wait, float(value))
                except ValueError:
                    try:
                        wait = max(wait, parsedate_to_datetime(value).timestamp() - stamp)
                    except (ValueError, TypeError, OverflowError):
                        pass
                if response.headers.get("x-ratelimit-remaining") == "0":
                    try:
                        wait = max(
                            wait, float(response.headers.get("x-ratelimit-reset", "0")) - stamp
                        )
                    except ValueError:
                        pass
                if math.isfinite(wait):
                    row.blocked_until = max(row.blocked_until, stamp + wait)
            else:
                row.failures = 0
            if response.headers.get("x-ratelimit-remaining") == "0":
                try:
                    reset = float(response.headers.get("x-ratelimit-reset", str(stamp + 60)))
                    if math.isfinite(reset):
                        row.blocked_until = max(row.blocked_until, reset)
                except ValueError:
                    row.blocked_until = max(row.blocked_until, stamp + 60)
