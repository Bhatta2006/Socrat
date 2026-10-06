"""M8 atomicity on real PostgreSQL; CI provisions a disposable database per test."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_execution import claim, result
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel
from test_tutor import prepared
from test_tutor import test_fallback_nine_cells_idempotency_and_submit_evidence as verify

from socrat.config import Settings
from socrat.main import create_app
from socrat.models import LearningEvidence, SubmitAssistance, TutorTurn

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="No isolated PostgreSQL configured")


def test_postgres_tutor_evidence_and_receipts(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify((app, client), monkeypatch, "foundations", "python")


def test_postgres_concurrent_hints_and_submit_pin(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        _, client, headers, worker, _, attempt = prepared((app, client), monkeypatch)
        barrier = Barrier(2)

        def concurrent_hint():
            with TestClient(app, base_url="http://localhost:3000") as peer:
                peer.cookies.update(client.cookies)
                barrier.wait(timeout=10)
                return peer.post(
                    f"/api/v1/attempts/{attempt['id']}/tutor",
                    headers=headers,
                    json=dict(
                        idempotency_key="same",
                        draft_revision=0,
                        reasoning="I will trace the sample",
                        requested_level=1,
                    ),
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: concurrent_hint(), range(2)))
        assert all(x.status_code == 200 for x in results)
        assert results[0].json() == results[1].json()
        barrier = Barrier(2)

        def compete(mode):
            with TestClient(app, base_url="http://localhost:3000") as peer:
                peer.cookies.update(client.cookies)
                barrier.wait(timeout=10)
                body = dict(idempotency_key="race", draft_revision=0)
                if mode == "tutor":
                    body.update(reasoning="I traced a new boundary case", requested_level=2)
                return peer.post(
                    f"/api/v1/attempts/{attempt['id']}/{mode}", headers=headers, json=body
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            hint, submit = list(pool.map(compete, ["tutor", "submit"]))
        assert submit.status_code == 200
        assert hint.status_code in {200, 409}
        expected = 2 if hint.status_code == 200 else 1
        job = claim(client, worker)
        assert (
            client.post(
                "/api/v1/execution/worker/result", headers=worker, json=result(job)
            ).status_code
            == 200
        )
        with Session(engine) as db:
            pin = db.get(SubmitAssistance, job.manifest.job_id)
            assert pin.hint_level == expected
            fact = db.scalar(
                select(LearningEvidence).where(LearningEvidence.source_id == attempt["id"])
            )
            assert fact.payload["hint_level"] == expected
            assert len(list(db.scalars(select(TutorTurn)))) == expected
