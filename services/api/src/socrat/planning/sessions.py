"""Versioned M7 practice allocation; legacy M5 replay remains unchanged."""

from socrat.learnerstate.policy import digest

SESSION_POLICY = {
    "version": "1.0.0",
    "mixed_minimum_capacity": 60,
    "maximum_problems": 2,
    "upsolve_fraction": 0.20,
    "repair_categories": ["concept_gap", "wrong_answer", "complexity"],
}
SESSION_POLICY_DIGEST = digest(SESSION_POLICY)


def competitive_blocks(
    candidates, states, capacity, work_capacity, concepts, ready, structural_repairs=None
):
    """Only verified concepts receive timers. Repairs use reviewed safe inventory.

    Reserved repair time is optional, not a second timed deadline. A different
    family is a concept-matched practice task, not proof of structural novelty.
    """
    primary = candidates[0][0]
    if not all(ready(states.get(key, {})) for key in primary.concept_ids):
        return None
    eligible = [
        x[0] for x in candidates if all(ready(states.get(key, {})) for key in x[0].concept_ids)
    ]
    reserve = max(1, int(work_capacity * SESSION_POLICY["upsolve_fraction"]))
    anatomy = max(4, work_capacity // 6)
    practice = work_capacity - reserve - anatomy
    selected = [primary]
    if (
        capacity >= SESSION_POLICY["mixed_minimum_capacity"]
        and SESSION_POLICY["maximum_problems"] == 2
    ):
        diverse = [
            x
            for x in eligible
            if x.family_id != primary.family_id
            and set(x.concept_ids) != set(primary.concept_ids)
            and max(x.estimated_minutes, primary.estimated_minutes) <= practice // 2
        ]
        if diverse:
            selected.append(diverse[0])
    if any(x.estimated_minutes > practice // len(selected) for x in selected):
        return None
    concept_ids = sorted({key for item in selected for key in item.concept_ids})
    blocks = []
    for mode, minutes in (("retrieval", 1), ("instruction", 1), ("guided", anatomy - 3)):
        blocks.append(
            dict(
                mode=mode,
                minutes=minutes,
                concept_ids=concept_ids,
                exercise_ids=[],
                title=" / ".join(concepts[key].title for key in concept_ids),
                modality="text",
                timed=False,
                reason_codes=["competitive_concise_repair"],
            )
        )
    for index, item in enumerate(selected):
        repair_minutes = reserve // len(selected) + int(index < reserve % len(selected))
        repairs = [
            x
            for x in eligible
            if x.id not in {y.id for y in selected}
            and x.family_id not in {y.family_id for y in selected}
            and set(x.concept_ids) == set(item.concept_ids)
            and x.modality == item.modality
            and x.difficulty <= item.difficulty
            and x.estimated_minutes <= repair_minutes
            and (structural_repairs is None or (item.id, x.id) in structural_repairs)
        ]
        blocks.append(
            dict(
                mode="independent",
                minutes=practice // len(selected) + int(index < practice % len(selected)),
                upsolve_minutes=repair_minutes,
                repair_exercise_id=repairs[0].id if repairs else None,
                **(
                    {"repair_review": "reviewed_structural_variant"}
                    if repairs and structural_repairs is not None
                    else {}
                ),
                concept_ids=item.concept_ids,
                exercise_ids=[item.id],
                title=item.title,
                modality=item.modality,
                timed=True,
                reason_codes=[
                    "mixed_verified_practice" if len(selected) > 1 else "verified_timed_practice"
                ],
            )
        )
    blocks.append(
        dict(
            mode="exit_check",
            minutes=1,
            concept_ids=concept_ids,
            exercise_ids=[],
            title="Practice reflection",
            modality="text",
            timed=False,
            reason_codes=["session_anatomy"],
        )
    )
    return blocks
