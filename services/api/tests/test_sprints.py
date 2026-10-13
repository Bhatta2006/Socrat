"""Focus sprints, the upsolve nudge and upcoming rated rounds."""

import asyncio
import time

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.catalog.registry import default_catalog
from socrat.library import codeforces, sprints
from socrat.library import routes as library_routes
from socrat.mastery.model import DAY, ConceptState

STUDIED = ConceptState(alpha=3, beta=2, evidence_count=2)


def test_sprint_picks_studied_unlocked_unsolved_problems_easiest_first():
    catalog = default_catalog()
    assert sprints.choose(catalog, {}, 1000, set(), set()) == []
    states = {"zero:conditionals": STUDIED, "zero:for-loops": STUDIED, "zero:functions": STUDIED}
    picked = sprints.choose(catalog, states, 1000, set(), set())
    assert len(picked) == 3
    ratings = [sprints.problem_rating(catalog, p) for p in picked]
    assert ratings == sorted(ratings)
    concepts = {catalog.problems[p][1].concepts[0] for p in picked}
    assert len(concepts) == 3  # spread across topics when possible
    without = sprints.choose(catalog, states, 1000, set(picked), {"zero:functions"})
    assert not set(without) & set(picked)
    assert all(catalog.problems[p][1].concepts[0] != "functions" for p in without)


def pass_quiz(client, headers, concept):  # noqa: F811
    catalog = default_catalog()
    quiz = client.get(f"/api/v1/quiz/quiz:{concept}").json()
    for question in quiz["questions"]:
        item = next(q for q in catalog.concept(concept).quiz if q.id == question["id"])
        client.post(
            f"/api/v1/quiz/quiz:{concept}/answer",
            json={"item": question["id"], "choice": item.shown(quiz["id"])["answer"]},
            headers=headers,
        )


def test_sprint_journey_and_deadline(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    blocked = client.post("/api/v1/library/sprints", headers=headers)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "sprint_unavailable"

    pass_quiz(client, headers, "zero:input-and-arithmetic")  # a topic with judged problems
    sprint = client.post("/api/v1/library/sprints", headers=headers).json()
    assert sprint["problems"] and not sprint["finished"] and sprint["seconds_left"] > 0
    assert client.post("/api/v1/library/sprints", headers=headers).json()["id"] == sprint["id"]
    assert client.get("/api/v1/library/sprints").json()["current"]["id"] == sprint["id"]

    real_now = library_routes.now
    monkeypatch.setattr(library_routes, "now", lambda: real_now() + 2 * 3600)
    late = client.get(f"/api/v1/library/sprints/{sprint['id']}").json()
    assert late["finished"] and late["solved"] == 0
    overview = client.get("/api/v1/library/sprints").json()
    assert overview["current"] is None and overview["history"][0]["id"] == sprint["id"]


def test_upsolve_nudge_returns_unfinished_problems(client, monkeypatch):  # noqa: F811
    headers = login(client, subject="ups", name="Uma")
    onboard(client, headers, course="dsa", level="new-to-programming")
    listing = client.get("/api/v1/library?platform=LeetCode&concept=dsa:arrays-hashing&limit=1")
    target = listing.json()["items"][0]["id"]
    client.post(f"/api/v1/library/problems/{target}/opened", headers=headers)
    first = client.get("/api/v1/library/recommendations").json()["problems"]
    assert all(p["kind"] != "upsolve" for p in first)  # too soon to nag

    real_now = library_routes.now
    monkeypatch.setattr(library_routes, "now", lambda: real_now() + 3 * DAY)
    later = client.get("/api/v1/library/recommendations").json()["problems"]
    assert later[0]["kind"] == "upsolve" and later[0]["id"] == target
    assert "3 days ago" in later[0]["reason"]


def test_upcoming_rounds_are_filtered_and_cached(monkeypatch):
    soon = int(time.time()) + 3 * 86400
    rounds = [
        {
            "id": 1,
            "name": "Codeforces Round (Div. 3)",
            "phase": "BEFORE",
            "startTimeSeconds": soon,
            "durationSeconds": 8100,
        },
        {
            "id": 2,
            "name": "Some Gym Mirror",
            "phase": "BEFORE",
            "startTimeSeconds": soon,
            "durationSeconds": 3600,
        },
        {
            "id": 3,
            "name": "Educational Round",
            "phase": "FINISHED",
            "startTimeSeconds": soon,
            "durationSeconds": 7200,
        },
        {
            "id": 4,
            "name": "Codeforces Round (Div. 2)",
            "phase": "BEFORE",
            "startTimeSeconds": soon + 60 * 86400,
            "durationSeconds": 7200,
        },
    ]
    calls = []

    async def fake_call(http, method, params):
        calls.append(method)
        return rounds

    monkeypatch.setattr(codeforces, "_call", fake_call)
    monkeypatch.setattr(codeforces, "_contests", (0.0, []))
    first = asyncio.run(codeforces.upcoming_contests())
    assert [c["id"] for c in first] == [1] and first[0]["duration_minutes"] == 135
    asyncio.run(codeforces.upcoming_contests())
    assert calls == ["contest.list"]  # second call served from cache
