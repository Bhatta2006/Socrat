"""Achievements mark real milestones and show progress toward the next one."""

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.learn.achievements import Facts, evaluate


def by_id(badges: list[dict]) -> dict[str, dict]:
    return {b["id"]: b for b in badges}


def test_count_badges_earn_on_the_nth_event_and_report_progress():
    facts = Facts(events={"solves": [30, 10, 20] + list(range(100, 107))}, gate_count=4)
    badges = by_id(evaluate(facts))
    assert badges["first-solve"]["earned"] and badges["first-solve"]["earned_at"] == 10
    assert badges["solved-10"]["earned"] and badges["solved-10"]["earned_at"] == 106
    fifty = badges["solved-50"]
    assert not fifty["earned"] and fifty["value"] == 10 and fifty["goal"] == 50
    assert fifty["earned_at"] is None


def test_course_badge_needs_every_checkpoint_and_streaks_use_the_longest_run():
    badges = by_id(evaluate(Facts(events={"gates": [5, 9]}, gate_count=3, longest_streak=8)))
    assert badges["first-gate"]["earned"] and badges["first-gate"]["earned_at"] == 5
    cleared = badges["course-cleared"]
    assert not cleared["earned"] and (cleared["value"], cleared["goal"]) == (2, 3)
    assert badges["streak-7"]["earned"] and badges["streak-7"]["earned_at"] is None
    assert not badges["streak-30"]["earned"] and badges["streak-30"]["value"] == 8


def test_nothing_is_earned_from_no_activity():
    assert not any(b["earned"] for b in evaluate(Facts()))


def test_progress_lists_achievements_and_a_finished_lesson_earns_the_first(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    before = by_id(client.get("/api/v1/progress").json()["achievements"])
    assert not before["first-lesson"]["earned"]
    assert before["course-cleared"]["goal"] > 1

    first = client.get("/api/v1/today").json()["next"]
    client.post(f"/api/v1/activities/{first['id']}/complete", headers=headers)
    after = by_id(client.get("/api/v1/progress").json()["achievements"])
    assert after["first-lesson"]["earned"] and after["first-lesson"]["earned_at"]
