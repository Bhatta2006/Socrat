"""Fault injection and SQLite recovery; hosted operational game days remain pending."""

import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform
from test_learning_sessions import complete_code_journey

from socrat.config import Settings
from socrat.main import create_app
from socrat.models import DeliveredEvent, LearningEvidence, OutboxEvent
from socrat.worker import drain_once


def test_outbox_crash_rolls_back_and_retry_delivers_once(platform):
    app, client = platform
    login(client)

    def fail_commit(connection):
        raise RuntimeError("synthetic worker transaction failure")

    event.listen(app.state.engine, "commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="synthetic worker transaction failure"):
            drain_once(app.state.engine)
    finally:
        event.remove(app.state.engine, "commit", fail_commit)
    with Session(app.state.engine) as db:
        assert db.scalar(select(DeliveredEvent)) is None
        assert db.scalar(select(OutboxEvent)).delivered_at is None
    assert drain_once(app.state.engine) == 1
    assert drain_once(app.state.engine) == 0
    with Session(app.state.engine) as db:
        assert len(list(db.scalars(select(DeliveredEvent)))) == 1


def test_backup_restore_preserves_completed_session_and_evidence(platform, monkeypatch, tmp_path):
    app, client, _, goal, session = complete_code_journey(
        platform, monkeypatch, "foundations", "python"
    )
    cookies = dict(client.cookies)
    with Session(app.state.engine) as db:
        evidence = [(row.id, row.payload) for row in db.scalars(select(LearningEvidence))]
    restored_path = tmp_path / "restored.db"
    with sqlite3.connect(app.state.engine.url.database) as source:
        with sqlite3.connect(restored_path) as destination:
            source.backup(destination)
            assert destination.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    restored = create_app(
        Settings(
            database_url=f"sqlite:///{restored_path}",
            environment="test",
            dev_login_enabled=True,
            learning_sessions_enabled=True,
            dashboard_enabled=True,
        )
    )
    try:
        with TestClient(restored, base_url="http://localhost:3000") as peer:
            peer.cookies.update(cookies)
            response = peer.get(f"/api/v1/goals/{goal['id']}/learning-session")
            assert response.status_code == 200, response.text
            assert response.json()["session"] == session
            assert peer.get(f"/api/v1/progress?goal_id={goal['id']}").status_code == 200
            with Session(restored.state.engine) as db:
                assert [
                    (row.id, row.payload) for row in db.scalars(select(LearningEvidence))
                ] == evidence
    finally:
        restored.state.engine.dispose()
