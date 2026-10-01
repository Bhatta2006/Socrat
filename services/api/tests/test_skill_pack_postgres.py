"""Isolated PostgreSQL rehearsal of the M2 kernel; CI supplies the database URL."""

import json
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from test_foundation import login
from test_skill_packs import manifest

from socrat.config import Settings
from socrat.main import create_app
from socrat.models import AuditEvent, ContentOperator, OutboxEvent
from socrat.skill_packs import load_eligible_pack
from socrat.worker import drain_once


@pytest.fixture
def postgres_content_platform(monkeypatch):
    supplied = os.environ.get("SOCRAT_M2_POSTGRES_TEST_URL")
    if not supplied:
        pytest.skip("PostgreSQL M2 rehearsal runs only with an explicit CI database URL")
    base_url = make_url(supplied)
    if base_url.get_backend_name() != "postgresql":
        pytest.fail("SOCRAT_M2_POSTGRES_TEST_URL must point to PostgreSQL")
    if base_url.host not in {"localhost", "127.0.0.1"}:
        pytest.fail("M2 PostgreSQL rehearsal requires a local CI database host")
    # Alembic prefers SOCRAT_DATABASE_* environment values over its supplied
    # Config URL. Keep migration writes inside the disposable database.
    for name in tuple(os.environ):
        if name.startswith("SOCRAT_DATABASE_"):
            monkeypatch.delenv(name)

    database_name = f"socrat_m2_{uuid.uuid4().hex}"
    isolated_url = base_url.set(database=database_name)
    admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    app = None
    created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        created = True
        config = Config("alembic.ini")
        config.set_main_option(
            "sqlalchemy.url",
            isolated_url.render_as_string(hide_password=False).replace("%", "%%"),
        )
        command.upgrade(config, "head")
        app = create_app(
            Settings(
                database_url=isolated_url.render_as_string(hide_password=False),
                environment="test",
                dev_login_enabled=True,
            )
        )
        with TestClient(app, base_url="http://localhost:3000") as client:
            yield app, client
    finally:
        if app is not None:
            app.state.engine.dispose()
        if created:
            with admin_engine.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
        admin_engine.dispose()


def actor_headers(app, client, subject: str, role: str | None = None) -> dict[str, str]:
    login(client, subject)
    identity = client.get("/api/v1/me").json()
    if role:
        with Session(app.state.engine) as db, db.begin():
            db.add(ContentOperator(user_id=identity["id"], role=role))
    return {
        "Origin": "http://localhost:3000",
        "X-CSRF-Token": identity["csrf_token"],
    }


def test_m2_import_publish_quarantine_and_outbox_on_postgres(postgres_content_platform):
    app, client = postgres_content_platform
    roles = {
        "author": "author",
        "domain": "domain_reviewer",
        "learning": "learning_reviewer",
        "accessibility": "accessibility_reviewer",
        "rights": "rights_reviewer",
        "assessment": "assessment_reviewer",
        "release": "release_owner",
    }
    for subject, role in roles.items():
        actor_headers(app, client, subject, role)

    for filename in ("dsa-sample.json", "non-dsa-fixture.json"):
        draft = json.loads((Path("contracts/skill-packs") / filename).read_text(encoding="utf-8"))
        response = client.post(
            "/api/v1/admin/skill-packs",
            json=draft,
            headers=actor_headers(app, client, "author"),
        )
        assert response.status_code == 201, response.text
    assert client.get("/api/v1/skill-packs").json() == []

    version_ids = []
    for version in ("1.0.0", "1.1.0"):
        candidate = manifest(key="postgres-rehearsal", version=version)
        if version == "1.1.0":
            candidate["content"][0]["title"] = "Incorrect premise lesson for rollback rehearsal"
        imported = client.post(
            "/api/v1/admin/skill-packs",
            json=candidate,
            headers=actor_headers(app, client, "author"),
        )
        assert imported.status_code == 201, imported.text
        version_id = imported.json()["id"]
        version_ids.append(version_id)
        blocked = client.post(
            f"/api/v1/admin/skill-packs/{version_id}/publish",
            headers=actor_headers(app, client, "release"),
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "content_reviews_incomplete"

        for subject, role in roles.items():
            if not role.endswith("_reviewer"):
                continue
            approved = client.post(
                f"/api/v1/admin/skill-packs/{version_id}/reviews",
                json={
                    "role": role,
                    "decision": "approve",
                    "note": "Synthetic PostgreSQL workflow evidence only",
                },
                headers=actor_headers(app, client, subject),
            )
            assert approved.status_code == 201, approved.text
        published = client.post(
            f"/api/v1/admin/skill-packs/{version_id}/publish",
            headers=actor_headers(app, client, "release"),
        )
        assert published.status_code == 200, published.text
        assert published.json()["digest"] == imported.json()["digest"]

    assert client.get("/api/v1/skill-packs").json()[0]["version"] == "1.1.0"
    assert client.get("/api/v1/skill-packs/postgres-rehearsal/versions/1.0.0").status_code == 200
    with Session(app.state.engine) as db:
        eligible = load_eligible_pack(db, "postgres-rehearsal", "foundations", None)
        assert eligible is not None
        assert eligible.version == "1.1.0"

    quarantined = client.post(
        f"/api/v1/admin/skill-packs/{version_ids[1]}/quarantine",
        json={"reason": "Controlled bad-content PostgreSQL rehearsal"},
        headers=actor_headers(app, client, "release"),
    )
    assert quarantined.status_code == 200, quarantined.text
    assert quarantined.json()["active_version"] == "1.0.0"
    assert client.get("/api/v1/skill-packs").json()[0]["version"] == "1.0.0"
    assert client.get("/api/v1/skill-packs/postgres-rehearsal/versions/1.1.0").status_code == 404
    with Session(app.state.engine) as db:
        eligible = load_eligible_pack(db, "postgres-rehearsal", "foundations", None)
        assert eligible is not None
        assert eligible.version == "1.0.0"
        kinds = set(
            db.scalars(select(AuditEvent.kind).where(AuditEvent.target_id == version_ids[1])).all()
        )
        assert {"skill_pack.published", "skill_pack.quarantined"} <= kinds
        queued = db.scalars(
            select(OutboxEvent).where(OutboxEvent.kind == "skill_pack.quarantined")
        ).all()
        assert len(queued) == 1
        assert queued[0].payload["target_id"] == version_ids[1]
        assert queued[0].delivered_at is None

    assert drain_once(app.state.engine) > 0
    with Session(app.state.engine) as db:
        queued = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == "skill_pack.quarantined"))
        assert queued is not None and queued.delivered_at is not None
