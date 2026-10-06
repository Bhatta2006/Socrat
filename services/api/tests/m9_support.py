"""Synthetic parallel forms; never real launch content or human review evidence."""

import copy

from m4_support import accepted, diagnostic_pack
from m6_support import code_pack

from socrat.skillpacks.schema import SkillPack


def assessment_pack(qualitative=False, code=False, code_boundary=False):
    payload = (code_pack() if code else diagnostic_pack()).model_dump()
    root = SkillPack.model_validate(payload).topological_order()[0]
    other = SkillPack.model_validate(payload).topological_order()[1]
    probe = next((x for x in payload["exercises"] if x["id"] == "a_runtime_probe"), None)
    payload["assessment_forms"] = []
    payload["version"] = "9.0.0"
    for track in payload["tracks"]:
        for kind in ("baseline", "weekly", "final", "retention"):
            for variant in range(2):
                blueprint_id = f"m9_{track['id']}_{kind}_{variant}"
                specs = []
                for index in range(2):
                    key = f"{blueprint_id}_{index}"
                    concepts = [root, other] if kind == "weekly" and index == 1 else [root]
                    exercise = dict(
                        id=key,
                        title=f"Synthetic {kind} check {index}",
                        concept_ids=concepts,
                        inventory="assessment",
                        modality="text",
                        evidence_mode="trace",
                        statement="Synthetic trace: start with 1 and add 1. Explain the state.",
                        rubric="Trace the two steps",
                        difficulty=1,
                        calibration="reviewed",
                        estimated_minutes=1,
                        family_id=key,
                        provenance=payload["provenance"],
                        accessibility="Plain text, keyboard accessible",
                    )
                    spec = dict(
                        exercise_id=key,
                        response=dict(kind="trace", answer="PRIVATE-M9-KEY"),
                        unfamiliar_representation=index == 0,
                    )
                    if qualitative and index == 1:
                        exercise["evidence_mode"] = "explain"
                        for concept in payload["concepts"]:
                            concept["evidence_modes"] = sorted(
                                set(concept["evidence_modes"]) | {"explain"}
                            )
                        spec.update(
                            response=dict(kind="human_rubric"),
                            rubric_criteria=["correctness", "complexity"],
                        )
                    if code and index == 0:
                        exercise = {
                            **copy.deepcopy(probe),
                            **dict(
                                id=key, family_id=key, inventory="assessment", concept_ids=concepts
                            ),
                        }
                        spec["response"] = dict(kind="implementation")
                        if code_boundary:
                            exercise["tests"] += copy.deepcopy(exercise["tests"])
                    payload["exercises"].append(exercise)
                    specs.append(spec)
                payload["blueprints"].append(
                    dict(
                        id=blueprint_id,
                        kind=kind,
                        exercise_ids=[x["exercise_id"] for x in specs],
                        concept_ids=[root, other] if kind == "weekly" else [root],
                        scoring="human_rubric" if qualitative else "deterministic",
                    )
                )
                payload["assessment_forms"].append(
                    dict(
                        blueprint_id=blueprint_id,
                        track=track["id"],
                        languages=payload["languages"],
                        parallel_group=f"m9_{track['id']}_{'parallel' if kind in {'baseline', 'final'} else kind}",
                        maximum_seconds=900,
                        pass_score=0.7,
                        review_reference="synthetic-review-only",
                        retention_representation="recall" if kind == "retention" else None,
                        items=specs,
                    )
                )
    return SkillPack.model_validate(payload)


def prepared(platform, monkeypatch, track="foundations", language="python", **options):
    monkeypatch.setattr("m4_support.diagnostic_pack", lambda: assessment_pack(**options))
    app, client, headers, goal = accepted(platform, track, language)
    app.state.settings.assessments_enabled = True
    return app, client, headers, goal


def start(client, headers, goal, kind="baseline", key="m9-start"):
    response = client.post(
        f"/api/v1/goals/{goal['id']}/assessments",
        headers=headers,
        json=dict(kind=kind, idempotency_key=key),
    )
    assert response.status_code == 200, response.text
    return response.json()


def respond(client, headers, session, item=None, answer="PRIVATE-M9-KEY", **changes):
    item = item or next(x for x in session["items"] if x["status"] == "available")
    response = client.post(
        f"/api/v1/assessments/{session['id']}/responses",
        headers=headers,
        json=dict(
            item_id=item["id"],
            revision=session["revision"],
            idempotency_key=item["id"],
            answer=answer,
            **changes,
        ),
    )
    assert response.status_code == 200, response.text
    return response.json()


def finish(client, headers, session):
    response = client.post(f"/api/v1/assessments/{session['id']}/complete", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()
