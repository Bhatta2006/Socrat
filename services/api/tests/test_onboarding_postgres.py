"""Hosted PostgreSQL confirmation race and funnel reconciliation rehearsal."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from test_foundation import login
from test_onboarding import goal
from test_skill_packs_postgres import POSTGRES_URL
from test_skill_packs_postgres import postgres_kernel as postgres_kernel

from socrat.config import ContentAdminIdentity, Settings
from socrat.main import create_app

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="No isolated PostgreSQL service configured"
)


def test_postgres_concurrent_confirmation_records_one_goal_and_event_pair(postgres_kernel):
    engine, _ = postgres_kernel
    app = create_app(
        Settings(
            database_url=engine.url.render_as_string(hide_password=False),
            environment="test",
            dev_login_enabled=True,
            onboarding_enabled=True,
            content_admin_identities=[
                ContentAdminIdentity(issuer="local-development", subject="alice")
            ],
        )
    )
    barrier = Barrier(2)

    def confirm(_):
        with TestClient(app, base_url="http://localhost:3000") as client:
            login(client)
            profile = client.get("/api/v1/me").json()
            headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": profile["csrf_token"]}
            value = goal().model_dump()
            preview = client.post("/api/v1/onboarding/preview", headers=headers, json=value).json()
            body = dict(
                goal=value,
                review_digest=preview["review_digest"],
                reviewed=True,
                idempotency_key="shared-key",
            )
            barrier.wait(timeout=10)
            response = client.post("/api/v1/onboarding/confirm", headers=headers, json=body)
            if response.status_code == 409:
                response = client.post("/api/v1/onboarding/confirm", headers=headers, json=body)
            assert response.status_code == 200
            return response.json()["id"]

    # Establish the shared adult profile before either race participant previews.
    with TestClient(app, base_url="http://localhost:3000") as client:
        login(client)
        csrf = client.get("/api/v1/me").json()["csrf_token"]
        client.patch(
            "/api/v1/me",
            headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
            json={"display_name": "Synthetic", "timezone": "UTC", "adult_confirmed": True},
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert len(set(executor.map(confirm, range(2)))) == 1
        response = client.get("/api/v1/onboarding/reconciliation")
        assert response.status_code == 200
        assert all(
            item["reconciliation_ratio"] == 1 and item["goals"] == 1
            for item in response.json()["items"].values()
        )
