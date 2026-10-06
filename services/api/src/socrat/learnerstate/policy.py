"""Retained policy implementations. Candidate policies require an audited promotion."""

import hashlib
import json
from typing import TypedDict

from pydantic import Field

from socrat.skillpacks.types import Contract


class LearningPolicy(Contract):
    version: str
    prior_alpha: float = 2.0
    prior_beta: float = 2.0
    hint_multipliers: list[float] = Field(default_factory=lambda: [1.0, 0.85, 0.65, 0.35, 0.0, 0.0])
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "recognize": 0.5,
            "trace": 0.8,
            "analyze": 0.8,
            "explain": 0.8,
            "implement": 1.2,
            "transfer": 1.8,
            "retain": 1.5,
        }
    )
    maximum_delta: float = 0.15
    diagnostic_weight_cap: float = 0.8
    family_weight_cap: float = 1.8
    minimum_mastery: float = 0.8
    minimum_confidence: float = 0.65
    minimum_latest_score: float = 0.7
    prerequisite_mastery: float = 0.75
    retention_days: int = 7
    half_life_days: float = 30.0
    retention_floor: float = 0.65
    weight_scale: float = 1.0


POLICIES = {
    "1.0.0": LearningPolicy(version="1.0.0"),
    # Conservative shadow candidate; never chosen for a new learner automatically.
    "1.0.1": LearningPolicy(version="1.0.1", weight_scale=0.9),
    # M9 scheduling candidate; promotion still requires reviewed replay evidence.
    "1.1.0": LearningPolicy(version="1.1.0"),
}


class SpacedPolicy(TypedDict):
    intervals_days: list[int]
    expansion: float
    expand_score: float
    keep_score: float
    repair_interval_days: int
    maximum_interval_days: int
    ordinary_session_review_fraction: float
    representations: list[str]


SPACED_POLICY: SpacedPolicy = {
    "intervals_days": [2, 7, 14, 30],
    "expansion": 1.8,
    "expand_score": 0.8,
    "keep_score": 0.6,
    "repair_interval_days": 2,
    "maximum_interval_days": 365,
    "ordinary_session_review_fraction": 0.25,
    "representations": ["recall", "small_implementation", "mixed_problem", "retention_assessment"],
}


def canonical(value) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()
