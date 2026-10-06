"""Offline planner rehearsals: no learners, execution, or editorial mutations."""

from datetime import date
from typing import cast

from socrat.learning.content import coverage_audit, lesson_for
from socrat.planning.engine import build_plan
from socrat.planning.policy import POLICY, POLICY_DIGEST
from socrat.planning.sessions import SESSION_POLICY, SESSION_POLICY_DIGEST
from socrat.skillpacks.schema import SkillPack

AUDIT_DATE = date(2026, 10, 5)  # Monday; never depend on the machine's calendar.
AUDIT_STAMP = 1791158400


def planning_audit(pack: SkillPack) -> dict:
    """Rehearse bounded, versioned scenarios, not all possible learner histories.

    Runtime availability is assumed from declared variants, never attested here.
    Readiness remains fixed across the horizon, matching the production planner.
    Only safe identifiers and reason codes leave this function.
    """
    inventory = coverage_audit(pack)
    cells = []
    for cell in inventory["cells"]:
        track, language = cell["track"], cell["language"]
        overlay = next((x for x in pack.tracks if x.id == track), None)
        scenarios = []
        if overlay is not None and language in pack.languages:
            readiness = max([0.78, *(edge.minimum_mastery for edge in pack.edges)])
            proven = {
                key: dict(
                    effective_mastery=readiness,
                    confidence=0.9,
                    independent_successes=3,
                    missing_gates=["unverified_mastery"],
                )
                for key in pack.topological_order()
            }
            due = {key: dict(**state, due_at=AUDIT_STAMP) for key, state in proven.items()}
            closure = set(overlay.concept_ids)
            while True:
                expanded = closure | {x.prerequisite for x in pack.edges if x.concept in closure}
                if expanded == closure:
                    break
                closure = expanded
            families = sorted(
                {
                    x.family_id
                    for x in pack.exercises
                    if x.inventory == "practice"
                    and x.calibration == "reviewed"
                    and set(x.concept_ids) <= closure
                    and pack.variant_for(x.id, language) is not None
                }
            )
            exhausted = {
                x.id: dict(count=POLICY.maximum_exposures)
                for x in pack.exercises
                if families and x.family_id == families[0]
            }
            runtimes = sorted(
                {
                    v.runtime_ref
                    for x in pack.exercises
                    for v in x.variants
                    if v.language == language
                }
            )
            profiles: tuple[tuple[str, dict, dict, int], ...] = (
                ("beginner", {}, {}, 1),
                ("ready", proven, {}, 1),
                ("review_due", due, {}, 1),
                ("one_family_exhausted", proven, exhausted, 1),
                ("second_band", proven, {}, 2),
            )
            budgets = sorted(
                {20, min(60, overlay.maximum_daily_minutes), min(90, overlay.maximum_daily_minutes)}
            )
            for profile, states, exposures, band in profiles:
                for weekdays in ([0, 2, 4], [0, 1, 2, 3, 4, 5]):
                    for minutes in budgets:
                        plan = build_plan(
                            pack=pack,
                            track=track,
                            language=language,
                            states=states,
                            today=AUDIT_DATE,
                            as_of=AUDIT_STAMP,
                            weekdays=weekdays,
                            minutes=minutes,
                            target_date="no_fixed_date",
                            history=[],
                            exposures=exposures,
                            previous=dict(difficulty=band),
                            code_execution=True,
                            runtime_refs=runtimes,
                            session_policy=cast(str, SESSION_POLICY["version"]),
                        )
                        gaps = []
                        for day in plan["days"]:
                            if day["status"] == "rest":
                                continue
                            if day["status"] == "content_gap":
                                rejected = sorted(
                                    {
                                        reason
                                        for decision in plan["decisions"]
                                        if decision["date"] == day["date"]
                                        for reason in decision["rejected_by"]
                                    }
                                )
                                gaps.append(
                                    dict(
                                        code="planner_content_gap",
                                        date=day["date"],
                                        rejection_codes=rejected,
                                    )
                                )
                                continue
                            independent = [x for x in day["blocks"] if x["mode"] == "independent"]
                            if (
                                track == "competitive"
                                and profile != "beginner"
                                and day["capacity_minutes"]
                                >= cast(int, SESSION_POLICY["mixed_minimum_capacity"])
                                and len(independent) < cast(int, SESSION_POLICY["maximum_problems"])
                            ):
                                gaps.append(dict(code="mixed_set_unavailable", date=day["date"]))
                            for block in day["blocks"]:
                                if block["mode"] == "independent":
                                    if block["modality"] != "code":
                                        gaps.append(
                                            dict(code="unverified_text_practice", date=day["date"])
                                        )
                                    continue
                                for concept in block["concept_ids"]:
                                    if not lesson_for(
                                        pack, track, language, [concept], block["concept_ids"]
                                    ):
                                        gap = dict(
                                            code="selected_lesson_unavailable",
                                            date=day["date"],
                                            concept_id=concept,
                                        )
                                        if gap not in gaps:
                                            gaps.append(gap)
                        scenarios.append(
                            dict(
                                profile=profile,
                                difficulty=band,
                                weekdays=weekdays,
                                minutes=minutes,
                                effective_minutes=plan["controller"]["workload_minutes"],
                                exhausted_family_id=families[0]
                                if families and profile == "one_family_exhausted"
                                else None,
                                scheduled_days=sum(x["status"] != "rest" for x in plan["days"]),
                                ready=not gaps,
                                gaps=gaps,
                            )
                        )
        cells.append(
            dict(
                track=track,
                language=language,
                ready=cell["ready"] and bool(scenarios) and all(x["ready"] for x in scenarios),
                inventory_gaps=cell["gaps"],
                scenarios=scenarios,
            )
        )
    return dict(
        version="m7_planning_audit_1.0.0",
        pack_digest=pack.digest(),
        planner_policy_digest=POLICY_DIGEST,
        session_policy_digest=SESSION_POLICY_DIGEST,
        start_date=AUDIT_DATE.isoformat(),
        horizon_days=POLICY.horizon_days,
        runtime_availability="assumed_declared_variants",
        scope="bounded_offline_scenarios",
        ready=all(x["ready"] for x in cells),
        cells=cells,
    )
