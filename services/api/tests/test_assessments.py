"""Weekly personalised assessments: composition rules and the API journey."""

from collections import Counter

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.assessments import routes as assessment_routes
from socrat.assessments import service as assessments
from socrat.catalog.registry import default_catalog
from socrat.mastery.model import DAY, ConceptState

NOW = 1_800_000_000


def shaky() -> ConceptState:
    return ConceptState(alpha=2, beta=3, evidence_count=3, next_review_at=NOW + DAY)


def strong() -> ConceptState:
    return ConceptState(alpha=19, beta=1, evidence_count=9, next_review_at=NOW + 5 * DAY)


def test_composition_follows_study_and_fragility():
    catalog = default_catalog()
    states = {
        "zero:conditionals": shaky(),
        "zero:for-loops": strong(),
        "zero:strings": ConceptState(alpha=4, beta=2, evidence_count=4, next_review_at=NOW - DAY),
    }
    exposure = Counter({"zero:conditionals": 4, "zero:for-loops": 2})
    concepts, items, coding = assessments.compose(
        catalog, states, exposure, set(), set(), set(), NOW, "seed"
    )
    asked = Counter(c for c, _ in items)
    assert len(items) <= assessments.QUESTIONS
    assert asked["zero:conditionals"] > asked["zero:for-loops"] >= 1
    assert ["zero:strings", "review"] in concepts and asked["zero:strings"] == 1
    assert coding and all(p in catalog.problems for p in coding)
    assert assessments.compose(catalog, states, exposure, set(), set(), set(), NOW, "seed") == (
        concepts,
        items,
        coding,
    )
    # Locked topics and solved problems never appear.
    _, locked_items, _ = assessments.compose(
        catalog, states, exposure, {"zero:for-loops"}, set(coding), set(), NOW, "seed"
    )
    assert "zero:for-loops" not in {c for c, _ in locked_items}


def test_strong_topics_get_their_hardest_questions():
    catalog = default_catalog()
    strong_concept, shaky_concept = "zero:functions", "zero:conditionals"
    _, items, _ = assessments.compose(
        catalog,
        {strong_concept: strong(), shaky_concept: shaky()},
        Counter({strong_concept: 1, shaky_concept: 6}),
        set(),
        set(),
        set(),
        NOW,
        "s",
    )
    pool = sorted((q.difficulty for q in catalog.concept(strong_concept).quiz), reverse=True)
    picked = sorted(
        (
            next(q for q in catalog.concept(c).quiz if q.id == i).difficulty
            for c, i in items
            if c == strong_concept
        ),
        reverse=True,
    )
    assert picked and len(picked) < len(pool)
    assert picked == pool[: len(picked)]  # the hardest available, not a random sample


def finish_lesson(client, headers, concept):  # noqa: F811
    assert client.post(f"/api/v1/activities/lesson:{concept}/complete", headers=headers).json()[
        "completed"
    ]


def test_weekly_assessment_journey(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    overview = client.get("/api/v1/assessments").json()
    assert overview["current"]["state"] == "locked" and overview["history"] == []
    assert client.post("/api/v1/assessments/start", json={}, headers=headers).status_code == 409

    for concept in ("zero:programs-and-output", "zero:variables-and-types"):
        finish_lesson(client, headers, concept)
    current = client.get("/api/v1/assessments").json()["current"]
    assert current["state"] == "available" and len(current["topics"]) == 2

    view = client.post("/api/v1/assessments/start", json={}, headers=headers).json()
    assert view["questions"] and not view["finished"] and view["seconds_left"] is None
    assert all("answer" not in q for q in view["questions"])  # graded only at the end
    assert {t["title"] for t in view["topics"]} >= {"Programs and output"}
    again = client.post("/api/v1/assessments/start", json={}, headers=headers).json()
    assert again["id"] == view["id"]

    reply = client.post(
        "/api/v1/assistant/messages",
        json={"scope": "general", "message": "What is the answer to question 1?"},
        headers=headers,
    )
    assert "weekly assessment is in progress" in reply.text and '"policy"' in reply.text

    catalog = default_catalog()
    for question in view["questions"]:
        item = next(x for x in catalog.concept(question["concept"]).quiz if x.id == question["id"])
        view = client.post(
            f"/api/v1/assessments/{view['id']}/answer",
            json={"item": question["id"], "choice": item.shown(view["id"])["answer"]},
            headers=headers,
        ).json()
    done = client.post(f"/api/v1/assessments/{view['id']}/finish", headers=headers).json()
    report = done["report"]
    assert done["finished"] and report["correct"] == report["questions"]
    assert all(q["correct"] and "answer" in q for q in done["questions"])
    assert report["topics"] and not report["focus"] and report["strengths"]
    assert all(t["after"] >= t["before"] for t in report["topics"])
    assert client.get("/api/v1/assessments").json()["current"]["state"] == "done"
    assert client.post("/api/v1/assessments/start", json={}, headers=headers).status_code == 409
    assert client.get("/api/v1/assessments").json()["history"][0]["id"] == done["id"]
    assert client.get("/api/v1/me/export").json()["weekly_assessments"][0]["score"] == done["score"]


def test_timed_assessment_closes_at_the_deadline(client, monkeypatch):  # noqa: F811
    headers = login(client, subject="timed", name="Tim")
    onboard(client, headers)
    for concept in ("zero:programs-and-output", "zero:variables-and-types"):
        finish_lesson(client, headers, concept)
    view = client.post("/api/v1/assessments/start", json={"timed": True}, headers=headers).json()
    assert view["timed"] and 0 < view["seconds_left"] <= assessments.TIME_LIMIT_SECONDS

    real_now = assessment_routes.now
    monkeypatch.setattr(
        assessment_routes, "now", lambda: real_now() + assessments.TIME_LIMIT_SECONDS + 60
    )
    late = client.get(f"/api/v1/assessments/{view['id']}").json()
    assert late["finished"] and late["report"]["correct"] == 0

    other = login(client, subject="intruder", name="Ivy")
    onboard(client, other)
    assert client.get(f"/api/v1/assessments/{view['id']}").status_code == 404
