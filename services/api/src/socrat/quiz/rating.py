"""Elo-style ratings shared by learners and items (content.md §8.5).

θ is a learner's rating for one pattern, d an item's difficulty, both on the same scale.
θ drives item choice and reporting only; mastery stays the Beta-Bernoulli model (D4).
"""

from dataclasses import dataclass

from socrat.quiz.config import DEFAULT, EngineConfig


def p_correct(theta: float, d: float) -> float:
    """Chance of a correct, unassisted answer."""
    return 1.0 / (1.0 + 10 ** ((d - theta) / 400.0))


def k_user(n: int, cfg: EngineConfig = DEFAULT) -> float:
    """Learner step size after ``n`` earlier answers on this pattern."""
    for limit, k in cfg.k_user_steps:
        if n < limit:
            return k
    return cfg.k_user_floor


def k_item(n: int, cfg: EngineConfig = DEFAULT) -> float:
    """Item step size after ``n`` earlier responses to it."""
    return cfg.k_item_base / (1 + n / cfg.k_item_halflife) + cfg.k_item_floor


def answer_score(correct: bool, hints: int, cfg: EngineConfig = DEFAULT) -> float:
    """1.0 unassisted, less per hint used, 0.0 when wrong."""
    if not correct:
        return 0.0
    return cfg.hint_scores[min(max(hints, 0), len(cfg.hint_scores) - 1)]


def band_for(theta: float, cfg: EngineConfig = DEFAULT) -> int:
    """Band whose prior is nearest θ; the lower band wins a tie."""
    return min(range(1, 8), key=lambda b: (abs(cfg.prior(b) - theta), b))


def theta_bounds(max_band: int, cfg: EngineConfig = DEFAULT) -> tuple[float, float]:
    """θ range a learner may hold while bands above ``max_band`` are not allowed."""
    high = min(cfg.theta_max, cfg.prior(max_band) + cfg.band_headroom)
    return cfg.theta_min, high


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class Update:
    theta: float
    d: float
    p: float
    score: float


def update(
    theta: float,
    d: float,
    score: float,
    n_user: int,
    n_item: int,
    item_frozen: bool,
    bounds: tuple[float, float],
    cfg: EngineConfig = DEFAULT,
) -> Update:
    """θ ← θ + K_u·(s − P); d ← d − K_i·(s − P) unless the item is calibrated."""
    if not 0.0 <= score <= 1.0:
        raise ValueError("score must be within [0, 1]")
    p = p_correct(theta, d)
    surprise = score - p
    new_theta = clamp(theta + k_user(n_user, cfg) * surprise, *bounds)
    new_d = d if item_frozen else d - k_item(n_item, cfg) * surprise
    return Update(theta=new_theta, d=new_d, p=p, score=score)
