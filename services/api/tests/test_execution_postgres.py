"""Durable broker and immutable execution jobs on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from test_execution import (
    test_nine_cells_drafts_runs_submits_signature_secrecy_and_exactly_once as verify_submission,
)
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.config import Settings
from socrat.execution.protocol import JobEnvelope
from socrat.main import create_app

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="No isolated PostgreSQL configured")


def test_postgres_verified_submit_and_immutable_jobs(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify_submission((app, client), monkeypatch, "foundations", "python")


def test_postgres_workers_claim_once_and_duplicate_callbacks_append_once(
    postgres_kernel, monkeypatch
):
    from m6_support import profiles, setup
    from test_execution import queue, result, start

    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        _, client, headers, worker, goal = setup((app, client), monkeypatch)
        attempt = start(client, headers, goal)
        assert queue(client, headers, attempt).status_code == 200
        assert (
            client.post(
                "/api/v1/execution/worker/heartbeat",
                headers=worker,
                json=dict(worker_id="worker-2", images=[x["image"] for x in profiles()]),
            ).status_code
            == 200
        )
        barrier = Barrier(2)

        def claim_job(worker_id):
            with TestClient(app, base_url="http://localhost:3000") as peer:
                barrier.wait(timeout=10)
                response = peer.post(
                    "/api/v1/execution/worker/claim", headers=worker, json=dict(worker_id=worker_id)
                )
                assert response.status_code == 200, response.text
                return worker_id, response.json()["job"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(claim_job, ["worker-1", "worker-2"]))
        claimed = [x for x in claims if x[1]]
        assert len(claimed) == 1
        worker_id, envelope = claimed[0]
        signed = result(JobEnvelope.model_validate(envelope))
        signed["worker_id"] = worker_id
        initial = client.get("/api/v1/learner-state/evidence").json()["total"]

        def callback(_):
            with TestClient(app, base_url="http://localhost:3000") as peer:
                barrier.wait(timeout=10)
                return peer.post("/api/v1/execution/worker/result", headers=worker, json=signed)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(callback, range(2)))
        assert all(x.status_code == 200 for x in results), [x.text for x in results]
        assert results[0].json() == results[1].json()
        assert client.get("/api/v1/learner-state/evidence").json()["total"] == initial + 1
