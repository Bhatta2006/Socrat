"""Owner-facing metrics, computed from learning data (no third-party trackers).

Definitions follow docs/product/metric-contract.md where it applies:
- activation: a first lesson completed and a first concept check answered within 24 hours
  of signing up;
- retention Dn: share of learners old enough to be measured who studied on day n (±0 days)
  after sign-up;
- content QA: quiz items whose correct rate is extreme on enough answers.
"""

from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.models import (
    ActivityRecord,
    AssistantMessage,
    DailyActivity,
    Enrollment,
    QuizSession,
    ResourceEvent,
    Submission,
    User,
)

DAY = 86400
MIN_ANSWERS = 20  # an item needs this many answers before it can be flagged
TOO_EASY = 0.95
TOO_HARD = 0.10


def funnel(db: Session) -> list[dict]:
    users = db.scalar(select(func.count()).select_from(User)) or 0
    profiled = db.scalar(select(func.count()).where(User.birth_year.is_not(None))) or 0
    enrolled = db.scalar(select(func.count(func.distinct(Enrollment.user_id)))) or 0
    placed = (
        db.scalar(
            select(func.count(func.distinct(Enrollment.user_id))).where(
                Enrollment.status == "active"
            )
        )
        or 0
    )

    def completed(prefix: str) -> int:
        return (
            db.scalar(
                select(func.count(func.distinct(Enrollment.user_id)))
                .join(ActivityRecord, ActivityRecord.enrollment_id == Enrollment.id)
                .where(
                    ActivityRecord.activity_id.like(f"{prefix}%"),
                    ActivityRecord.completed_at.is_not(None),
                )
            )
            or 0
        )

    solved = (
        db.scalar(
            select(func.count(func.distinct(Submission.user_id))).where(
                Submission.mode == "submit", Submission.verdict == "accepted"
            )
        )
        or 0
    )
    steps = [
        ("Signed up", users),
        ("Profile done", profiled),
        ("Enrolled", enrolled),
        ("Plan ready", placed),
        ("First lesson", completed("lesson:")),
        ("First concept check", completed("quiz:")),
        ("First problem solved", solved),
        ("First checkpoint passed", completed("checkpoint:")),
    ]
    return [
        dict(step=name, learners=count, share=round(count / users, 3) if users else 0.0)
        for name, count in steps
    ]


def activation(db: Session) -> dict:
    signups = dict(db.execute(select(User.id, User.created_at)).all())
    firsts: dict[str, dict[str, int]] = defaultdict(dict)
    rows = db.execute(
        select(Enrollment.user_id, ActivityRecord.activity_id, ActivityRecord.completed_at)
        .join(ActivityRecord, ActivityRecord.enrollment_id == Enrollment.id)
        .where(ActivityRecord.completed_at.is_not(None))
    )
    for user_id, activity, at in rows:
        kind = activity.split(":", 1)[0]
        if kind in {"lesson", "quiz"} and at is not None:
            firsts[user_id][kind] = min(firsts[user_id].get(kind, at), at)
    activated = sum(
        1
        for user_id, created in signups.items()
        if all(
            kind in firsts[user_id] and firsts[user_id][kind] - created <= DAY
            for kind in ("lesson", "quiz")
        )
    )
    return dict(
        activated=activated,
        signups=len(signups),
        rate=round(activated / len(signups), 3) if signups else 0.0,
    )


def retention(db: Session, today: date) -> list[dict]:
    created = {u: date.fromtimestamp(t) for u, t in db.execute(select(User.id, User.created_at))}
    active = defaultdict(set)
    for user_id, day in db.execute(select(DailyActivity.user_id, DailyActivity.day)):
        active[user_id].add(date.fromisoformat(day))
    out = []
    for n in (1, 7, 30):
        eligible = [u for u, d in created.items() if d + timedelta(days=n) <= today]
        kept = sum(1 for u in eligible if created[u] + timedelta(days=n) in active[u])
        out.append(
            dict(
                day=n,
                eligible=len(eligible),
                retained=kept,
                rate=round(kept / len(eligible), 3) if eligible else None,
            )
        )
    return out


def engagement(db: Session, now: int, today: date) -> dict:
    week_ago = (today - timedelta(days=6)).isoformat()
    rows = db.execute(
        select(DailyActivity.user_id, DailyActivity.minutes).where(DailyActivity.day >= week_ago)
    ).all()
    learners = {u for u, _ in rows}
    minutes = [m for _, m in rows if m]
    tutor = db.scalar(
        select(func.count()).where(
            AssistantMessage.role == "user", AssistantMessage.created_at >= now - 7 * DAY
        )
    )
    ratings = Counter(
        r
        for (r,) in db.execute(
            select(AssistantMessage.rating).where(AssistantMessage.rating.is_not(None))
        )
    )
    return dict(
        weekly_active=len(learners),
        minutes_per_active_day=round(sum(minutes) / len(minutes), 1) if minutes else 0.0,
        tutor_messages_7d=tutor or 0,
        tutor_messages_per_active=round((tutor or 0) / len(learners), 1) if learners else 0.0,
        tutor_ratings=dict(up=ratings.get(1, 0), down=ratings.get(-1, 0)),
    )


def item_quality(db: Session, catalog: Catalog) -> list[dict]:
    stats: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for session in db.scalars(select(QuizSession)):
        items: list = session.items
        answers: dict = session.answers
        lookup = {item_id: concept for concept, item_id in items}
        for item_id, answer in answers.items():
            key = (lookup.get(item_id, ""), item_id)
            stats[key][0] += 1
            stats[key][1] += int(bool(answer.get("correct")))
    flagged = []
    for (concept, item_id), (n, correct) in sorted(stats.items(), key=lambda x: -x[1][0]):
        if n < MIN_ANSWERS or concept not in catalog.concepts:
            continue
        rate = correct / n
        if rate >= TOO_EASY or rate <= TOO_HARD:
            flagged.append(
                dict(
                    concept=catalog.concept(concept).title,
                    item=item_id,
                    answers=n,
                    correct_rate=round(rate, 3),
                    issue="too easy" if rate >= TOO_EASY else "too hard or ambiguous",
                )
            )
    return flagged[:50]


def gates(db: Session, catalog: Catalog) -> list[dict]:
    records = db.scalars(
        select(ActivityRecord).where(ActivityRecord.activity_id.like("checkpoint:%"))
    )
    tally: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # learners, passed, attempts
    for record in records:
        completed = record.completed_at
        outcome: dict = record.outcome or {}
        entry = tally[record.activity_id.removeprefix("checkpoint:")]
        entry[0] += 1
        entry[1] += int(completed is not None)
        entry[2] += int(outcome.get("attempts", 1 if completed else 0))
    out = []
    for module_key, (learners, passed, attempts) in tally.items():
        course_id, module_id = module_key.split(":", 1)
        module = next((m for m in catalog.course(course_id).modules if m.id == module_id), None)
        out.append(
            dict(
                module=module.title if module else module_key,
                learners=learners,
                pass_rate=round(passed / learners, 3) if learners else 0.0,
                attempts_per_learner=round(attempts / learners, 2) if learners else 0.0,
            )
        )
    return sorted(out, key=lambda x: x["pass_rate"])


def resources(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            ResourceEvent.url, ResourceEvent.concept, ResourceEvent.helpful, ResourceEvent.opened_at
        )
    )
    stats: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for url, concept, helpful, opened in rows:
        entry = stats[(concept, url)]
        entry[0] += int(opened is not None)
        entry[1] += int(helpful is True)
        entry[2] += int(helpful is False)
    ranked = sorted(
        ((c, u, o, h, n) for (c, u), (o, h, n) in stats.items() if n),
        key=lambda x: (-(x[4] - x[3]), -x[2]),
    )
    return [
        dict(concept=c, url=u, opens=o, helpful=h, unhelpful=n) for c, u, o, h, n in ranked[:20]
    ]


def overview(db: Session, catalog: Catalog, now: int) -> dict:
    today = date.fromtimestamp(now)
    return dict(
        funnel=funnel(db),
        activation=activation(db),
        retention=retention(db, today),
        engagement=engagement(db, now, today),
        gates=gates(db, catalog),
        flagged_items=item_quality(db, catalog),
        unhelpful_resources=resources(db),
    )
