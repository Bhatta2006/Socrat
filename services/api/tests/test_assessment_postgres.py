"""Real PostgreSQL serializes issuance, responses and assessment finalization."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local

import pytest
from fastapi.testclient import TestClient
from m9_support import prepared, respond
from sqlalchemy.orm import Session
from test_foundation import login
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.config import ContentAdminIdentity, Settings
from socrat.main import create_app
from socrat.models import AssessmentSession

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="No isolated PostgreSQL configured")


def test_postgres_concurrent_start_response_completion_and_restart(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    settings = Settings(
        database_url=engine.url.render_as_string(hide_password=False),
        environment="test",
        dev_login_enabled=True,
    )
    app = create_app(settings)
    with TestClient(app, base_url="http://localhost:3000") as client:
        app, client, headers, goal = prepared((app, client), monkeypatch)

        def concurrent(path, body=None):
            barrier = Barrier(2)

            def call(_):
                with TestClient(app, base_url="http://localhost:3000") as peer:
                    peer.cookies.update(client.cookies)
                    barrier.wait(timeout=10)
                    return peer.post(path, json=body, headers=headers)

            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(call, range(2)))
            assert all(x.status_code == 200 for x in responses), [x.text for x in responses]
            assert responses[0].json() == responses[1].json()
            return responses[0].json()

        session = concurrent(
            f"/api/v1/goals/{goal['id']}/assessments", dict(kind="baseline", idempotency_key="same")
        )
        item = session["items"][0]
        session = concurrent(
            f"/api/v1/assessments/{session['id']}/responses",
            dict(item_id=item["id"], revision=0, idempotency_key="same", answer="PRIVATE-M9-KEY"),
        )
        session = respond(client, headers, session)
        finalized = concurrent(f"/api/v1/assessments/{session['id']}/complete")
        assert client.get("/api/v1/learner-state/evidence").json()["total"] == 2
        restarted = create_app(settings)
        with TestClient(restarted, base_url="http://localhost:3000") as peer:
            peer.cookies.update(client.cookies)
            assert peer.get(f"/api/v1/assessments/{session['id']}").json() == finalized
        restarted.state.engine.dispose()


def test_postgres_review_refreshes_revision_after_waiting_for_learner_lock(
    postgres_kernel, monkeypatch
):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        from m9_support import start

        app, client, headers, goal = prepared((app, client), monkeypatch)
        session = start(client, headers, goal)
        session = respond(client, headers, session)
        session = respond(client, headers, session)
        app.state.settings.content_admin_identities = [
            ContentAdminIdentity(issuer="local-development", subject="reviewer")
        ]
        login(client, "reviewer")
        headers = {**headers, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
        barrier = Barrier(2)
        gated = local()
        original = Session.get

        def get_after_both_load(db, entity, *args, **kwargs):
            value = original(db, entity, *args, **kwargs)
            if entity is AssessmentSession and not getattr(gated, "seen", False):
                gated.seen = True
                barrier.wait(timeout=10)
            return value

        monkeypatch.setattr(Session, "get", get_after_both_load)

        def review(item):
            with TestClient(app, base_url="http://localhost:3000") as peer:
                peer.cookies.update(client.cookies)
                return peer.post(
                    f"/api/v1/admin/assessments/items/{item['id']}/review",
                    headers=headers,
                    json=dict(
                        revision=session["revision"],
                        idempotency_key=item["id"],
                        decision="accept",
                        evidence_reference="synthetic-concurrency-review",
                        rationale="Objective result checked.",
                    ),
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(review, session["items"]))
        assert sorted(x.status_code for x in responses) == [200, 409], [x.text for x in responses]
        assert (
            next(x.json() for x in responses if x.status_code == 200)["revision"]
            == session["revision"] + 1
        )
