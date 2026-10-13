"""Focus sprints: a short, timed set of judged problems pitched just above the learner's level.

Three unsolved Socrat problems from topics the learner has studied, easiest first, against a
clock. Solves are confirmed by the judge (an accepted Submit after the sprint started), and
the result records how long each took — the habit of solving under time, built gently.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.library import ladder
from socrat.library import service as library
from socrat.mastery.model import ConceptState
from socrat.models import Enrollment, FocusSprint, Submission, User

PROBLEMS = 3
SECONDS_PER_PROBLEM = 15 * 60
DIFFICULTY_OFFSET = {"easy": -200, "medium": 0, "hard": 200}


def problem_rating(catalog: Catalog, problem_id: str) -> int:
    course_id, problem = catalog.problems[problem_id]
    concept = f"{course_id}:{problem.concepts[0]}"
    return ladder.tier_of(concept) + DIFFICULTY_OFFSET[problem.difficulty]


def choose(
    catalog: Catalog,
    states: dict[str, ConceptState],
    rating: int,
    solved: set[str],
    locked: set[str],
) -> list[str]:
    """Up to three unsolved problems near rating+100, spread across topics, easiest first."""
    target = rating + 100
    candidates = []
    for problem_id, (course_id, problem) in catalog.problems.items():
        concept = f"{course_id}:{problem.concepts[0]}"
        studied = states.get(concept, ConceptState()).evidence_count > 0
        if problem_id in solved or concept in locked or not studied:
            continue
        candidates.append((abs(problem_rating(catalog, problem_id) - target), problem_id, concept))
    candidates.sort()
    picked: list[str] = []
    used: set[str] = set()
    for _, problem_id, concept in candidates:
        if concept not in used:
            picked.append(problem_id)
            used.add(concept)
        if len(picked) == PROBLEMS:
            break
    for _, problem_id, _ in candidates:  # fewer topics than slots: allow repeats
        if len(picked) == PROBLEMS:
            break
        if problem_id not in picked:
            picked.append(problem_id)
    return sorted(picked, key=lambda p: (problem_rating(catalog, p), p))


def active(db: Session, enrollment: Enrollment, now: int) -> FocusSprint | None:
    return db.scalar(
        select(FocusSprint)
        .where(
            FocusSprint.enrollment_id == enrollment.id,
            FocusSprint.finished_at.is_(None),
            FocusSprint.deadline >= now,
        )
        .order_by(FocusSprint.started_at.desc())
    )


def start(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> FocusSprint:
    running = active(db, enrollment, now)
    if running is not None:
        return running
    learner = library.learner_for(db, catalog, user, enrollment, now)
    problems = choose(
        catalog, learner.states, learner.rating, learner.native_solved, learner.locked
    )
    if not problems:
        raise HTTPException(409, "sprint_unavailable")
    sprint = FocusSprint(
        enrollment_id=enrollment.id,
        problems=problems,
        started_at=now,
        deadline=now + SECONDS_PER_PROBLEM * len(problems),
        results={},
    )
    db.add(sprint)
    db.flush()
    return sprint


def solve_times(db: Session, user_id: str, sprint: FocusSprint) -> dict[str, int]:
    end = sprint.finished_at or sprint.deadline
    rows = db.execute(
        select(Submission.problem_id, Submission.created_at)
        .where(
            Submission.user_id == user_id,
            Submission.problem_id.in_(sprint.problems),
            Submission.mode == "submit",
            Submission.verdict == "accepted",
            Submission.created_at >= sprint.started_at,
            Submission.created_at <= end,
        )
        .order_by(Submission.created_at)
    )
    times: dict[str, int] = {}
    for problem_id, created in rows:
        times.setdefault(problem_id, created - sprint.started_at)
    return times


def finish(db: Session, user: User, sprint: FocusSprint, now: int) -> None:
    if sprint.finished_at is not None:
        return
    sprint.finished_at = min(now, sprint.deadline)
    sprint.results = solve_times(db, user.id, sprint)
    learn.bump_daily(db, user, now, minutes=max(1, (sprint.finished_at - sprint.started_at) // 60))


def view(db: Session, catalog: Catalog, user: User, sprint: FocusSprint, now: int) -> dict:
    finished = sprint.finished_at is not None
    times = sprint.results if finished else solve_times(db, user.id, sprint)
    problems = []
    for problem_id in sprint.problems:
        course_id, problem = catalog.problems[problem_id]
        problems.append(
            dict(
                id=problem_id,
                title=problem.title,
                difficulty=problem.difficulty,
                concept=catalog.concept(f"{course_id}:{problem.concepts[0]}").title,
                solved_after=times.get(problem_id),
            )
        )
    return dict(
        id=sprint.id,
        started_at=sprint.started_at,
        deadline=sprint.deadline,
        seconds_left=None if finished else max(0, sprint.deadline - now),
        finished=finished,
        solved=len(times),
        problems=problems,
    )


def history(db: Session, enrollment: Enrollment, limit: int = 10) -> list[dict]:
    rows = db.scalars(
        select(FocusSprint)
        .where(FocusSprint.enrollment_id == enrollment.id, FocusSprint.finished_at.is_not(None))
        .order_by(FocusSprint.started_at.desc())
        .limit(limit)
    )
    return [
        dict(
            id=r.id,
            started_at=r.started_at,
            solved=len(r.results),
            total=len(r.problems),
            minutes=max(1, ((r.finished_at or r.deadline) - r.started_at) // 60),
        )
        for r in rows
    ]
