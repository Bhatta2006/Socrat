"""Local PostgreSQL read contention baseline, not a hosted beta load acceptance."""

from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from m6_support import setup
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.config import Settings
from socrat.main import create_app
from socrat.models import LearningEvidence

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="No isolated PostgreSQL configured")


def test_postgres_progress_read_contention(postgres_kernel, monkeypatch, record_property):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    try:
        with TestClient(app, base_url="http://localhost:3000") as client:
            app, client, _, _, goal = setup((app, client), monkeypatch)
            app.state.settings.dashboard_enabled = True
            cookies = dict(client.cookies)
            with Session(engine) as db:
                before = [(row.id, row.payload) for row in db.scalars(select(LearningEvidence))]

            def read_batch(_):
                # Independent client/cookie jars; each HTTP request gets its own DB session.
                with TestClient(app, base_url="http://localhost:3000") as peer:
                    peer.cookies.update(cookies)
                    timings = []
                    for _ in range(25):
                        started = perf_counter()
                        response = peer.get(f"/api/v1/progress?goal_id={goal['id']}")
                        timings.append(perf_counter() - started)
                        assert response.status_code == 200, response.text
                        assert response.json()["goal_id"] == goal["id"]
                    return timings

            with ThreadPoolExecutor(max_workers=8) as pool:
                timings = sorted(
                    value for batch in pool.map(read_batch, range(8)) for value in batch
                )
            assert len(timings) == 200
            record_property("scope", "local_in_process_postgres_progress_reads")
            record_property("requests", 200)
            record_property("concurrency", 8)
            record_property("p95_seconds", timings[189])
            with Session(engine) as db:
                assert before == [
                    (row.id, row.payload) for row in db.scalars(select(LearningEvidence))
                ]
    finally:
        app.state.engine.dispose()
