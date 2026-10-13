"""Anonymous Core Web Vitals: same-origin only, bounded, summarised at p75 per page."""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from test_learner_api import ORIGIN, client  # noqa: F401  (client is a fixture)

from socrat import vitals


def beacon(client, samples, origin=ORIGIN):  # noqa: F811
    return client.post(
        "/api/v1/vitals",
        content=json.dumps({"samples": samples}),
        headers={"Origin": origin, "Content-Type": "text/plain;charset=UTF-8"},
    )


def test_vitals_accept_same_origin_beacons_and_drop_noise(client):  # noqa: F811
    lcp = {"route": "/today", "metric": "LCP", "value": 1800, "device": "mobile"}
    assert beacon(client, [lcp], origin="https://evil.example").status_code == 403
    assert beacon(client, [{**lcp, "metric": "XYZ"}]).status_code == 422
    assert beacon(client, [lcp] * 11).status_code == 422
    ok = beacon(
        client,
        [
            lcp,
            {**lcp, "value": 3200},
            {**lcp, "value": 2000},
            {**lcp, "value": 2100},
            {**lcp, "route": "/secret/123"},  # unknown route: dropped
            {**lcp, "value": 999_999},  # absurd value: dropped
            {"route": "/today", "metric": "INP", "value": 120, "device": "mobile"},
        ],
    )
    assert ok.status_code == 204
    with Session(client.app.state.engine) as db:
        summary = vitals.summary(db, datetime.now(UTC).date())
    [today] = summary["pages"]
    assert today["route"] == "/today" and today["samples"] == 4
    assert today["LCP"] == {"p75": 3200, "ok": False}  # p75 of 1800, 2000, 2100, 3200
    assert today["INP"] == {"p75": 120, "ok": True}


def test_admin_overview_reports_page_speed(client):  # noqa: F811
    from test_learner_api import login

    beacon(client, [{"route": "/", "metric": "CLS", "value": 0.02, "device": "desktop"}])
    client.app.state.settings.admin_subjects = ["boss"]
    login(client, subject="boss", name="Boss")
    overview = client.get("/api/v1/admin/overview").json()
    assert overview["vitals"]["budgets"]["LCP"] == 2500
    assert overview["vitals"]["pages"][0]["CLS"]["ok"] is True
