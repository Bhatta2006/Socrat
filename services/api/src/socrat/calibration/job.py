"""Database side of calibration: compute item health, and apply human-approved status changes.

``run`` only ever writes statistics and flags; it never changes an item's status and never
fills ``approved_by``. Status changes go through ``transition``, which needs a named human
approver and, for ``calibrated``, at least 30 responses and no repair flags.
"""

import time
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.calibration import stats
from socrat.catalog.registry import Catalog
from socrat.models import ItemCalibration, LearnerAbility, QuizResponse
from socrat.quiz import service as quiz
from socrat.quiz.pools import Item

LEGACY_EXPECTED_SECONDS = 60
# Names that identify tooling rather than a person; an approval needs a person.
NOT_A_PERSON = {"auto", "automatic", "bot", "ci", "claude", "script", "socrat", "system", "tool"}
ALLOWED = {
    ("provisional", "calibrated"),
    ("provisional", "retired"),
    ("calibrated", "retired"),
    ("calibrated", "provisional"),  # back to repair, keeping the record
}


class TransitionError(ValueError):
    pass


def answer_index(catalog: Catalog, item: Item) -> int:
    shown = quiz.render(catalog, item, "calibration", "python")
    return shown["order"][shown["answer"]]


def expected_seconds(catalog: Catalog, item: Item) -> float:
    """Half the family's time limit; legacy items have no limit, so a minute."""
    if item.family:
        return catalog.quiz_families[item.family].time_limit_s / 2
    return LEGACY_EXPECTED_SECONDS


def run(
    db: Session, catalog: Catalog, now: int | None = None, rules: stats.Rules = stats.DEFAULT
) -> dict[str, stats.ItemStats]:
    """Recompute statistics for every item with responses; returns them by item key."""
    now = now or int(time.time())
    items = {i.key: i for i in quiz.bank(catalog)}
    abilities = {(a.enrollment_id, a.pattern): a.theta for a in db.scalars(select(LearnerAbility))}
    grouped: dict[str, list[stats.Response]] = defaultdict(list)
    for row in db.scalars(select(QuizResponse)):
        item = items.get(row.item_id)
        if item is None:
            continue  # content removed since the answer; the response stays for the record
        grouped[row.item_id].append(
            stats.Response(
                correct=row.correct,
                choice=row.choice,
                time_s=row.time_s,
                ability=abilities.get((row.enrollment_id, item.pattern), 0.0),
            )
        )
    computed = {}
    for key, responses in grouped.items():
        item = items[key]
        result = stats.compute(
            responses, answer_index(catalog, item), expected_seconds(catalog, item), rules
        )
        computed[key] = result
        record = db.get(ItemCalibration, key)
        if record is None:
            record = ItemCalibration(item_id=key, status=item.status)
            db.add(record)
        record.n_responses = result.n
        record.pct_correct = result.pct_correct
        record.discrimination = result.discrimination
        record.distractor_counts = result.distractor_counts
        record.median_time_s = result.median_time_s
        record.flags = list(result.flags)
        record.computed_at = now
    return computed


def transition(
    db: Session,
    item_id: str,
    to: str,
    approver: str,
    now: int | None = None,
    rules: stats.Rules = stats.DEFAULT,
) -> ItemCalibration:
    """Move an item to a new status on a named person's approval."""
    name = approver.strip()
    if len(name) < 2 or name.lower() in NOT_A_PERSON:
        raise TransitionError("a status change needs the name of the person approving it")
    record = db.get(ItemCalibration, item_id)
    if record is None:
        raise TransitionError(f"{item_id}: no statistics yet; run the stats job first")
    if (record.status, to) not in ALLOWED:
        raise TransitionError(f"{item_id}: {record.status} -> {to} is not allowed")
    if to == "calibrated":
        if record.n_responses < rules.min_responses:
            raise TransitionError(
                f"{item_id}: {record.n_responses} responses; calibration needs {rules.min_responses}"
            )
        if record.flags:
            raise TransitionError(f"{item_id}: flagged for repair ({', '.join(record.flags)})")
    record.status = to
    record.approved_by = name
    record.approved_at = now or int(time.time())
    return record
