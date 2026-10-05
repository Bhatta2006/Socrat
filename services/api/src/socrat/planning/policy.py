from dataclasses import asdict, dataclass
from typing import Any

from socrat.learnerstate.policy import digest


@dataclass(frozen=True)
class PlannerPolicy:
    version: str = "1.0.0"
    horizon_days: int = 14
    minimum_confidence: float = 0.65
    readiness: float = 0.75
    mastery: float = 0.80
    weekly_reserve: float = 0.20
    review_fraction: float = 0.25
    cooldown_days: int = 2
    maximum_exposures: int = 3
    difficulty_hold_days: int = 2
    maximum_detours: int = 1


POLICY = PlannerPolicy()
TRACKS: dict[str, dict[str, Any]] = {
    "foundations": {"new_review": [60, 40], "timed": False, "success_zone": [0.75, 0.85]},
    "interview": {"new_review": [50, 50], "timed": False, "success_zone": [0.65, 0.80]},
    "competitive": {"new_review": [40, 60], "timed": True, "success_zone": [0.50, 0.70]},
}
POLICY_DOCUMENT = {**asdict(POLICY), "tracks": TRACKS}
POLICY_DIGEST = digest(POLICY_DOCUMENT)
