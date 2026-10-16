"""One quiz step, without storage: decide what comes next, then score an answer.

The API service and the simulator both drive sessions through these two functions, so the
simulator tests the same code learners meet.
"""

from socrat.quiz.config import DEFAULT, EngineConfig
from socrat.quiz.modes import stop_reason
from socrat.quiz.pools import Item
from socrat.quiz.rating import Update, answer_score, theta_bounds, update
from socrat.quiz.selection import Choice, Context, Outcome, Step, select


def next_choice(
    items: list[Item],
    steps: list[Step],
    ctx: Context,
    ceiling_band: int,
    cfg: EngineConfig = DEFAULT,
) -> Choice:
    """The next item, or a stop reason (max_items, ceiling, stable, exhausted)."""
    reason = stop_reason(steps, ctx.mode, ceiling_band, cfg)
    if reason:
        return Choice(None, reason)
    return select(items, steps, ctx, cfg)


def score(
    item: Item,
    outcome: Outcome,
    hints: int,
    misconception: str | None,
    theta: float,
    d: float,
    n_user: int,
    n_item: int,
    max_band: int,
    cfg: EngineConfig = DEFAULT,
) -> tuple[Step, Update | None]:
    """The recorded step and the rating update; a skip ("not seen this") changes nothing."""
    if outcome == "skipped":
        step = Step(
            item.key, item.pattern, item.band, item.format, "skipped", hints, None, theta, theta
        )
        return step, None
    change = update(
        theta,
        d,
        answer_score(outcome == "correct", hints, cfg),
        n_user,
        n_item,
        item_frozen=item.status == "calibrated",
        bounds=theta_bounds(max_band, cfg),
        cfg=cfg,
    )
    step = Step(
        item.key,
        item.pattern,
        item.band,
        item.format,
        outcome,
        hints,
        misconception if outcome == "wrong" else None,
        theta,
        change.theta,
    )
    return step, change
