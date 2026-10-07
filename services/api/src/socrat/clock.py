"""Injectable learner clock. Unscoped/production calls always use wall time."""

import time
from contextvars import ContextVar

demo_offset: ContextVar[int] = ContextVar("socrat_demo_offset", default=0)


def now() -> int:
    return int(time.time()) + demo_offset.get()


def offset_for(engine) -> int:
    from sqlalchemy.orm import Session

    from socrat.models import DemoClock

    with Session(engine) as db:
        row = db.get(DemoClock, "demo")
        return row.offset_seconds if row else 0
