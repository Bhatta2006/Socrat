"""Synthetic M5 inventory; never real launch content."""

from m4_support import diagnostic_pack

from socrat.skillpacks.schema import SkillPack


def planner_pack():
    payload = diagnostic_pack().model_dump()
    for concept in payload["concepts"]:
        for index in range(6):
            payload["exercises"].append(
                dict(
                    id=f"practice_{concept['id']}_{index}",
                    title=f"Independent {concept['title']} {index}",
                    concept_ids=[concept["id"]],
                    inventory="practice",
                    modality="text",
                    evidence_mode="trace",
                    statement="Trace the reviewed example independently.",
                    rubric="Explain the resulting value",
                    difficulty=1,
                    calibration="reviewed",
                    estimated_minutes=5,
                    family_id=f"practice_{concept['id']}_{index}",
                    provenance=payload["provenance"],
                    accessibility="Keyboard and plain text",
                )
            )
    return SkillPack.model_validate(payload)


def completed(platform, monkeypatch, track="foundations", language="python"):
    from m4_support import accepted, submit

    monkeypatch.setattr("m4_support.diagnostic_pack", planner_pack)
    app, client, headers, goal = accepted(platform, track, language, "professional")
    app.state.settings.planning_enabled = True
    session = client.post(f"/api/v1/goals/{goal['id']}/diagnostics", headers=headers).json()
    while session["item"]:
        response = submit(client, headers, session)
        assert response.status_code == 200, response.text
        session = response.json()
    assert (
        client.post(f"/api/v1/diagnostics/{session['id']}/complete", headers=headers).status_code
        == 200
    )
    return app, client, headers, goal
