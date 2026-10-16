"""Item statistics and repair flags (content.md §8.7). Pure functions over plain values.

After at least 30 responses an item is "calibrating": percent correct, discrimination
(point-biserial correlation of correctness with the learner's ability), distractor selection
rates and median time are computed, and the item is flagged for repair when:

- percent correct is below 10% or above 95%;
- discrimination is below 0.15;
- one distractor is chosen by more than 60% of the strong learners (top third by ability);
- the median time is more than 3x the expected time.
"""

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rules:
    min_responses: int = 30
    too_hard: float = 0.10
    too_easy: float = 0.95
    min_discrimination: float = 0.15
    strong_share: float = 1 / 3
    attractive_share: float = 0.60
    slow_factor: float = 3.0


DEFAULT = Rules()


@dataclass(frozen=True)
class Response:
    correct: bool
    choice: int | None  # authored option index, when recorded
    time_s: int
    ability: float  # the learner's rating for the item's pattern


@dataclass(frozen=True)
class ItemStats:
    n: int
    pct_correct: float
    discrimination: float | None  # None when every answer was the same or abilities are equal
    distractor_counts: dict[str, int] = field(default_factory=dict)  # option index -> picks
    strong_top_distractor: float | None = (
        None  # share of strong learners on the most-picked distractor
    )
    median_time_s: float = 0.0
    flags: tuple[str, ...] = ()


def point_biserial(correct: list[bool], ability: list[float]) -> float | None:
    """r = (M1 − M0) / s · sqrt(p · q), with s the population SD of ability."""
    n = len(correct)
    hits = [a for a, c in zip(ability, correct, strict=True) if c]
    misses = [a for a, c in zip(ability, correct, strict=True) if not c]
    if not hits or not misses:
        return None
    sd = statistics.pstdev(ability)
    if sd == 0:
        return None
    p = len(hits) / n
    return (statistics.fmean(hits) - statistics.fmean(misses)) / sd * math.sqrt(p * (1 - p))


def compute(
    responses: list[Response],
    answer: int,
    expected_seconds: float,
    rules: Rules = DEFAULT,
) -> ItemStats:
    n = len(responses)
    if n == 0:
        return ItemStats(n=0, pct_correct=0.0, discrimination=None)
    pct = sum(r.correct for r in responses) / n
    r_pb = point_biserial([r.correct for r in responses], [r.ability for r in responses])
    picks = Counter(r.choice for r in responses if r.choice is not None and r.choice != answer)
    ordered = sorted(responses, key=lambda r: r.ability, reverse=True)
    strong = ordered[: max(1, math.ceil(n * rules.strong_share))]
    strong_picks = Counter(r.choice for r in strong if r.choice is not None and r.choice != answer)
    top = max(strong_picks.values()) / len(strong) if strong_picks else 0.0
    median = statistics.median(r.time_s for r in responses)
    flags: list[str] = []
    if n >= rules.min_responses:
        if pct < rules.too_hard:
            flags.append("too-hard")
        if pct > rules.too_easy:
            flags.append("too-easy")
        if r_pb is not None and r_pb < rules.min_discrimination:
            flags.append("low-discrimination")
        if top > rules.attractive_share:
            flags.append("attractive-distractor")
        if expected_seconds > 0 and median > rules.slow_factor * expected_seconds:
            flags.append("slow")
    return ItemStats(
        n=n,
        pct_correct=round(pct, 4),
        discrimination=None if r_pb is None else round(r_pb, 4),
        distractor_counts={str(k): v for k, v in sorted(picks.items())},
        strong_top_distractor=round(top, 4),
        median_time_s=float(median),
        flags=tuple(flags),
    )
