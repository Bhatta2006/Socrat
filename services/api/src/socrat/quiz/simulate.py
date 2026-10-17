"""Simulated learners for testing the engine (M3 task 15).

A learner has a fixed true ability θ*; an item has a true difficulty near its band prior.
Each answer is correct with probability P(θ*, d_true). The engine sees only answers, exactly
as in the API, through ``engine.next_choice`` and ``engine.score``.
"""

import random
from dataclasses import dataclass, field, replace

from socrat.quiz import engine
from socrat.quiz.config import DEFAULT, EngineConfig, Mode, Track
from socrat.quiz.modes import ceiling, initial_theta
from socrat.quiz.pools import Item, pool_for_key, unit
from socrat.quiz.rating import p_correct
from socrat.quiz.selection import Context, Step

FORMATS = ("mcq", "output_prediction", "fill_blank", "trace")


def synthetic_bank(
    patterns: tuple[str, ...] = ("sim:window",),
    per_band: int = 12,
    cfg: EngineConfig = DEFAULT,
) -> list[Item]:
    items = []
    for pattern in patterns:
        for band in range(1, 8):
            for n in range(per_band):
                key = f"{pattern}:b{band}-{n}"
                items.append(
                    Item(
                        key=key,
                        concept=pattern,
                        pattern=pattern,
                        family="sim",
                        item_id=f"b{band}-{n}",
                        format=FORMATS[n % len(FORMATS)],
                        band=band,
                        d_prior=cfg.prior(band),
                        pool=pool_for_key(key, cfg),
                        status="provisional",
                        misconceptions=(None, f"miss-{n % 3}", f"miss-{(n + 1) % 3}", None),
                    )
                )
    return items


def true_difficulty(item: Item, spread: float = 60.0) -> float:
    """Fixed per item: the prior plus a stable offset in [-spread, spread]."""
    return item.d_prior + (unit(item.key, "sim-difficulty") * 2 - 1) * spread


@dataclass
class Learner:
    true_theta: float
    thetas: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    seen: set[str] = field(default_factory=set)


def run(
    items: list[Item],
    learner: Learner,
    track: Track,
    mode: Mode,
    seed: str,
    cfg: EngineConfig = DEFAULT,
    max_items: int | None = None,
    patterns: tuple[str, ...] | None = None,
    exposure: dict[str, float] | None = None,
    ratings: dict[str, float] | None = None,
) -> list[Step]:
    """One session; mutates the learner's θ and seen set, and ``ratings`` when given."""
    spec = cfg.modes[mode]
    if max_items is not None:
        spec = replace(spec, max_items=max_items, stop_rules=False)
    scope = patterns or tuple(sorted({i.pattern for i in items}))
    for p in scope:
        learner.thetas.setdefault(p, initial_theta(track, None, cfg))
    rng = random.Random(f"answers:{seed}")
    ratings = ratings if ratings is not None else {}
    item_counts: dict[str, int] = {}
    pool = [i for i in items if i.pool == spec.pool and i.pattern in scope]
    steps: list[Step] = []
    micro = False
    while True:
        ctx = Context(
            track=track,
            mode=spec,
            patterns=scope,
            language="python",
            thetas=dict(learner.thetas),
            seed=seed,
            ratings=dict(ratings),
            seen=frozenset(learner.seen),
            exposure=exposure or {},
            micro_shown=micro,
        )
        choice = engine.next_choice(items, steps, ctx, ceiling(track, pool, 7, cfg), cfg)
        if choice.item is None:
            return steps
        micro = micro or choice.micro is not None
        item = choice.item
        correct = rng.random() < p_correct(learner.true_theta, true_difficulty(item))
        wrong_tag = item.misconceptions[1] if not correct and item.misconceptions else None
        step, change = engine.score(
            item,
            "correct" if correct else "wrong",
            0,
            wrong_tag,
            learner.thetas[item.pattern],
            ratings.get(item.key, item.d_prior),
            learner.counts.get(item.pattern, 0),
            item_counts.get(item.key, 0),
            7,
            cfg,
        )
        steps.append(step)
        learner.seen.add(item.key)
        if change is not None:
            learner.thetas[item.pattern] = change.theta
            learner.counts[item.pattern] = learner.counts.get(item.pattern, 0) + 1
            ratings[item.key] = change.d
            item_counts[item.key] = item_counts.get(item.key, 0) + 1
