"""Weighted Beta-Bernoulli mastery with spaced review.

The estimate is deliberately simple and inspectable: each scored piece of evidence
adds weighted pseudo-observations. Assistance lowers the weight of a success but
never softens a failure, so help cannot manufacture mastery.
"""

import math
from dataclasses import asdict, dataclass, replace
from typing import Literal

DAY = 86_400
EvidenceKind = Literal["placement", "quiz", "code", "checkpoint", "review", "external"]
WEIGHTS: dict[str, float] = {
    "placement": 1.0,
    "quiz": 0.6,
    "code": 1.2,
    "checkpoint": 1.6,
    "review": 1.4,
    "external": 0.3,
}
# Socratic assistance level 0–5 → how much a success still counts.
ASSISTANCE = (1.0, 0.85, 0.7, 0.5, 0.3, 0.1)
REVIEW_DAYS = (1, 3, 7, 14, 30, 60)
MAX_STEP = 0.15
MASTERED = 0.8
MIN_CONFIDENCE = 0.55
PRIOR = 2.0  # alpha + beta of the default prior


@dataclass(frozen=True)
class ConceptState:
    alpha: float = 1.0
    beta: float = 1.0
    evidence_count: int = 0
    independent_successes: int = 0
    assisted_successes: int = 0
    failures: int = 0
    review_step: int = 0
    last_evidence_at: int = 0
    next_review_at: int = 0
    assumed: bool = False  # Placed as known; confirmed later by a light review.

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def confidence(self) -> float:
        observed = max(0.0, self.alpha + self.beta - PRIOR)
        return min(0.95, 1 - math.exp(-observed / 5))

    def effective(self, now: int) -> float:
        """Mastery discounted when a scheduled review is overdue."""
        if not self.next_review_at or now <= self.next_review_at:
            return self.mean
        overdue_days = (now - self.next_review_at) / DAY
        return self.mean * max(0.7, 1 - 0.01 * overdue_days)

    def mastered(self, now: int) -> bool:
        return self.effective(now) >= MASTERED and self.confidence >= MIN_CONFIDENCE

    def due(self, now: int) -> bool:
        return bool(self.next_review_at) and now >= self.next_review_at

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict | None) -> "ConceptState":
        return cls(**value) if value else cls()


def placed(known: bool, now: int) -> ConceptState:
    """Placement seeds a prior; it is never treated as verified mastery."""
    if known:
        return ConceptState(
            alpha=4.2, beta=1.0, assumed=True, review_step=1, next_review_at=now + 2 * DAY
        )
    return ConceptState(alpha=1.0, beta=2.0)


def apply(
    state: ConceptState,
    kind: EvidenceKind,
    score: float,
    now: int,
    assistance: int = 0,
) -> ConceptState:
    if not 0 <= score <= 1:
        raise ValueError("score must be within [0, 1]")
    if not 0 <= assistance < len(ASSISTANCE):
        raise ValueError("assistance level out of range")
    weight = WEIGHTS[kind] * (ASSISTANCE[assistance] if score >= 0.5 else 1.0)
    alpha = state.alpha + weight * score
    beta = state.beta + weight * (1 - score)
    # Cap one event's influence on the estimate.
    before, after = state.mean, alpha / (alpha + beta)
    if abs(after - before) > MAX_STEP:
        target = before + math.copysign(MAX_STEP, after - before)
        total = alpha + beta
        alpha, beta = target * total, (1 - target) * total
    success = score >= 0.7
    independent = success and assistance == 0
    if success:
        step = min(state.review_step + 1, len(REVIEW_DAYS))
    else:
        step = 0
    review_at = now + REVIEW_DAYS[max(0, step - 1)] * DAY
    return replace(
        state,
        alpha=alpha,
        beta=beta,
        evidence_count=state.evidence_count + 1,
        independent_successes=state.independent_successes + int(independent),
        assisted_successes=state.assisted_successes + int(success and not independent),
        failures=state.failures + int(not success),
        review_step=step,
        last_evidence_at=now,
        next_review_at=review_at,
        assumed=state.assumed and success,
    )


def band(state: ConceptState, now: int) -> str:
    """Learner-facing wording; never a fake-precise percentage."""
    if state.evidence_count == 0 and not state.assumed:
        return "not_started"
    if state.mastered(now):
        return "strong"
    if state.assumed and state.evidence_count == 0:
        return "likely_known"
    if state.effective(now) >= 0.6:
        return "developing"
    return "needs_practice"
