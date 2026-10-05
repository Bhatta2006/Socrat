"""Pure replay. Delivery order is irrelevant; aggregate sequence is authoritative."""

import math
from statistics import median
from typing import Literal

from pydantic import Field, model_validator

from socrat.learnerstate.policy import POLICIES, LearningPolicy, canonical
from socrat.skillpacks.types import Contract, Key


class EvidenceFact(Contract):
    schema_version: Literal[1] = 1
    event_id: str = Field(min_length=1, max_length=36)
    user_id: str = Field(min_length=1, max_length=36)
    goal_id: str = Field(min_length=1, max_length=36)
    track: Literal["foundations", "interview", "competitive"]
    sequence: int = Field(ge=1)
    kind: Literal["scored", "invalidated"] = "scored"
    target_event_id: str | None = None
    source_id: str = Field(min_length=1, max_length=36)
    pack_id: str = Field(min_length=1, max_length=36)
    pack_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    language: str = Field(max_length=16)
    concept_ids: list[Key] = Field(min_length=1, max_length=100)
    mode: Literal["diagnostic", "practice", "assessment", "retention", "passive"]
    evidence_type: Literal[
        "recognize", "trace", "analyze", "explain", "implement", "transfer", "retain"
    ]
    family_id: Key
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    quality: float = Field(ge=0, le=1, allow_inf_nan=False)
    hint_level: int = Field(ge=0, le=5)
    elapsed_seconds: float = Field(default=0.0, ge=0, le=2700, allow_inf_nan=False)
    expected_seconds: float = Field(default=60.0, gt=0, le=10800, allow_inf_nan=False)
    difficulty: int = Field(default=1, ge=1, le=10)
    valid: bool
    unseen: bool
    finalized: bool
    occurred_at: int = Field(ge=0)
    scoring_version: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(min_length=1, max_length=64)
    policy_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason_code: Key
    misconception_codes: list[Key] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def valid_fact(self):
        if len(self.concept_ids) != len(set(self.concept_ids)):
            raise ValueError("Duplicate concept attribution")
        if (self.kind == "invalidated") != (self.target_event_id is not None):
            raise ValueError("Invalid correction reference")
        if self.mode in {"assessment", "retention"} and self.hint_level:
            raise ValueError("Independent protected mode cannot have hints")
        return self


def state_key(pack_id: str, language: str, concept: str) -> str:
    return f"{pack_id}:{language}:{concept}"


def band(mean: float) -> str:
    return "needs_foundation" if mean < 0.4 else "developing" if mean < 0.65 else "capable"


def empty_state(policy: LearningPolicy) -> dict:
    return {
        "alpha": policy.prior_alpha,
        "beta": policy.prior_beta,
        "mastery_mean": 0.5,
        "confidence": 0.0,
        "retention_factor": 1.0,
        "effective_mastery": 0.5,
        "band": "insufficient_evidence",
        "independent_count": 0,
        "independent_successes": 0,
        "assisted_count": 0,
        "independent_rate": None,
        "assisted_rate": None,
        "evidence_count": 0,
        "evidence_counts_by_type": {},
        "evidence_counts_by_difficulty": {},
        "maximum_hint_level": 0,
        "median_solve_seconds": None,
        "median_time_ratio": None,
        "families": [],
        "forms": [],
        "independent_forms": [],
        "assessment_passed": False,
        "retention_passed": False,
        "latest_independent_score": None,
        "last_evidence_at": None,
        "due_at": None,
        "misconceptions": {},
        "reason_codes": ["insufficient_evidence"],
        "model_version": policy.version,
    }


def ordered_facts(facts: list[EvidenceFact]) -> list[EvidenceFact]:
    unique: dict[str, EvidenceFact] = {}
    sequences: dict[int, str] = {}
    for fact in facts:
        if fact.event_id in unique and canonical(unique[fact.event_id].model_dump()) != canonical(
            fact.model_dump()
        ):
            raise ValueError("Conflicting duplicate evidence")
        if fact.sequence in sequences and sequences[fact.sequence] != fact.event_id:
            raise ValueError("Conflicting evidence sequence")
        unique[fact.event_id] = fact
        sequences[fact.sequence] = fact.event_id
    ordered = sorted(unique.values(), key=lambda fact: fact.sequence)
    if [fact.sequence for fact in ordered] != list(range(1, len(ordered) + 1)):
        raise ValueError("Evidence sequence gap")
    seen: dict[str, EvidenceFact] = {}
    sources: set[tuple[str, str]] = set()
    for fact in ordered:
        source_key = fact.source_id, fact.kind
        if source_key in sources:
            raise ValueError("Duplicate logical source")
        sources.add(source_key)
        if fact.kind == "invalidated":
            target = seen.get(fact.target_event_id or "")
            if target is None or target.kind != "scored" or target.source_id != fact.source_id:
                raise ValueError("Invalid correction target")
            if (target.pack_id, target.language, target.concept_ids) != (
                fact.pack_id,
                fact.language,
                fact.concept_ids,
            ):
                raise ValueError("Correction scope mismatch")
        seen[fact.event_id] = fact
    return ordered


def replay(
    facts: list[EvidenceFact], version: str, as_of: int, requirements: dict | None = None
) -> dict:
    policy = POLICIES[version]
    ordered = ordered_facts(facts)
    invalidated = {fact.target_event_id for fact in ordered if fact.kind == "invalidated"}
    states: dict[str, dict] = {}
    counters: dict[str, dict] = {}
    for fact in ordered:
        for concept in fact.concept_ids:
            key = state_key(fact.pack_id, fact.language, concept)
            retention_days = max(
                policy.retention_days, (requirements or {}).get(key, {}).get("retention_days", 7)
            )
            state = states.setdefault(key, empty_state(policy))
            counter = counters.setdefault(
                key,
                {
                    "family_weights": {},
                    "independent_sum": 0.0,
                    "assisted_sum": 0.0,
                    "first_success_at": None,
                    "success_families": set(),
                    "interval_days": retention_days,
                    "solve_times": [],
                    "time_ratios": [],
                },
            )
            if (
                fact.kind != "scored"
                or fact.event_id in invalidated
                or not fact.valid
                or not fact.finalized
                or fact.mode == "passive"
                or not fact.quality
            ):
                continue
            if fact.occurred_at > as_of:
                raise ValueError("Replay clock precedes evidence")
            base_weight = policy.weights[fact.evidence_type]
            if fact.mode == "diagnostic":
                base_weight = min(base_weight, policy.diagnostic_weight_cap)
            weight = (
                base_weight
                * policy.hint_multipliers[fact.hint_level]
                * policy.weight_scale
                * fact.quality
                / len(fact.concept_ids)
            )
            spent = counter["family_weights"].get(fact.family_id, 0.0)
            weight = min(weight, max(0.0, policy.family_weight_cap - spent))
            if weight <= 0:
                continue
            total = state["alpha"] + state["beta"]
            mean = state["alpha"] / total
            distance = abs(fact.score - mean)
            if distance > policy.maximum_delta:
                weight = min(
                    weight, policy.maximum_delta * total / (distance - policy.maximum_delta)
                )
            counter["family_weights"][fact.family_id] = spent + weight
            state["alpha"] += weight * fact.score
            state["beta"] += weight * (1 - fact.score)
            state["evidence_count"] += 1
            state["evidence_counts_by_type"][fact.evidence_type] = (
                state["evidence_counts_by_type"].get(fact.evidence_type, 0) + 1
            )
            difficulty_key = str(fact.difficulty)
            state["evidence_counts_by_difficulty"][difficulty_key] = (
                state["evidence_counts_by_difficulty"].get(difficulty_key, 0) + 1
            )
            state["maximum_hint_level"] = max(state["maximum_hint_level"], fact.hint_level)
            counter["solve_times"].append(fact.elapsed_seconds)
            counter["time_ratios"].append(fact.elapsed_seconds / fact.expected_seconds)
            state["last_evidence_at"] = max(state["last_evidence_at"] or 0, fact.occurred_at)
            state["families"] = sorted(set(state["families"]) | {fact.family_id})
            state["forms"] = sorted(set(state["forms"]) | {fact.evidence_type})
            if fact.hint_level == 0:
                state["independent_forms"] = sorted(
                    set(state["independent_forms"]) | {fact.evidence_type}
                )
                state["independent_count"] += 1
                counter["independent_sum"] += fact.score
                state["latest_independent_score"] = fact.score
                if fact.score >= policy.minimum_latest_score:
                    counter["success_families"].add(fact.family_id)
                    state["independent_successes"] = len(counter["success_families"])
                    counter["first_success_at"] = counter["first_success_at"] or fact.occurred_at
                    if fact.mode == "assessment" and fact.unseen:
                        state["assessment_passed"] = True
                if (
                    fact.mode == "retention"
                    and counter["first_success_at"] is not None
                    and fact.occurred_at - counter["first_success_at"] >= retention_days * 86400
                ):
                    state["retention_passed"] = fact.score >= policy.minimum_latest_score
                    counter["interval_days"] = (
                        min(365, counter["interval_days"] * 2)
                        if state["retention_passed"]
                        else retention_days
                    )
                    state["assessment_passed"] = (
                        state["assessment_passed"] and state["retention_passed"]
                    )
            else:
                state["assisted_count"] += 1
                counter["assisted_sum"] += fact.score
            for code in fact.misconception_codes:
                state["misconceptions"][code] = {
                    "last_observed_at": fact.occurred_at,
                    "counterexamples": 0,
                    "counterexample_families": [],
                    "resolved": False,
                }
            if fact.hint_level == 0 and fact.score >= 0.7:
                for code, flag in state["misconceptions"].items():
                    if code not in fact.misconception_codes and not flag["resolved"]:
                        if fact.mode != "retention":
                            flag["counterexample_families"] = sorted(
                                set(flag["counterexample_families"]) | {fact.family_id}
                            )
                            flag["counterexamples"] = len(flag["counterexample_families"])
                        if (
                            flag["counterexamples"] >= 2
                            and fact.mode == "retention"
                            and fact.family_id not in flag["counterexample_families"]
                            and fact.occurred_at - flag["last_observed_at"]
                            >= retention_days * 86400
                        ):
                            flag["resolved"] = True
    for key, state in states.items():
        counter = counters[key]
        state["mastery_mean"] = state["alpha"] / (state["alpha"] + state["beta"])
        state["median_solve_seconds"] = (
            median(counter["solve_times"]) if counter["solve_times"] else None
        )
        state["median_time_ratio"] = (
            median(counter["time_ratios"]) if counter["time_ratios"] else None
        )
        diversity = min(1.0, len(state["families"]) / 3) * min(1.0, len(state["forms"]) / 3)
        state["confidence"] = min(
            0.95, diversity * (1 - math.exp(-(state["alpha"] + state["beta"] - 4) / 8))
        )
        if state["last_evidence_at"] is not None:
            age_days = max(0, as_of - state["last_evidence_at"]) / 86400
            state["retention_factor"] = max(
                policy.retention_floor, 2 ** (-age_days / policy.half_life_days)
            )
            state["due_at"] = state["last_evidence_at"] + counter["interval_days"] * 86400
        state["effective_mastery"] = state["mastery_mean"] * state["retention_factor"]
        state["independent_rate"] = (
            counter["independent_sum"] / state["independent_count"]
            if state["independent_count"]
            else None
        )
        state["assisted_rate"] = (
            counter["assisted_sum"] / state["assisted_count"] if state["assisted_count"] else None
        )
        state["band"] = (
            band(state["mastery_mean"]) if state["evidence_count"] else "insufficient_evidence"
        )
        state["reason_codes"] = (
            ["evidence_backed_estimate"] if state["evidence_count"] else ["insufficient_evidence"]
        )
    # Prerequisite checks use final estimates, independent of dictionary iteration order.
    for key, state in states.items():
        requirement = (requirements or {}).get(key, {})
        ready = all(
            states.get(prerequisite, {}).get("effective_mastery", 0) >= threshold
            for prerequisite, threshold in requirement.get("prerequisites", {}).items()
        )
        gates = {
            "mastery_below_threshold": state["mastery_mean"] >= policy.minimum_mastery,
            "confidence_insufficient": state["confidence"] >= policy.minimum_confidence,
            "independent_evidence_insufficient": state["independent_successes"]
            >= requirement.get("minimum_independent", 2),
            "diverse_evidence_required": len(
                set(state["independent_forms"]) & {"implement", "trace", "explain"}
            )
            >= 2
            and len(state["families"]) >= requirement.get("minimum_families", 2),
            "unseen_assessment_required": state["assessment_passed"],
            "latest_independent_below_threshold": (state["latest_independent_score"] or 0) >= 0.7,
            "prerequisite_not_ready": ready,
        }
        state["prerequisites_ready"] = ready
        state["missing_gates"] = [reason for reason, passed in gates.items() if not passed]
        if all(gates.values()):
            state["band"] = "mastered" if state["retention_passed"] else "provisionally_mastered"
        if state["due_at"] is not None and as_of >= state["due_at"]:
            state["band"] = "retention_due"
            state["reason_codes"].append("delayed_check_due")
        for name in (
            "alpha",
            "beta",
            "mastery_mean",
            "confidence",
            "retention_factor",
            "effective_mastery",
        ):
            state[name] = round(state[name], 12)
    return {
        "schema_version": 1,
        "model_version": version,
        "as_of": as_of,
        "watermark": len(ordered),
        "concepts": dict(sorted(states.items())),
    }
