"""Synthetic diagnostics only; never publication evidence."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_onboarding import goal, prepare

from socrat.models import SkillPackHead, SkillPackVersion, User
from socrat.skillpacks.schema import SkillPack


def diagnostic_pack(domain="dsa"):
    name = "dsa-1.0.0" if domain == "dsa" else "clear-writing-1.0.0"
    payload = json.loads(
        Path(f"contracts/fixtures/skill-packs/{name}.json").read_text(encoding="utf-8")
    )
    payload["version"] = "2.0.0"
    payload["change_log"] = "Synthetic M4 contract fixtures; no real learner release."
    payload["blueprints"] = []
    payload["diagnostics"] = []
    payload["misconception_taxonomy"] = []
    if domain != "dsa":
        # Preserve domain neutrality while using the currently supported goal family.
        payload["goals"][0]["id"] = "foundations"
        payload["goals"][0]["track_id"] = "foundations"
        payload["tracks"][0]["id"] = "foundations"
        payload["tracks"][0]["goals"] = ["foundations"]
    payload["exercises"] = [
        item for item in payload["exercises"] if item["inventory"] == "practice"
    ]
    for concept in payload["concepts"]:
        concept["evidence_modes"] = sorted(set(concept["evidence_modes"]) | {"recognize", "trace"})
        payload["misconception_taxonomy"].append(
            dict(
                id=f"{concept['id']}_boundary",
                concept_id=concept["id"],
                description="Synthetic observable boundary confusion",
                repair_concept_id=concept["id"],
            )
        )
    for track in payload["tracks"]:
        items = []
        for concept in track["concept_ids"]:
            for index in range(4):
                key = f"{track['id']}_{concept}_{index}"
                payload["exercises"].append(
                    dict(
                        id=key,
                        title=f"{concept.replace('_', ' ')} check {index + 1}",
                        concept_ids=[concept],
                        inventory="assessment",
                        modality="text",
                        evidence_mode="trace" if index % 2 else "recognize",
                        statement="Synthetic trace: start at 0 and add 2. What value remains?",
                        rubric="Exact result of the synthetic trace",
                        difficulty=1,
                        calibration="reviewed",
                        estimated_minutes=1,
                        family_id=key,
                        provenance=payload["provenance"],
                        accessibility="Plain text and keyboard accessible",
                    )
                )
                items.append(
                    dict(
                        exercise_id=key,
                        stage="no_code_trace_and_reasoning"
                        if index % 2 == 0
                        else "dsa_trace_and_reasoning",
                        languages=payload["languages"],
                        response=dict(
                            kind="choice",
                            choices=[dict(id="two", label="2"), dict(id="three", label="3")],
                            answer="two",
                            misconception_answers={"three": f"{concept}_boundary"},
                        ),
                    )
                )
        blueprint = f"{track['id']}_diagnostic"
        payload["blueprints"].append(
            dict(
                id=blueprint,
                kind="diagnostic",
                exercise_ids=[item["exercise_id"] for item in items],
                concept_ids=track["concept_ids"],
                scoring="deterministic",
            )
        )
        payload["diagnostics"].append(
            dict(
                blueprint_id=blueprint,
                track=track["id"],
                languages=payload["languages"],
                scope="objective_readiness",
                minimum_per_concept=2,
                maximum_items=len(items),
                maximum_seconds=900 if track["id"] == "foundations" else 2700,
                uncertainty_margin=0.01,
                items=items,
            )
        )
    return SkillPack.model_validate(payload)


def accepted(platform, track="foundations", language="python", experience="none"):
    app, client, headers = prepare(platform)
    app.state.settings.diagnostics_enabled = True
    content = diagnostic_pack()
    payload = content.model_dump()
    payload["purpose"] = "launch"  # Only inside isolated synthetic tests.
    for template in payload["goals"]:
        value = goal(template["id"])
        template["released_targets"] = [
            dict(
                outcome=value.target_outcome,
                value=value.target_value,
                role_level=value.role_level,
                platform_or_format=value.platform_or_format,
            )
        ]
    content = SkillPack.model_validate(payload)
    with Session(app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.subject == "alice"))
        record = SkillPackVersion(
            pack_key=content.key,
            version=content.version,
            domain=content.domain,
            payload=json.loads(content.canonical_json()),
            digest=content.digest(),
            status="released",
            author_id=user.id,
        )
        db.add(record)
        db.flush()
        db.add(SkillPackHead(pack_key=content.key, active_id=record.id))
    value = goal(track, language=language, language_experience=experience).model_dump()
    preview = client.post("/api/v1/onboarding/preview", json=value, headers=headers).json()
    saved = client.post(
        "/api/v1/onboarding/confirm",
        headers=headers,
        json=dict(
            goal=value,
            review_digest=preview["review_digest"],
            reviewed=True,
            idempotency_key="m4-goal",
        ),
    ).json()
    return app, client, headers, saved


def submit(client, headers, session, answer="two", **changes):
    body = dict(
        attempt_id=session["item"]["attempt_id"],
        revision=session["revision"],
        idempotency_key=session["item"]["attempt_id"],
        answer=answer,
        **changes,
    )
    return client.post(f"/api/v1/diagnostics/{session['id']}/responses", headers=headers, json=body)
