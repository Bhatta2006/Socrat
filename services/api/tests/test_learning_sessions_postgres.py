"""M7 session persistence and immutable pins on an isolated PostgreSQL database."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from m6_support import setup
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_learning_sessions import act
from test_learning_sessions import (
    test_nine_cell_normal_session_submit_resume_and_no_passive_mastery as verify_session,
)
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel
from test_timed_learning import independent, prepared, tick
from test_timed_learning import (
    test_timed_deadline_preserves_source_and_upsolve_is_seen as verify_timed,
)

from socrat.config import Settings
from socrat.main import create_app
from socrat.models import CodeAttempt, LearningSession, SessionCommand

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="No isolated PostgreSQL configured")


def test_postgres_objective_learning_checks(postgres_kernel, monkeypatch):
    from test_learning_content import (
        test_objective_exit_is_exact_and_reflection_has_no_mastery_effect as verify,
    )

    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify((app, client), monkeypatch)


def test_postgres_session_telemetry_and_invalidation(postgres_kernel, monkeypatch):
    from test_learning_history import (
        test_meaningful_activation_requires_valid_submit_and_invalidation_reconciles as verify,
    )

    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify((app, client), monkeypatch)


def test_postgres_mixed_session_variants(postgres_kernel, monkeypatch):
    from test_competitive_sets import (
        test_mixed_session_repairs_are_pinned_owned_seen_and_independently_admitted as verify_mixed,
    )

    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify_mixed((app, client), monkeypatch, "python")


def test_postgres_learning_session_and_receipts(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify_session((app, client), monkeypatch, "foundations", "python")


def test_postgres_concurrent_start_and_command_retry_are_once(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        _, _, headers, _, goal = setup((app, client), monkeypatch)
        app.state.settings.learning_sessions_enabled = True
        plan = client.get(f"/api/v1/goals/{goal['id']}/curriculum").json()
        barrier = Barrier(2)
        cookies = dict(client.cookies)

        def race(path, body):
            def post(_):
                with TestClient(app, base_url="http://localhost:3000") as peer:
                    peer.cookies.update(cookies)
                    barrier.wait(timeout=10)
                    return peer.post(path, headers=headers, json=body)

            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(post, range(2)))
            assert all(x.status_code == 200 for x in responses), [x.text for x in responses]
            assert responses[0].json() == responses[1].json()
            return responses[0].json()

        session = race(
            f"/api/v1/goals/{goal['id']}/learning-session",
            dict(curriculum_revision=plan["revision"]),
        )
        response = race(
            f"/api/v1/learning-sessions/{session['id']}/commands",
            dict(
                action="advance",
                expected_revision=0,
                idempotency_key="concurrent",
                answer="my trace",
            ),
        )
        assert response["revision"] == 1
        with Session(app.state.engine) as db:
            assert db.scalar(select(func.count()).select_from(LearningSession)) == 1
            assert db.scalar(select(func.count()).select_from(SessionCommand)) == 1


def test_postgres_timed_upsolve_and_seen_evidence(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        verify_timed((app, client), monkeypatch, "python")


def test_postgres_concurrent_upsolve_retries_create_one_attempt(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        _, _, headers, worker, goal, session, clock = prepared((app, client), monkeypatch)
        session = independent(client, headers, session)
        session = act(client, headers, session, "start_timed").json()
        block = next(x for x in session["blocks"] if x["status"] == "available")
        tick(client, worker, clock, block["deadline_at"])
        barrier = Barrier(2)
        cookies = dict(client.cookies)

        def repair(_):
            with TestClient(app, base_url="http://localhost:3000") as peer:
                peer.cookies.update(cookies)
                barrier.wait(timeout=10)
                return act(
                    peer,
                    headers,
                    session,
                    "upsolve",
                    key="same-upsolve",
                    error_classification="time_pressure",
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(repair, range(2)))
        assert all(x.status_code == 200 for x in responses), [x.text for x in responses]
        assert responses[0].json() == responses[1].json()
        with Session(app.state.engine) as db:
            assert db.scalar(select(func.count()).select_from(CodeAttempt)) == 2
