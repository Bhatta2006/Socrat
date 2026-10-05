"""Real PostgreSQL serialization and append-only replay rehearsal."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from m4_support import accepted
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.config import Settings
from socrat.learnerstate.policy import canonical
from socrat.learnerstate.service import facts_for, project
from socrat.main import create_app
from socrat.models import DiagnosticAttempt, LearningEvidence, MasteryEvent, User

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="No isolated PostgreSQL service configured"
)


def test_postgres_creation_response_and_replay_races(postgres_kernel):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
            onboarding_enabled=True,
            diagnostics_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        app, client, headers, goal = accepted((app, client))
        cookies = dict(client.cookies)
        barrier = Barrier(2)

        def start(_):
            with TestClient(app, base_url="http://localhost:3000", cookies=cookies) as peer:
                barrier.wait(timeout=10)
                response = peer.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers)
                assert response.status_code == 200, response.text
                return response.json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            sessions = list(executor.map(start, range(2)))
        assert sessions[0]["id"] == sessions[1]["id"]
        session = sessions[0]
        body = dict(
            attempt_id=session["item"]["attempt_id"],
            revision=session["revision"],
            idempotency_key="concurrent-answer",
            answer="two",
        )
        barrier = Barrier(2)

        def respond(_):
            with TestClient(app, base_url="http://localhost:3000", cookies=cookies) as peer:
                barrier.wait(timeout=10)
                response = peer.post(
                    f"/api/v1/diagnostics/{session['id']}/responses", headers=headers, json=body
                )
                assert response.status_code == 200, response.text
                return response.json()["revision"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            assert list(executor.map(respond, range(2))) == [1, 1]
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.subject == "alice"))
            facts = facts_for(db, user.id)
            assert len(facts) == 1
            assert db.scalar(select(func.count()).select_from(MasteryEvent)) == 1
            assert db.scalar(select(func.count()).select_from(DiagnosticAttempt)) == 2
            first = project(db, user.id, "1.0.0", facts[0].occurred_at)
            assert json.loads(canonical(first)) == project(
                db, user.id, "1.0.0", facts[0].occurred_at
            )
            with pytest.raises(DBAPIError):
                db.execute(update(LearningEvidence).values(payload={"tampered": True}))
            db.rollback()
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "0005"
