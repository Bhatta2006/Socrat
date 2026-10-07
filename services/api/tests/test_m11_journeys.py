"""200 independent local API journeys; human/hosted alpha acceptance stays separate.

Each case owns a freshly migrated database. The execution worker is simulated;
Python/C++/Java protocol coverage here does not execute those language runtimes.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import platform as platform
from test_learning_sessions import complete_code_journey

from socrat.accountability.privacy import erase_once, owned_filters
from socrat.models import Base, LearningEvidence, LearningSession

CELLS = [
    (track, language)
    for track in ("foundations", "interview", "competitive")
    for language in ("python", "cpp", "java")
]
JOURNEYS = [(*CELLS[index % len(CELLS)], index) for index in range(200)]


@pytest.mark.parametrize(
    "track,language,journey",
    JOURNEYS,
    ids=[f"{track}-{language}-{index:03d}" for track, language, index in JOURNEYS],
)
def test_complete_alpha_journey(platform, monkeypatch, track, language, journey):
    app, client, headers, goal, session = complete_code_journey(
        platform, monkeypatch, track, language
    )
    app.state.settings.dashboard_enabled = True
    owner = client.get("/api/v1/me").json()["id"]
    with Session(app.state.engine) as db:
        evidence_ids = list(db.scalars(select(LearningEvidence.id)))
    progress = client.get(f"/api/v1/progress?goal_id={goal['id']}")
    assert progress.status_code == 200, progress.text
    assert progress.json()["goal_id"] == goal["id"]
    exported = client.post("/api/v1/privacy/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert "reference_solution" not in exported.text
    assert "manifest" not in exported.text
    assert exported.json()["data"]["learning_sessions"]
    with Session(app.state.engine) as db:
        assert list(db.scalars(select(LearningEvidence.id))) == evidence_ids
        assert db.get(LearningSession, session["id"]).status == "completed"
    deletion = client.post(
        "/api/v1/privacy/delete",
        headers=headers,
        json={"confirmation": "DELETE MY DATA"},
    )
    assert deletion.status_code == 202, deletion.text
    receipt = deletion.json()
    assert client.get("/api/v1/me").status_code == 401
    assert erase_once(app.state.engine, receipt["created_at"]) == 1
    assert erase_once(app.state.engine, receipt["created_at"]) == 0
    with Session(app.state.engine) as db:
        for name, predicate in owned_filters(owner).items():
            assert db.execute(select(Base.metadata.tables[name]).where(predicate)).first() is None
    path = f"/api/v1/privacy/requests/{receipt['id']}"
    assert client.get(path).status_code == 404
    response = client.get(path, headers={"X-Privacy-Token": receipt["receipt_token"]})
    assert response.status_code == 200
    assert response.json()["tasks"]["database"] == "complete"
    assert response.json()["status"] == "awaiting_external_cleanup"
