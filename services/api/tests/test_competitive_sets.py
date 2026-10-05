"""Synthetic mixed inventory: no content review or live sandbox acceptance claim."""

from datetime import date

import pytest
from m6_support import code_pack
from sqlalchemy.orm import Session
from test_execution import claim, queue, result
from test_foundation import platform as platform
from test_learner_state import fact
from test_learning_sessions import act
from test_timed_learning import independent, prepared, tick

from socrat.learnerstate.service import append_fact, facts_for
from socrat.models import CodeAttempt, CurriculumRevision, LearnerGoal, identifier
from socrat.planning.engine import build_plan
from socrat.skillpacks.schema import SkillPack


def mixed_pack():
    payload = code_pack().model_dump()
    base = next(x for x in payload["exercises"] if x["id"] == "a_runtime_probe")
    base["estimated_minutes"] = 3
    roots = code_pack().topological_order()
    for track in payload["tracks"]:
        if track["id"] == "competitive":
            track["maximum_daily_minutes"] = 90
    for concept in payload["concepts"]:
        if "implement" not in concept["evidence_modes"]:
            concept["evidence_modes"].append("implement")
    for key, concept, minutes in (
        ("b_second_topic", roots[1], 3),
        ("c_root_repair", roots[0], 3),
        ("d_second_repair", roots[1], 3),
    ):
        payload["exercises"].append(
            {
                **base,
                "id": key,
                "title": key,
                "concept_ids": [concept],
                "family_id": key,
                "estimated_minutes": minutes,
                "statement": "Synthetic repair task: " + key,
                "variants": [
                    {**v, "starter_code": v["starter_code"] + "\n"} for v in base["variants"]
                ],
            }
        )
    return SkillPack.model_validate(payload)


def planned(pack, **changes):
    return build_plan(
        **{
            "pack": pack,
            "track": "competitive",
            "language": "python",
            "states": {
                key: dict(effective_mastery=0.78, confidence=0.9, independent_successes=3)
                for key in pack.topological_order()
            },
            "today": date(2026, 10, 5),
            "as_of": 1791158400,
            "weekdays": list(range(7)),
            "minutes": 60,
            "target_date": "no_fixed_date",
            "history": [],
            "exposures": {},
            "code_execution": True,
            "session_policy": "1.0.0",
            **changes,
        }
    )


def test_versioned_mixed_sets_budget_diversity_and_historical_replay():
    pack = mixed_pack()
    legacy = planned(pack, session_policy=None)
    actual = planned(pack)
    assert actual == planned(pack)
    assert len([x for x in legacy["days"][0]["blocks"] if x["mode"] == "independent"]) == 1
    blocks = actual["days"][0]["blocks"]
    tasks = [x for x in blocks if x["mode"] == "independent"]
    assert len(tasks) == 2 and tasks[0]["concept_ids"] != tasks[1]["concept_ids"]
    assert all(x["repair_exercise_id"] for x in tasks)
    for day in actual["days"]:
        assert sum(x["minutes"] + x.get("upsolve_minutes", 0) for x in day["blocks"]) <= 48
    short = planned(pack, minutes=30)["days"][0]["blocks"]
    assert len([x for x in short if x["mode"] == "independent"]) == 1
    # A second concept cannot receive a timer before its readiness is verified.
    root = pack.topological_order()[0]
    unready = planned(
        pack, states={root: dict(effective_mastery=0.78, confidence=0.9, independent_successes=3)}
    )
    assert all(x["concept_ids"] == [root] for x in unready["days"][0]["blocks"] if x["timed"])
    with pytest.raises(ValueError, match="unsupported"):
        planned(pack, session_policy="unknown")


@pytest.mark.parametrize("minutes", [20, 25, 30, 45, 59, 60, 90])
def test_optional_repairs_stay_within_budget_and_obey_inventory_filters(minutes):
    pack = mixed_pack()
    payload = pack.model_dump()
    for exercise in payload["exercises"]:
        if exercise["id"] == "c_root_repair":
            exercise["calibration"] = "uncalibrated"
    pack = SkillPack.model_validate(payload)
    actual = planned(pack, minutes=minutes, exposures={"d_second_repair": dict(count=3)})
    items = {x.id: x for x in pack.exercises}
    for day in actual["days"]:
        assert sum(x["minutes"] + x.get("upsolve_minutes", 0) for x in day["blocks"]) <= int(
            day["capacity_minutes"] * 0.8
        )
        for block in day["blocks"]:
            if repair := block.get("repair_exercise_id"):
                assert repair not in {"c_root_repair", "d_second_repair"}
                assert items[repair].estimated_minutes <= block["upsolve_minutes"]
                assert items[repair].family_id != items[block["exercise_ids"][0]].family_id


@pytest.mark.parametrize("language", ["python", "cpp", "java"])
def test_mixed_session_repairs_are_pinned_owned_seen_and_independently_admitted(
    platform, monkeypatch, language
):
    monkeypatch.setattr("m6_support.code_pack", mixed_pack)
    app, client, headers, worker, goal, session, clock = prepared(
        platform, monkeypatch, language, minutes=60, ready_all=True
    )
    tasks = [x for x in session["blocks"] if x["mode"] == "independent"]
    assert len(tasks) == 2 and tasks[0]["attempt_id"] != tasks[1]["attempt_id"]
    assert session["planned_minutes"] <= 48 and session["upsolve_reserved_minutes"] > 0
    session = independent(client, headers, session)
    # The older daily-plan completion rule also requires explanation evidence.
    # Seed that separately so one solved member cannot complete a two-task day.
    with Session(app.state.engine) as db, db.begin():
        owner = db.get(LearnerGoal, goal["id"])
        plan = client.get(f"/api/v1/goals/{goal['id']}/curriculum").json()
        sequence = len(facts_for(db, owner.user_id)) + 1
        append_fact(
            db,
            owner.user_id,
            fact(
                index=sequence,
                sequence=sequence,
                event_id=identifier(),
                source_id=identifier(),
                user_id=owner.user_id,
                goal_id=goal["id"],
                pack_id=plan["pack_id"],
                pack_digest=plan["pack_digest"],
                concept_ids=sorted({key for task in tasks for key in task["concept_ids"]}),
                track="competitive",
                language=language,
                family_id="synthetic_explanation",
                evidence_type="explain",
                occurred_at=clock[0],
            ),
        )
    for index in range(2):
        task = tasks[index]
        parent = client.get(f"/api/v1/attempts/{task['attempt_id']}").json()
        # Editing a draft is allowed while execution of a later block is locked.
        if index == 0:
            later = client.get(f"/api/v1/attempts/{tasks[1]['attempt_id']}").json()
            assert queue(client, headers, later).json()["error"]["code"] == "session_block_locked"
        session = act(client, headers, session, "start_timed", key=f"timer-{index}").json()
        block = next(x for x in session["blocks"] if x["status"] == "available")
        tick(client, worker, clock, block["deadline_at"])
        response = act(
            client,
            headers,
            session,
            "upsolve",
            key=f"repair-{index}",
            error_classification="concept_gap",
        )
        assert response.status_code == 200, response.text
        repaired = response.json()
        assert (
            act(
                client,
                headers,
                session,
                "upsolve",
                key=f"repair-{index}",
                error_classification="concept_gap",
            ).json()
            == repaired
        )
        block = next(x for x in repaired["blocks"] if x["status"] == "available")
        assert block["exercise_ids"] == [task["repair_exercise_id"]]
        assert block["repair_selection"] == "concept_matched_variant"
        assert block["minutes"] == task["upsolve_minutes"]
        repair = client.get(f"/api/v1/attempts/{block['attempt_id']}").json()
        expected = next(x for x in mixed_pack().exercises if x.id == block["exercise_ids"][0])
        assert repair["source"] == next(
            v.starter_code for v in expected.variants if v.language == language
        )
        assert client.get(f"/api/v1/attempts/{parent['id']}").json()["source"] == parent["source"]
        assert queue(client, headers, parent, key=f"old-{index}").status_code == 409
        submit = queue(client, headers, repair, key=f"submit-repair-{index}")
        assert submit.status_code == 200, submit.text
        job = claim(client, worker)
        assert (
            client.post(
                "/api/v1/execution/worker/result", headers=worker, json=result(job)
            ).status_code
            == 200
        )
        session = act(
            client, headers, repaired, key=f"advance-{index}", run_id=job.manifest.job_id
        ).json()
        assert session["status"] == "in_progress", session
        daily = client.get(
            f"/api/v1/daily-plan?goal_id={goal['id']}&date={session['local_date']}"
        ).json()
        assert daily["status"] == ("completed" if index == 1 else "in_progress"), daily
        with Session(app.state.engine) as db:
            assert db.get(CodeAttempt, repair["id"]).snapshot["unseen"] is False
    assert next(x for x in session["blocks"] if x["status"] == "available")["mode"] == "exit_check"
    assert (
        act(client, headers, session, answer="review", reflection="concept_gap").json()["status"]
        == "completed"
    )
    with Session(app.state.engine) as db:
        revision = db.get(
            CurriculumRevision, client.get(f"/api/v1/goals/{goal['id']}/curriculum").json()["id"]
        )
        inputs = dict(revision.snapshot["replay_inputs"])
        inputs["today"] = date.fromisoformat(inputs["today"])
        replayed = build_plan(mixed_pack(), **inputs)
        assert all(revision.snapshot[key] == value for key, value in replayed.items())
