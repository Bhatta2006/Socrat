"""Practice library: personalised browsing, marks, recommendations and Codeforces sync."""

import pytest
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.library import codeforces, ladder, recommend
from socrat.mastery.model import ConceptState

NOW = 1_800_000_000


def strong(now: int = NOW) -> ConceptState:
    return ConceptState(alpha=19, beta=1, evidence_count=10, next_review_at=now + 86400)


def test_rating_estimate_climbs_the_ladder_tier_by_tier():
    assert ladder.estimate_rating({}, NOW) == 800
    first = {c: strong() for c in ladder.TIERS[0][1]}
    two = first | {c: strong() for c in ladder.TIERS[1][1]}
    assert ladder.estimate_rating(first, NOW) == 1000
    assert ladder.estimate_rating(two, NOW) == 1200
    # A linked contest rating is blended in, not ignored.
    assert 1200 < ladder.estimate_rating(two, NOW, linked=1700) < 1700


def test_recommendations_fit_the_level_and_skip_solved():
    from socrat.catalog.practice import default_index, rating_of
    from socrat.catalog.registry import default_catalog

    index, catalog = default_index(), default_catalog()
    learner = recommend.Learner(
        course="dsa", states={"dsa:two-pointers": strong()}, now=NOW, rating=1200, seed="s"
    )
    picks = recommend.best_for(index, learner, "dsa:two-pointers", 6)
    low, high = recommend.window(learner, "dsa:two-pointers")
    assert picks and all(low - 300 < rating_of(p) < high + 300 for p in picks)
    learner.solved = {picks[0]["id"]}
    assert picks[0]["id"] not in {
        p["id"] for p in recommend.best_for(index, learner, "dsa:two-pointers", 6)
    }
    # Stretch picks for a strong concept lean on rated platforms.
    stretch = recommend.next_problems(index, catalog, learner, None, limit=4)
    assert any(p["kind"] == "stretch" for p in stretch)
    assert all(p["reason"] and p["concept"]["id"] for p in stretch)


def test_codeforces_summary_counts_verdicts_and_skips_gym():
    subs = [
        {"verdict": "OK", "problem": {"contestId": 1873, "index": "A", "tags": ["greedy"]}},
        {
            "verdict": "WRONG_ANSWER",
            "problem": {"contestId": 1873, "index": "A", "tags": ["greedy"]},
        },
        {"verdict": "WRONG_ANSWER", "problem": {"contestId": 1873, "index": "B", "tags": ["dp"]}},
        {"verdict": "OK", "problem": {"contestId": 100001, "index": "A", "tags": ["math"]}},
    ]
    summary = codeforces.summarize(subs)
    assert summary["solved"] == ["cf:1873A"]
    assert summary["attempted"] == ["cf:1873B"]
    assert summary["tag_stats"]["dp"] == {"solved": 0, "unsolved": 1}


def test_library_browse_mark_and_recommend(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    meta = client.get("/api/v1/library/meta").json()
    assert set(meta["platforms"]) == {"LeetCode", "CSES", "Codeforces"}
    assert any(c["id"] == "dsa:two-pointers" for c in meta["concepts"])

    page = client.get("/api/v1/library?concept=dsa:two-pointers&platform=Codeforces&limit=5").json()
    assert page["total"] > 0 and len(page["items"]) == 5
    assert all(p["platform"] == "Codeforces" and p["rating"] for p in page["items"])
    rated = client.get(
        "/api/v1/library?platform=Codeforces&rating_min=1500&rating_max=1600&sort=easiest"
    ).json()["items"]
    assert rated and all(1500 <= p["rating"] <= 1600 for p in rated)
    assert rated == sorted(rated, key=lambda p: p["rating"])

    target = page["items"][0]["id"]
    assert (
        client.put(f"/api/v1/library/problems/{target}", json={"bookmarked": True}).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/library/problems/{target}/opened", headers=headers).json()["status"]
        == "attempted"
    )
    marked = client.put(
        f"/api/v1/library/problems/{target}", json={"status": "solved"}, headers=headers
    ).json()
    assert marked["status"] == "solved"
    solved = client.get("/api/v1/library?status=solved").json()
    assert [p["id"] for p in solved["items"]] == [target]
    unsolved = client.get(
        "/api/v1/library?concept=dsa:two-pointers&platform=Codeforces&status=unsolved"
    )
    assert target not in {p["id"] for p in unsolved.json()["items"]}
    assert client.put("/api/v1/library/problems/cf:0Z", json={}, headers=headers).status_code == 404

    recs = client.get("/api/v1/library/recommendations").json()
    assert recs["level"]["rating"] >= 800 and recs["level"]["name"]
    assert recs["problems"] and all(p["reason"] for p in recs["problems"])
    assert target not in {p["id"] for p in recs["problems"]}
    assert recs["topics"] and recs["topics"][0]["reason"]

    exported = client.get("/api/v1/me/export").json()
    assert exported["practice_marks"][0]["problem"] == target
    # A self-reported solve is weak evidence on the problem's concept.
    assert any(e["kind"] == "external" for e in exported["evidence"])


def test_codeforces_link_uses_synced_profile(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="cp", level="new-to-programming")

    async def fake(handle):
        if handle == "ghost":
            raise codeforces.CodeforcesError("handle_not_found")
        return {
            "handle": "Tourist_fan",
            "rating": 1450,
            "max_rating": 1510,
            "rank": "specialist",
            "solved": ["cf:1000A"],
            "attempted": ["cf:1000B"],
            "tag_stats": {"dp": {"solved": 1, "unsolved": 3}},
        }

    monkeypatch.setattr(codeforces, "fetch_profile", fake)
    bad = client.post("/api/v1/library/codeforces", json={"handle": "ghost"}, headers=headers)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "codeforces_handle_not_found"
    assert (
        client.post(
            "/api/v1/library/codeforces", json={"handle": "x y"}, headers=headers
        ).status_code
        == 422
    )
    linked = client.post(
        "/api/v1/library/codeforces", json={"handle": "tourist_fan"}, headers=headers
    )
    account = linked.json()["account"]
    assert account["rating"] == 1450 and account["weak_tags"] == ["dp"]
    # Synced solves count as solved in the library; the rating lifts the level estimate.
    assert client.get("/api/v1/library?status=solved").json()["items"][0]["id"] == "cf:1000A"
    assert client.get("/api/v1/library/recommendations").json()["level"]["rating"] > 1000
    again = client.post("/api/v1/library/codeforces/sync", headers=headers).json()
    assert again["synced"] is False  # cooldown
    assert client.delete("/api/v1/library/codeforces", headers=headers).status_code == 204
    assert client.get("/api/v1/library/codeforces").json()["account"] is None


@pytest.mark.parametrize("rating", [800, 1350, 2100])
def test_level_view_is_bounded(rating):
    view = recommend.level_view(rating)
    assert 0 <= view["progress"] <= 1 and view["name"]
