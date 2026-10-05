"""Synthetic reviewed metadata for tests only; never a release approval."""

from test_competitive_sets import mixed_pack

from socrat.skillpacks.schema import SkillPack


def lesson_pack():
    payload = mixed_pack().model_dump()
    payload["session_content_version"] = "1.0.0"
    payload["competitive_penalty"] = dict(
        wrong_submit_seconds=60,
        calibration="reviewed",
        review_reference="Synthetic policy only, not an approved penalty",
    )
    for overlay in payload["tracks"]:
        for language in payload["languages"]:
            for concept in overlay["concept_ids"]:
                key = f"{overlay['id']}_{language}_{concept}"
                payload["learning_lessons"].append(
                    dict(
                        id=key,
                        track=overlay["id"],
                        language=language,
                        concept_ids=[concept],
                        title=f"Synthetic {key}",
                        instruction=f"Synthetic {overlay['id']} instruction for {concept}.",
                        examples=[f"Synthetic {language} trace: 1 + 2 = 3."],
                        language_notes=f"Synthetic {language} semantics note.",
                        pattern_recognition="Synthetic pattern recognition.",
                        correctness="Synthetic loop invariant.",
                        complexity="Synthetic O(n) analysis.",
                        retrieval_check=dict(
                            id="retrieve",
                            prompt="Which value is 1 + 2?",
                            response=dict(
                                kind="choice",
                                answer="three",
                                choices=[
                                    dict(id="three", label="3"),
                                    dict(id="four", label="4"),
                                ],
                            ),
                        ),
                        exit_check=dict(
                            id="exit",
                            prompt="Trace 2 + 2. Use exactly one digit.",
                            response=dict(kind="trace", answer="4"),
                        ),
                        calibration="reviewed",
                        accessibility="Keyboard and plain text",
                        source_reference="Synthetic test fixture, not a human review",
                    )
                )
    payload["structural_repairs"] = [
        dict(
            exercise_id=source,
            variant_id=target,
            structural_change="Synthetic mapping only",
            review_reference="Synthetic tests only",
            calibration="reviewed",
        )
        for source, target in (
            ("a_runtime_probe", "c_root_repair"),
            ("b_second_topic", "d_second_repair"),
        )
    ]
    return SkillPack.model_validate(payload)
