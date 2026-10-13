"""Admin overview: allow-listed access and metrics computed from learning data."""

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.catalog.registry import default_catalog


def test_admin_overview_is_private_and_counts_the_funnel(client):  # noqa: F811
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    client.post("/api/v1/activities/lesson:zero:programs-and-output/complete", headers=learner)
    catalog = default_catalog()
    quiz = client.get("/api/v1/quiz/quiz:zero:programs-and-output").json()
    for question in quiz["questions"]:
        item = next(
            q for q in catalog.concept("zero:programs-and-output").quiz if q.id == question["id"]
        )
        client.post(
            "/api/v1/quiz/quiz:zero:programs-and-output/answer",
            json={"item": question["id"], "choice": item.shown(quiz["id"])["answer"]},
            headers=learner,
        )
    assert client.get("/api/v1/admin/overview").status_code == 403

    client.app.state.settings.admin_subjects = ["boss"]
    login(client, subject="boss", name="Boss")
    overview = client.get("/api/v1/admin/overview").json()
    steps = {s["step"]: s["learners"] for s in overview["funnel"]}
    assert steps["Signed up"] == 2 and steps["Enrolled"] == 1
    assert steps["First lesson"] == 1 and steps["First concept check"] == 1
    assert overview["activation"] == {"activated": 1, "signups": 2, "rate": 0.5}
    assert [r["day"] for r in overview["retention"]] == [1, 7, 30]
    assert overview["engagement"]["weekly_active"] >= 1
    assert overview["flagged_items"] == []  # too few answers to judge any item
