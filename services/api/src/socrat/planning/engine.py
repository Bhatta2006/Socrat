"""Pure, replayable planner. Future days never assume future mastery gains."""

import math
from datetime import date, timedelta

from socrat.planning.policy import POLICY, TRACKS
from socrat.planning.sessions import SESSION_POLICY, competitive_blocks
from socrat.skillpacks.schema import SkillPack


def ready(state: dict, threshold: float = POLICY.readiness) -> bool:
    return (
        state.get("effective_mastery", 0) >= threshold
        and state.get("confidence", 0) >= POLICY.minimum_confidence
        and state.get("independent_successes", 0) >= 2
    )


def adapt(history: list[dict], previous: dict, today: date, track: str) -> dict:
    """One-band bounded changes with an evidence watermark and dwell time."""
    valid = [
        x
        for x in history
        if x.get("valid")
        and x.get("finalized")
        and x.get("mode") in {"practice", "assessment", "retention"}
    ]
    independent = [x for x in valid if x.get("hint_level", 0) == 0 and x.get("mode") != "passive"]
    band = previous.get("difficulty", 1)
    reasons = []
    watermark = max((x.get("sequence", 0) for x in valid), default=0)
    changed = previous.get("changed_on", today.isoformat())
    fresh = [x for x in independent if x.get("sequence", 0) > previous.get("watermark", 0)]
    can_change = (today - date.fromisoformat(changed)).days >= POLICY.difficulty_hold_days
    if can_change and len(fresh) >= 2:
        last = fresh[-3:]
        diverse = len({x.get("family_id") for x in last}) >= 2
        at_band = all(x.get("difficulty", 1) == band for x in last)
        if at_band and diverse and all(x["score"] >= 0.85 for x in last):
            timed = all(x.get("elapsed_seconds", 0) <= x.get("expected_seconds", 60) for x in last)
            track_ready = (
                track == "foundations"
                or track == "interview"
                and all(x.get("unseen") for x in last)
                and any(x.get("evidence_type") == "explain" for x in last)
                and any(x.get("evidence_type") in {"implement", "transfer"} for x in last)
                or track == "competitive"
                and len(last) == 3
                and timed
                and len({key for x in last for key in x.get("concept_ids", [])}) >= 2
            )
            if track_ready:
                band = min(10, band + 1)
                reasons.append("diverse_clean_success_raise_one_band")
        elif all(x["score"] < 0.4 for x in last[-2:]):
            band = max(1, band - 1)
            reasons.append("repeated_failure_prerequisite_repair")
        if reasons:
            changed = today.isoformat()
    last_five = valid[-5:]
    dependence = len(last_five) == 5 and sum(x.get("hint_level", 0) >= 4 for x in last_five) > 2
    if dependence:
        reasons.append("independence_practice_lower_novelty")
    if any(
        x["score"] >= 0.7 and x.get("elapsed_seconds", 0) > 2 * x.get("expected_seconds", 60)
        for x in independent[-2:]
    ):
        reasons.append("strategy_review_keep_difficulty")
    misconceptions = [code for x in valid[-2:] for code in x.get("misconception_codes", [])]
    repair = sorted({code for code in misconceptions if misconceptions.count(code) >= 2})[:1]
    if repair:
        reasons.append("repeated_misconception_one_detour")
    return dict(
        difficulty=band,
        changed_on=changed,
        watermark=watermark
        if reasons
        and any("one_band" in reason or "repeated_failure" in reason for reason in reasons)
        else previous.get("watermark", 0),
        lower_novelty=dependence,
        repair_codes=repair,
        reason_codes=reasons,
    )


def build_plan(
    pack: SkillPack,
    track: str,
    language: str,
    states: dict[str, dict],
    today: date,
    as_of: int,
    weekdays: list[int],
    minutes: int,
    target_date: str,
    history: list[dict],
    exposures: dict[str, dict],
    previous: dict | None = None,
    missed_days: int = 0,
    code_execution: bool = False,
    runtime_refs: list[str] | None = None,
    session_policy: str | None = None,
) -> dict:
    if session_policy not in {None, SESSION_POLICY["version"]}:
        raise ValueError("unsupported session planning policy")
    overlay = next(x for x in pack.tracks if x.id == track)
    capacity = min(
        minutes, overlay.maximum_daily_minutes, (previous or {}).get("workload_minutes", minutes)
    )
    controller = adapt(history, previous or {}, today, track)
    if controller["difficulty"] > (previous or {}).get("difficulty", 1):
        latest = [
            x
            for x in history
            if x.get("valid")
            and x.get("finalized")
            and x.get("mode") in {"practice", "assessment", "retention"}
            and x.get("hint_level", 0) == 0
        ][-3:]
        if any(
            states.get(key, {}).get("confidence", 0) < POLICY.minimum_confidence
            for x in latest
            for key in x.get("concept_ids", [])
        ):
            controller.update(
                difficulty=(previous or {}).get("difficulty", 1),
                changed_on=(previous or {}).get("changed_on", today.isoformat()),
                watermark=(previous or {}).get("watermark", 0),
                reason_codes=["difficulty_held_for_confidence"],
            )
    reasons = list(controller["reason_codes"])
    if missed_days >= 2:
        reasons.append("missed_days_recalculate_without_backlog")
    if missed_days >= 3:
        capacity = max(20, capacity * 3 // 4)
        reasons.append("repeated_misses_reduce_workload")
    capacity = min(capacity, minutes, overlay.maximum_daily_minutes)
    controller["workload_minutes"] = capacity
    targets = set(overlay.concept_ids)
    closure = set(targets)
    while True:
        enlarged = closure | {e.prerequisite for e in pack.edges if e.concept in closure}
        if enlarged == closure:
            break
        closure = enlarged
    nodes = []
    eligible = set()
    for key in pack.topological_order():
        if key not in closure:
            continue
        state = states.get(key, {})
        blocked = [
            e.prerequisite
            for e in pack.edges
            if e.concept == key
            and not ready(states.get(e.prerequisite, {}), max(POLICY.readiness, e.minimum_mastery))
        ]
        proven = ready(state, POLICY.mastery) and not state.get("missing_gates", ["unknown"])
        due = state.get("due_at") is not None and state["due_at"] <= as_of
        need = (
            (1 - state.get("effective_mastery", 0))
            * (1 + len([e for e in pack.edges if e.prerequisite == key]))
            * (2 - state.get("confidence", 0))
        )
        nodes.append(
            dict(
                concept_id=key,
                prerequisites=[e.prerequisite for e in pack.edges if e.concept == key],
                state="blocked"
                if blocked
                else "retained"
                if proven and not due
                else "review_due"
                if due
                else "ready",
                blocked_by=blocked,
                need=round(need, 6),
                reason_codes=[
                    "prerequisite_not_ready"
                    if blocked
                    else "retention_due"
                    if due
                    else "sufficient_mastery"
                    if proven
                    else "verified_frontier"
                ],
            )
        )
        if not blocked:
            eligible.add(key)
    node_map = {x["concept_id"]: x for x in nodes}
    concept_map = {x.id: x for x in pack.concepts}
    required = sum(
        concept_map[x["concept_id"]].estimated_minutes for x in nodes if x["state"] != "retained"
    )
    # Explicit weekdays are anchored in the learner's timezone, never the server timezone.
    weekly = capacity * len(weekdays)
    usable = weekly * (1 - POLICY.weekly_reserve)
    weeks = max(1, math.ceil(required / usable)) if usable else 0
    feasible_date = today + timedelta(days=weeks * 7)
    if target_date == "no_fixed_date":
        available = None
        feasibility = "on_track"
    else:
        deadline = date.fromisoformat(target_date)
        days = max(0, (deadline - today).days + 1)
        count = sum((today + timedelta(days=i)).weekday() in weekdays for i in range(days))
        available = int(count * capacity * (1 - POLICY.weekly_reserve))
        feasibility = (
            "date_unfeasible"
            if required > available
            else "at_risk"
            if required > available * 0.85
            else "on_track"
        )
    # Weekly assessment is a reservation only: M9 owns sequestered item selection.
    decisions = []
    days_out = []
    seen = {key: dict(value) for key, value in exposures.items()}
    for offset in range(POLICY.horizon_days):
        day = today + timedelta(days=offset)
        if day.weekday() not in weekdays:
            days_out.append(
                dict(
                    date=day.isoformat(),
                    status="rest",
                    capacity_minutes=0,
                    blocks=[],
                    deferred_reviews=[],
                )
            )
            continue
        candidates = []
        for item in pack.exercises:
            rejection = []
            if item.inventory != "practice":
                rejection.append("protected_inventory")
            if item.calibration != "reviewed":
                rejection.append("uncalibrated_content")
            if not set(item.concept_ids) <= eligible:
                rejection.append("prerequisite_not_ready")
            if item.modality == "code" and (
                not code_execution or language not in {v.language for v in item.variants}
            ):
                rejection.append("runtime_unavailable")
            if (
                item.modality == "code"
                and runtime_refs is not None
                and not any(
                    v.language == language and v.runtime_ref in runtime_refs for v in item.variants
                )
            ):
                rejection.append("runtime_unavailable")
            if item.estimated_minutes > capacity // 2:
                rejection.append("time_budget")
            if item.difficulty > controller["difficulty"]:
                rejection.append("difficulty_limit")
            exposure = seen.get(item.id, {})
            last = exposure.get("last_date")
            if exposure.get("count", 0) >= POLICY.maximum_exposures:
                rejection.append("exposure_limit")
            if last and (day - date.fromisoformat(last)).days < POLICY.cooldown_days:
                rejection.append("cooldown")
            if any(node_map.get(key, {}).get("state") == "retained" for key in item.concept_ids):
                rejection.append("redundant_practice")
            due = any(
                node_map.get(key, {}).get("state") == "review_due" for key in item.concept_ids
            )
            repair_concepts = {
                x.repair_concept_id
                for x in pack.misconception_taxonomy
                if x.id in controller["repair_codes"]
            }
            scores = dict(
                need=sum(node_map.get(key, {}).get("need", 0) for key in item.concept_ids),
                due_review=3 * TRACKS[track]["new_review"][1] / 40 if due else 0,
                goal_relevance=1,
                misconception_match=2 if repair_concepts & set(item.concept_ids) else 0,
                diversity=1 / (1 + exposure.get("count", 0)),
                difficulty_fit=1 / (1 + abs(controller["difficulty"] - item.difficulty)),
                recent_exposure=-exposure.get("count", 0),
                duration_mismatch=-abs(capacity * 0.4 - item.estimated_minutes) / capacity,
                abandonment_risk=-1
                if controller["lower_novelty"]
                and any(not ready(states.get(key, {})) for key in item.concept_ids)
                else 0,
            )
            score = round(sum(scores.values()), 6)
            decisions.append(
                dict(
                    date=day.isoformat(),
                    exercise_id=item.id,
                    rejected_by=rejection,
                    score=score,
                    components=scores,
                )
            )
            if not rejection:
                candidates.append((item, score, exposure, due))
        candidates.sort(
            key=lambda x: (-x[1], x[2].get("count", 0), x[2].get("last_date", ""), x[0].id)
        )
        # Aging exposure penalties plus cooldown ensure equal eligible inventory rotates.
        blocks: list[dict] = []
        deferred = sorted(key for key in eligible if node_map[key]["state"] == "review_due")
        if candidates:
            item, score, exposure, due = candidates[0]
            duration = item.estimated_minutes
            review_cap = int(capacity * POLICY.review_fraction)
            work_capacity = int(capacity * (1 - POLICY.weekly_reserve))
            retrieval = max(1, int(work_capacity * 0.075))
            instruction = max(1, int(work_capacity * 0.15))
            guided = max(1, int(work_capacity * 0.30))
            exit_minutes = max(1, int(work_capacity * 0.075))
            if due:
                retrieval = min(review_cap, retrieval)
                deferred = [x for x in deferred if x not in item.concept_ids]
            independent = max(duration, int(work_capacity * 0.40))
            concept = item.concept_ids[0]
            for mode, time, refs in (
                ("retrieval", retrieval, []),
                ("instruction", instruction, []),
                ("guided", guided, []),
                ("independent", independent, [item.id]),
                ("exit_check", exit_minutes, []),
            ):
                blocks.append(
                    dict(
                        mode=mode,
                        minutes=time,
                        concept_ids=item.concept_ids,
                        exercise_ids=refs,
                        title=item.title if refs else concept_map[concept].title,
                        modality=item.modality if refs else "text",
                        timed=track == "competitive"
                        and ready(states.get(concept, {}))
                        and mode == "independent",
                        reason_codes=["ranked_eligible_practice" if refs else "session_anatomy"],
                    )
                )
            # Integer rounding can never produce debt or a budget overrun.
            while sum(x["minutes"] for x in blocks) > work_capacity:
                block = max(
                    (x for x in blocks if x["mode"] != "independent"), key=lambda x: x["minutes"]
                )
                block["minutes"] -= 1
            if session_policy and track == "competitive":
                blocks = (
                    competitive_blocks(
                        candidates, states, capacity, work_capacity, concept_map, ready
                    )
                    or blocks
                )
            if session_policy and track == "competitive":
                for block in blocks:
                    if block["timed"]:
                        block["timed"] = all(
                            ready(states.get(key, {})) for key in block["concept_ids"]
                        )
            issued = {
                key
                for block in blocks
                for key in [*block["exercise_ids"], block.get("repair_exercise_id")]
                if key is not None
            }
            # Reserve variants conservatively: all items in an issued family age together.
            families = {x.family_id for x in pack.exercises if x.id in issued}
            for selected_item in pack.exercises:
                if selected_item.id in issued or (
                    session_policy and selected_item.family_id in families
                ):
                    seen[selected_item.id] = dict(
                        count=seen.get(selected_item.id, {}).get("count", 0) + 1,
                        last_date=day.isoformat(),
                    )
        days_out.append(
            dict(
                date=day.isoformat(),
                status="draft" if blocks else "content_gap",
                capacity_minutes=capacity,
                reserved_minutes=capacity - int(capacity * (1 - POLICY.weekly_reserve)),
                blocks=blocks,
                deferred_reviews=deferred,
                reason_codes=["current_readiness_only"]
                + ([] if blocks else ["no_safe_independent_candidate"]),
            )
        )
    milestone_minutes = 0
    milestones = []
    for node in nodes:
        if node["state"] != "retained":
            milestone_minutes += concept_map[node["concept_id"]].estimated_minutes
        milestones.append(
            dict(
                concept_id=node["concept_id"],
                estimated_date=(
                    today
                    + timedelta(days=math.ceil(milestone_minutes / usable) * 7 if usable else 0)
                ).isoformat(),
                conditional=True,
            )
        )
    return dict(
        nodes=nodes,
        days=days_out,
        decisions=decisions,
        controller=controller,
        track_policy=TRACKS[track],
        feasibility=feasibility,
        required_minutes=required,
        available_minutes=available,
        feasible_target_date=feasible_date.isoformat(),
        weekly_reserve_minutes=math.ceil(weekly * POLICY.weekly_reserve),
        assessment_reservation_minutes=math.ceil(weekly * 0.1),
        milestones=milestones,
        reason_codes=reasons,
        alternatives=["extend_target_date", "reduce_target_scope"]
        if feasibility == "date_unfeasible"
        else [],
        provisional=any(not ready(states.get(key, {})) for key in closure),
    )
