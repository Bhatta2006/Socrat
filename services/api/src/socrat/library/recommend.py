"""Choose what one learner should practise and learn next.

Pure functions of the learner's state: mastery per concept, an estimated level from the
skill ladder, what they solved or tried, and their plan. Every pick carries a short,
learner-facing reason.
"""

import hashlib
import math
from dataclasses import dataclass, field

from socrat.catalog.practice import PracticeIndex, public, rating_of
from socrat.catalog.registry import Catalog
from socrat.library import ladder
from socrat.mastery.model import ConceptState, band
from socrat.planner.engine import Plan

# Where each course starts on each platform. Rated platforms gain weight as the learner's
# level rises, whatever course they picked.
PLATFORM_BIAS = {
    "zero": {"LeetCode": 0.5, "CSES": 0.4, "Codeforces": 0.1},
    "dsa": {"LeetCode": 0.6, "CSES": 0.25, "Codeforces": 0.15},
    "cp": {"LeetCode": 0.1, "CSES": 0.4, "Codeforces": 0.5},
}
# Target rating window relative to the learner's level, by their band on the concept.
BAND_WINDOW = {
    "not_started": (-300, 0),
    "needs_practice": (-250, 50),
    "developing": (-100, 150),
    "likely_known": (0, 250),
    "strong": (100, 350),
}
LEVEL_NAMES = [
    (800, "Foundations"),
    (1000, "Builder"),
    (1200, "Practitioner"),
    (1400, "Problem solver"),
    (1600, "Advanced"),
    (1800, "Expert"),
    (2000, "Master"),
]


@dataclass
class Learner:
    course: str
    states: dict[str, ConceptState]
    now: int
    rating: int
    solved: set[str] = field(default_factory=set)
    attempted: set[str] = field(default_factory=set)
    seed: str = ""  # rotates near-ties so suggestions change from day to day
    course_concepts: set[str] = field(default_factory=set)
    native_solved: set[str] = field(default_factory=set)  # Socrat's own judged problems

    def band(self, concept: str) -> str:
        return band(self.states.get(concept, ConceptState()), self.now)


def level_view(rating: int) -> dict:
    current = max((r, name) for r, name in LEVEL_NAMES if r <= max(rating, 800))
    upcoming = next(((r, name) for r, name in LEVEL_NAMES if r > rating), None)
    progress = 1.0
    if upcoming:
        progress = (rating - current[0]) / (upcoming[0] - current[0])
    return {
        "rating": rating,
        "name": current[1],
        "next_name": upcoming[1] if upcoming else None,
        "next_rating": upcoming[0] if upcoming else None,
        "progress": round(max(0.0, min(1.0, progress)), 2),
    }


def platform_weight(learner: Learner, platform: str, stretch: bool = False) -> float:
    base = PLATFORM_BIAS.get(learner.course, PLATFORM_BIAS["dsa"]).get(platform, 0.2)
    growth = max(0.0, min(1.0, (learner.rating - 1000) / 800))
    if platform == "Codeforces":
        base += 0.35 * growth + (0.3 if stretch else 0.0)
    elif platform == "CSES":
        base += 0.15 * growth + (0.15 if stretch else 0.0)
    return base


def window(learner: Learner, concept: str, stretch: bool = False) -> tuple[int, int]:
    tier = ladder.tier_of(concept)
    level = learner.rating if tier <= learner.rating else (learner.rating + tier) // 2
    low, high = BAND_WINDOW[learner.band(concept)]
    if stretch:
        low, high = 150, 400
    return level + low, level + high


def _jitter(seed: str, problem_id: str) -> float:
    digest = hashlib.sha256(f"{seed}:{problem_id}".encode()).digest()
    return digest[0] / 255 * 0.25


def score(learner: Learner, problem: dict, concept: str, stretch: bool = False) -> float | None:
    """Higher is better; None means "not a good pick for this learner now"."""
    if problem["id"] in learner.solved:
        return None
    low, high = window(learner, concept, stretch)
    rating = rating_of(problem)
    distance = 0 if low <= rating <= high else min(abs(rating - low), abs(rating - high))
    fit = 1 - distance / 300
    if fit <= 0:
        return None
    value = 2 * fit + platform_weight(learner, problem["platform"], stretch)
    value += 0.4 if problem["concepts"] and problem["concepts"][0] == concept else 0.0
    value += 0.2 if "striver-a2z" in problem["sheets"] else 0.0
    value += 0.15 * min(1.0, math.log1p(problem.get("companies", 0)) / 3)
    value += 0.1 * min(1.0, math.log10(problem.get("solvers", 0) + 1) / 5)
    value += 0.3 if problem["id"] in learner.attempted else 0.0  # finish what you started
    return value + _jitter(learner.seed, problem["id"])


def best_for(
    index: PracticeIndex,
    learner: Learner,
    concept: str,
    limit: int,
    stretch: bool = False,
    exclude: set[str] | None = None,
) -> list[dict]:
    exclude = exclude or set()
    scored = []
    for problem_id in index.by_concept.get(concept, []):
        if problem_id in exclude:
            continue
        problem = index.problems[problem_id]
        value = score(learner, problem, concept, stretch)
        if value is not None:
            scored.append((value, problem_id))
    scored.sort(reverse=True)
    return [index.problems[i] for _, i in scored[:limit]]


def _title(catalog: Catalog, concept: str) -> str:
    return catalog.concept(concept).title if concept in catalog.concepts else concept


def focus(
    catalog: Catalog,
    learner: Learner,
    plan: Plan | None,
    stocked: set[str] | frozenset[str] = frozenset(),
) -> list[tuple[str, str, str]]:
    """(concept, kind, reason) in priority order: reviews, weak spots, current, stretch."""
    picks: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(concept: str, kind: str, reason: str):
        if concept not in seen:
            seen.add(concept)
            picks.append((concept, kind, reason))

    studied = {
        c: s for c, s in learner.states.items() if s.evidence_count and c in catalog.concepts
    }
    for concept, state in sorted(studied.items(), key=lambda x: x[1].next_review_at):
        if state.due(learner.now):
            add(
                concept,
                "review",
                f"{_title(catalog, concept)} is due for review — one problem keeps it fresh.",
            )
    weak = sorted(
        (s.effective(learner.now), c)
        for c, s in studied.items()
        if learner.band(c) in {"needs_practice", "developing"}
    )
    for _, concept in weak[:3]:
        add(
            concept,
            "practice",
            f"You're building {_title(catalog, concept)}; this sits right at your level.",
        )
    if plan is not None:
        for item in plan.roadmap:
            if (
                item["status"] in {"in_progress", "practiced"}
                and item["concept"] in catalog.concepts
            ):
                add(
                    item["concept"],
                    "current",
                    f"Matches {item['title']}, which you're working on now.",
                )
                break
    strong = sorted(
        (
            (s.effective(learner.now), c)
            for c, s in studied.items()
            if learner.band(c) in {"likely_known", "strong"}
        ),
        reverse=True,
    )
    for _, concept in strong[:2]:
        add(concept, "stretch", f"A step up in {_title(catalog, concept)} — you're ready for it.")
    if len(picks) < 2:  # New or nearly new: the first open rungs of their own course.
        for concept in ladder.frontier(learner.states, learner.now, learner.rating, limit=12):
            in_course = not learner.course_concepts or concept in learner.course_concepts
            practicable = concept in stocked or (
                concept in catalog.concepts and catalog.concept(concept).problems
            )
            if in_course and practicable:
                add(concept, "start", f"A gentle first problem on {_title(catalog, concept)}.")
            if len(picks) >= 3:
                break
    return picks


def native_for(catalog: Catalog, learner: Learner, concept: str) -> list[dict]:
    """Socrat's own problems for a concept (run and judged in the app), unsolved first."""
    if concept not in catalog.concepts:
        return []
    order = {"easy": 0, "medium": 1, "hard": 2}
    problems = sorted(
        (catalog.problem(p) for p in catalog.concept(concept).problems),
        key=lambda p: (order[p.difficulty], p.id),
    )
    return [
        dict(
            id=f"socrat:{p.id}",
            title=p.title,
            url=f"/problems/{p.id}",
            platform="Socrat",
            difficulty=p.difficulty,
            rating=None,
            concepts=[concept],
            companies=0,
            striver=False,
        )
        for p in problems
        if p.id not in learner.native_solved
    ]


def next_problems(
    index: PracticeIndex, catalog: Catalog, learner: Learner, plan: Plan | None, limit: int = 6
) -> list[dict]:
    out: list[dict] = []
    taken: set[str] = set()
    per_focus = 1 if limit <= 4 else 2
    stocked = {c for c, ids in index.by_concept.items() if ids}
    for concept, kind, reason in focus(catalog, learner, plan, stocked):
        ref = dict(id=concept, title=_title(catalog, concept), band=learner.band(concept))
        picks: list[dict] = []
        if kind != "stretch":  # practise in the app first, where Socrat can coach and judge
            picks += native_for(catalog, learner, concept)[:1]
        external = best_for(index, learner, concept, per_focus, kind == "stretch", taken)
        picks += [public(p) for p in external][: per_focus - len(picks) or 1]
        for problem in picks:
            taken.add(problem["id"])
            out.append(
                dict(
                    problem,
                    kind=kind,
                    reason=reason,
                    concept=ref,
                    status="attempted" if problem["id"] in learner.attempted else None,
                )
            )
        if len(out) >= limit:
            break
    return out[:limit]


def next_topics(
    catalog: Catalog, learner: Learner, plan: Plan | None, limit: int = 3
) -> list[dict]:
    topics: list[dict] = []
    seen: set[str] = set()

    def add(concept: str, reason: str, kind: str):
        if concept in seen or concept not in catalog.concepts or len(topics) >= limit:
            return
        seen.add(concept)
        c = catalog.concept(concept)
        topics.append(
            dict(
                id=concept,
                title=c.title,
                summary=c.summary,
                reason=reason,
                kind=kind,
                band=learner.band(concept),
                minutes=c.estimated_minutes,
            )
        )

    if plan is not None:
        for item in plan.roadmap:
            if item["status"] == "in_progress":
                add(
                    item["concept"],
                    "You've started this — finishing it unlocks what comes next.",
                    "continue",
                )
        for item in plan.roadmap:
            if item["status"] == "upcoming":
                add(item["concept"], "Next in your plan; its prerequisites are in place.", "next")
                break
        done = sum(
            1 for item in plan.roadmap if item["status"] in {"mastered", "assumed", "practiced"}
        )
        nearly_done = plan.roadmap and done / len(plan.roadmap) >= 0.7
    else:
        nearly_done = False
    for concept, state in learner.states.items():
        if state.failures >= 2 and learner.band(concept) == "needs_practice":
            add(concept, "A few recent misses here — a second pass will pay off.", "revisit")
    if nearly_done or len(topics) < limit:
        # Beyond the course: the next rungs of the ladder, outside what the plan covers.
        for concept in ladder.frontier(learner.states, learner.now, learner.rating, limit=12):
            if (
                concept not in learner.course_concepts
                and catalog.prerequisites.get(concept) is not None
            ):
                ready = all(
                    learner.states.get(p, ConceptState()).effective(learner.now) >= 0.6
                    for p in catalog.prerequisites[concept]
                )
                if ready:
                    add(
                        concept,
                        "You're ready for this — it builds directly on what you know.",
                        "beyond",
                    )
    return topics
