"""CI exercises PostgreSQL erasure guards and concurrent consent serialization."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from m9_support import prepared, respond, start
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.accountability.privacy import erase_once
from socrat.config import Settings
from socrat.main import create_app
from socrat.models import AssessmentItem, PrivacyRequest

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="No isolated PostgreSQL configured")


def test_postgres_owned_erasure_guards_and_concurrent_preferences(postgres_kernel, monkeypatch):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
        )
    )
    with TestClient(app, base_url="http://localhost:3000") as client:
        app, client, headers, goal = prepared((app, client), monkeypatch)
        assessment = respond(client, headers, start(client, headers, goal), answer="my-trace")
        before = client.get("/api/v1/preferences").json()
        revision = before.pop("revision")
        body = {**before, "expected_revision": revision, "reminders_consent": True}
        barrier = Barrier(2)

        def save(_):
            with TestClient(app, base_url="http://localhost:3000") as peer:
                peer.cookies.update(client.cookies)
                barrier.wait(timeout=10)
                return peer.patch("/api/v1/preferences", headers=headers, json=body).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(save, range(2))) == [200, 409]
        from socrat.worker import remind_once

        remind_once(engine)  # Exercise the worker's canonical User-only row lock.
        with Session(engine) as db:
            with pytest.raises(DBAPIError):
                db.execute(
                    delete(AssessmentItem).where(AssessmentItem.session_id == assessment["id"])
                )
            db.rollback()
        receipt = client.post(
            "/api/v1/privacy/delete", headers=headers, json={"confirmation": "DELETE MY DATA"}
        ).json()
        assert erase_once(engine, receipt["created_at"]) == 1
        with Session(engine) as db:
            assert (
                db.scalar(
                    select(AssessmentItem).where(AssessmentItem.session_id == assessment["id"])
                )
                is None
            )
            assert db.get(PrivacyRequest, receipt["id"]).target_user_id is None
