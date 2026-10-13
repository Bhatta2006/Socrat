"""Plan revisions are logged once per change, even when page loads race."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.catalog.registry import default_catalog
from socrat.learn import service
from socrat.models import Enrollment, PlanRevision, User

NOW = 1_800_000_000


def revisions(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(PlanRevision)) or 0


def test_racing_requests_record_a_changed_plan_once(client):  # noqa: F811
    onboard(client, login(client))
    engine = client.app.state.engine
    catalog = default_catalog()
    with Session(engine) as db, db.begin():
        db.execute(update(Enrollment).values(plan_signature="stale"))
        before = revisions(db)

    first, second = Session(engine), Session(engine)
    try:
        # Both requests read the enrollment before either writes.
        loaded = []
        for db in (first, second):
            enrollment = db.scalar(select(Enrollment))
            loaded.append((db, db.get(User, enrollment.user_id), enrollment))
        for db, user, enrollment in loaded:
            service.plan_for(db, catalog, user, enrollment, NOW)
            db.commit()
    finally:
        first.close()
        second.close()

    with Session(engine) as db:
        assert revisions(db) == before + 1
        assert db.scalar(select(Enrollment.plan_signature)) != "stale"


def test_reads_without_record_never_write(client):  # noqa: F811
    onboard(client, login(client))
    engine = client.app.state.engine
    with Session(engine) as db, db.begin():
        db.execute(update(Enrollment).values(plan_signature="stale"))
        before = revisions(db)
        enrollment = db.scalar(select(Enrollment))
        user = db.get(User, enrollment.user_id)
        service.plan_for(db, default_catalog(), user, enrollment, NOW, record=False)
    with Session(engine) as db:
        assert revisions(db) == before
        assert db.scalar(select(Enrollment.plan_signature)) == "stale"
