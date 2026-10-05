"""Rehearse learner lock serialization and immutable planning records on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from m5_support import completed
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.config import Settings
from socrat.main import create_app
from socrat.models import CurriculumRevision, PlanningCommand

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="No isolated PostgreSQL service configured"
)


def test_postgres_serializes_same_key_and_stale_revision(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
            onboarding_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        _, client, headers, goal = completed((app, client), monkeypatch)
        cookies = dict(client.cookies)
        barrier = Barrier(2)
        path = f"/api/v1/goals/{goal['id']}/curriculum/commands"

        def send(index, shared=True):
            with TestClient(app, base_url="http://localhost:3000", cookies=cookies) as peer:
                barrier.wait(timeout=10)
                return peer.post(
                    path,
                    headers=headers,
                    json=dict(
                        action="generate" if shared else "refresh",
                        expected_revision=0 if shared else 1,
                        idempotency_key="shared" if shared else f"different-{index}",
                    ),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(send, range(2)))
        assert all(x.status_code == 200 for x in responses)
        assert responses[0].json() == responses[1].json()
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda i: send(i, False), range(2)))
        assert sorted(x.status_code for x in responses) == [200, 409]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(CurriculumRevision)) == 2
            assert db.scalar(select(func.count()).select_from(PlanningCommand)) == 2
            with pytest.raises(DBAPIError):
                db.execute(update(CurriculumRevision).values(digest="0" * 64))
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(update(PlanningCommand).values(outcome={}))
    app.state.engine.dispose()
