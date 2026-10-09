"""Turn learner evidence into a roadmap, an activity queue and a day-by-day schedule.

Pure function of its inputs: identical inputs always produce the identical plan,
so every adaptation can be replayed and explained.
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from socrat.catalog.registry import Catalog
from socrat.mastery.model import DAY, ConceptState

Pace = Literal["support", "steady", "fast"]
PACE_FACTOR: dict[str, float] = {"support": 1.3, "steady": 1.0, "fast": 0.7}
REVIEW_MINUTES = 5
CHECKPOINT_MINUTES = 15
MAX_REVIEWS_PER_DAY = 2
HORIZON_DAYS = 14
SCORED = {"quiz", "code", "checkpoint", "review"}


@dataclass(frozen=True)
class Activity:
    id: str
    kind: Literal["lesson", "quiz", "problem", "checkpoint", "review", "remedial"]
    concept: str  # qualified concept (module id for checkpoints)
    title: str
    minutes: int
    reason: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Plan:
    pace: Pace
    pace_reason: str
    roadmap: list[dict]
    queue: list[Activity]
    days: list[dict]
    remaining_minutes: int
    projected_finish: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pace": self.pace,
            "pace_reason": self.pace_reason,
            "roadmap": self.roadmap,
            "queue": [a.to_dict() for a in self.queue],
            "days": self.days,
            "remaining_minutes": self.remaining_minutes,
            "projected_finish": self.projected_finish,
            "reasons": self.reasons,
        }


def pace_of(history: list[dict]) -> tuple[Pace, str]:
    scored = [x for x in history if x.get("kind") in SCORED][-6:]
    if len(scored) < 3:
        return "steady", "Gathering evidence about your pace."
    last3, last4, last5 = scored[-3:], scored[-4:], scored[-5:]
    ratios = [
        x["elapsed_seconds"] / x["expected_seconds"]
        for x in last3
        if x.get("elapsed_seconds") and x.get("expected_seconds")
    ]
    if all(x["score"] >= 0.85 and x.get("assistance", 0) == 0 for x in last3) and (
        not ratios or sum(ratios) / len(ratios) <= 1.0
    ):
        return "fast", "Three strong independent results in a row — moving you ahead faster."
    if sum(x["score"] < 0.5 for x in last4) >= 2:
        return "support", "A couple of tough results — adding practice and smaller steps."
    if sum(x.get("assistance", 0) >= 3 for x in last5) >= 3:
        return "support", "You've leaned on big hints lately — building independence first."
    return "steady", "You're progressing at a steady pace."


def _minutes(value: float, pace: Pace) -> int:
    return max(3, int(math.ceil(value * PACE_FACTOR[pace] / 5) * 5))


def concept_activities(
    catalog: Catalog, qualified: str, state: ConceptState, pace: Pace
) -> list[Activity]:
    concept = catalog.concept(qualified)
    est = concept.estimated_minutes
    order = {"easy": 0, "medium": 1, "hard": 2}
    problems = sorted(
        (catalog.problem(p) for p in concept.problems), key=lambda p: (order[p.difficulty], p.id)
    )
    if pace == "fast" and len(problems) > 1:
        # Strong learners skip the warm-up problem but keep the real challenge.
        problems = [p for p in problems if p.difficulty != "easy"] or problems[-1:]
    elif pace == "support" and len(problems) > 1 and state.failures >= 1:
        problems = [p for p in problems if p.difficulty != "hard"] or problems[:1]
    items = [
        Activity(
            f"lesson:{qualified}", "lesson", qualified, concept.title, _minutes(est * 0.3, pace)
        ),
        Activity(
            f"quiz:{qualified}",
            "quiz",
            qualified,
            f"{concept.title} check",
            _minutes(est * 0.15, pace),
        ),
    ]
    share = est * 0.55 / max(1, len(problems))
    items += [
        Activity(f"problem:{p.id}", "problem", qualified, p.title, _minutes(max(10, share), pace))
        for p in problems
    ]
    return items


def weakest_prerequisite(
    catalog: Catalog, qualified: str, states: dict[str, ConceptState], now: int
) -> str | None:
    candidates = [
        (states.get(p, ConceptState()).effective(now), p)
        for p in catalog.prerequisites[qualified]
        if states.get(p, ConceptState()).effective(now) < 0.65
    ]
    return min(candidates)[1] if candidates else None


def study_days(start: date, weekdays: set[int], count: int) -> list[date]:
    days = [start]  # The learner is here today, so today is always a study day.
    cursor = start
    while len(days) < count:
        cursor += timedelta(days=1)
        if cursor.weekday() in weekdays:
            days.append(cursor)
    return days


def build_plan(
    catalog: Catalog,
    targets: list[str],
    states: dict[str, ConceptState],
    completed: set[str],
    history: list[dict],
    today: date,
    now: int,
    weekdays: set[int],
    minutes_per_day: int,
) -> Plan:
    if not weekdays:
        raise ValueError("at least one study weekday is required")
    pace, pace_reason = pace_of(history)
    path = catalog.closure(targets)
    roadmap: list[dict] = []
    queue: list[Activity] = []
    reasons: list[str] = []
    seen_modules: dict[str, list[str]] = {}
    for qualified in path:
        module = f"{catalog.owner[qualified]}:{catalog.module_of(qualified)}"
        seen_modules.setdefault(module, []).append(qualified)
    last_of_module = {members[-1]: module for module, members in seen_modules.items()}
    skipped = 0
    for qualified in path:
        state = states.get(qualified, ConceptState())
        concept = catalog.concept(qualified)
        if state.mastered(now) or (state.assumed and state.evidence_count == 0):
            status = "mastered" if state.mastered(now) else "assumed"
            skipped += 1
        else:
            activities = concept_activities(catalog, qualified, state, pace)
            pending = [a for a in activities if a.id not in completed]
            status = "upcoming"
            if any(a.id in completed for a in activities) or state.evidence_count:
                status = "in_progress"
            if not pending:
                status = "practiced"
            if state.failures >= 2 and state.mean < 0.5:
                weak = weakest_prerequisite(catalog, qualified, states, now)
                if weak and f"remedial:{weak}" not in completed:
                    queue.append(
                        Activity(
                            f"remedial:{weak}",
                            "remedial",
                            weak,
                            f"Refresh: {catalog.concept(weak).title}",
                            _minutes(15, pace),
                            reason=f"{concept.title} depends on {catalog.concept(weak).title}.",
                        )
                    )
                    reasons.append(
                        f"Added a refresher on {catalog.concept(weak).title} before more "
                        f"{concept.title}."
                    )
            queue.extend(pending)
        if qualified in last_of_module:
            module = last_of_module[qualified]
            course_id, module_id = module.split(":", 1)
            members = seen_modules[module]
            needs = [m for m in members if not states.get(m, ConceptState()).mastered(now)]
            check_id = f"checkpoint:{module}"
            if (
                needs
                and not all(states.get(m, ConceptState()).assumed for m in needs)
                and check_id not in completed
            ):
                title = next(
                    x.title for x in catalog.course(course_id).modules if x.id == module_id
                )
                queue.append(
                    Activity(
                        check_id,
                        "checkpoint",
                        module,
                        f"Checkpoint: {title}",
                        CHECKPOINT_MINUTES,
                        reason="Unseen mixed questions confirm the module stuck.",
                    )
                )
        roadmap.append(
            {
                "concept": qualified,
                "title": concept.title,
                "module": module_of(catalog, qualified),
                "status": status,
                "mastery": round(state.effective(now), 3),
                "confidence": round(state.confidence, 3),
                "minutes": concept.estimated_minutes,
            }
        )
    if skipped:
        reasons.append(f"Skipped {skipped} concept(s) you already know; they'll get quick reviews.")
    reviews = sorted(
        (states[q].next_review_at, q)
        for q in path
        if q in states and states[q].next_review_at and q not in {a.concept for a in queue[:3]}
    )
    days: list[dict] = []
    pending_queue = list(queue)
    for day in study_days(today, weekdays, HORIZON_DAYS):
        end = now + ((day - today).days + 1) * DAY
        budget = minutes_per_day
        items: list[dict] = []
        due = [q for at, q in reviews if at <= end][:MAX_REVIEWS_PER_DAY]
        for q in due:
            reviews = [(at, c) for at, c in reviews if c != q]
            items.append(
                Activity(
                    f"review:{q}",
                    "review",
                    q,
                    f"Review: {catalog.concept(q).title}",
                    REVIEW_MINUTES,
                    reason="Spaced review keeps it from fading.",
                ).to_dict()
            )
            budget -= REVIEW_MINUTES
        while pending_queue and (budget >= pending_queue[0].minutes * 0.6 or not items):
            activity = pending_queue.pop(0)
            items.append(activity.to_dict())
            budget -= activity.minutes
        days.append({"date": day.isoformat(), "items": items, "minutes": minutes_per_day - budget})
        if not pending_queue and not reviews:
            break
    remaining = sum(a.minutes for a in queue)
    weekly = minutes_per_day * len(weekdays)
    weeks = remaining / weekly if weekly else 0
    finish = today + timedelta(days=math.ceil(weeks * 7))
    return Plan(pace, pace_reason, roadmap, queue, days, remaining, finish.isoformat(), reasons)


def module_of(catalog: Catalog, qualified: str) -> str:
    return f"{catalog.owner[qualified]}:{catalog.module_of(qualified)}"
