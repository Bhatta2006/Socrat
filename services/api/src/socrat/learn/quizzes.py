"""Quiz-style activities: concept checks, spaced reviews, refreshers and module checkpoints.

Answers stay server-side. Learning quizzes give feedback per question; checkpoints reveal
results only when finished, because they are assessments.
"""

import random

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem
from socrat.learn import service as learn
from socrat.mastery.model import EvidenceKind
from socrat.models import Enrollment, QuizSession, User

KINDS: dict[str, EvidenceKind] = {
    "quiz": "quiz",
    "review": "review",
    "remedial": "quiz",
    "checkpoint": "checkpoint",
}


def item(catalog: Catalog, concept: str, item_id: str) -> QuizItem:
    return next(q for q in catalog.concept(concept).quiz if q.id == item_id)


def choose_items(
    catalog: Catalog, enrollment: Enrollment, activity_id: str, seed: int
) -> list[list[str]]:
    kind, _, target = activity_id.partition(":")
    rng = random.Random(f"{enrollment.id}:{activity_id}:{seed}")
    if kind == "quiz":
        quiz = sorted(catalog.concept(target).quiz, key=lambda q: (q.difficulty, q.id))
        return [[target, q.id] for q in quiz[:5]]
    if kind in {"review", "remedial"}:
        quiz = list(catalog.concept(target).quiz)
        rng.shuffle(quiz)
        return [[target, q.id] for q in quiz[: 3 if kind == "review" else 4]]
    if kind == "checkpoint":
        course_id, module_id = target.split(":", 1)
        course = catalog.course(course_id)
        module = next((m for m in course.modules if m.id == module_id), None)
        if module is None:
            raise HTTPException(404, "not_found")
        picked: list[list[str]] = []
        for cid in module.concepts:
            qualified = f"{course_id}:{cid}"
            hardest = sorted(catalog.concept(qualified).quiz, key=lambda q: (-q.difficulty, q.id))
            picked += [[qualified, q.id] for q in hardest[:2]]
        rng.shuffle(picked)
        return picked[:10]
    raise HTTPException(404, "not_found")


def open_session(
    db: Session, catalog: Catalog, enrollment: Enrollment, activity_id: str, now: int
) -> QuizSession:
    kind = activity_id.partition(":")[0]
    if kind not in KINDS:
        raise HTTPException(404, "not_found")
    session = db.scalar(
        select(QuizSession)
        .where(
            QuizSession.enrollment_id == enrollment.id,
            QuizSession.activity_id == activity_id,
            QuizSession.completed_at.is_(None),
        )
        .order_by(QuizSession.created_at.desc())
    )
    if session is None:
        session = QuizSession(
            enrollment_id=enrollment.id,
            activity_id=activity_id,
            items=choose_items(catalog, enrollment, activity_id, now // 86400),
            answers={},
            created_at=now,
        )
        db.add(session)
        db.flush()
        learn.start_activity(db, enrollment, activity_id, now)
    return session


def session_view(catalog: Catalog, session: QuizSession, language: str) -> dict:
    graded = not session.activity_id.startswith("checkpoint:") or session.completed_at is not None
    questions = []
    for concept, item_id in session.items:
        q = item(catalog, concept, item_id)
        answer = session.answers.get(item_id)
        shown = q.shown(session.id)
        entry = dict(
            id=q.id,
            concept=concept,
            concept_title=catalog.concept(concept).title,
            kind=q.kind,
            prompt=q.prompt,
            code=q.snippet(language),
            options=shown["options"],
            answered=answer is not None,
            choice=answer["choice"] if answer else None,
        )
        if answer is not None and graded:
            entry.update(
                correct=answer["correct"], answer=shown["answer"], explanation=q.explanation
            )
        questions.append(entry)
    return dict(
        id=session.id,
        activity_id=session.activity_id,
        questions=questions,
        completed=session.completed_at is not None,
        score=score_of(session) if session.completed_at else None,
        feedback="immediate" if not session.activity_id.startswith("checkpoint:") else "at_end",
    )


def score_of(session: QuizSession) -> float:
    if not session.items:
        return 0.0
    return sum(1 for a in session.answers.values() if a["correct"]) / len(session.items)


def answer(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    session: QuizSession,
    item_id: str,
    choice: int,
    now: int,
) -> dict:
    if session.completed_at is not None:
        raise HTTPException(409, "quiz_already_completed")
    pair = next((p for p in session.items if p[1] == item_id), None)
    if pair is None:
        raise HTTPException(404, "not_found")
    q = item(catalog, pair[0], item_id)
    if not 0 <= choice < len(q.options):
        raise HTTPException(422, "invalid_choice")
    if item_id in session.answers:
        raise HTTPException(409, "already_answered")
    correct = q.is_correct(session.id, choice)  # choice is a display position
    session.answers = {**session.answers, item_id: {"choice": choice, "correct": correct}}
    finished = len(session.answers) == len(session.items)
    if finished:
        finish(db, catalog, user, enrollment, session, now)
    return dict(finished=finished, correct=correct)


def finish(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    session: QuizSession,
    now: int,
):
    session.completed_at = now
    kind = KINDS[session.activity_id.partition(":")[0]]
    elapsed = learn.elapsed(db, enrollment, session.activity_id, now)
    expected = learn.expected_seconds(catalog, session.activity_id, enrollment)
    per_concept: dict[str, list[bool]] = {}
    for concept, item_id in session.items:
        per_concept.setdefault(concept, []).append(
            bool(session.answers.get(item_id, {}).get("correct"))
        )
    for concept, results in per_concept.items():
        learn.record_evidence(
            db,
            enrollment,
            concept,
            kind,
            sum(results) / len(results),
            session.activity_id,
            now,
            elapsed_seconds=elapsed,
            expected_seconds=expected,
        )
    if session.activity_id.startswith(("quiz:", "checkpoint:", "remedial:")):
        learn.complete_activity(
            db, user, enrollment, session.activity_id, now, outcome={"score": score_of(session)}
        )
    else:  # Reviews recur on a schedule; count the effort without completing them forever.
        learn.bump_daily(db, user, now, minutes=max(1, round(elapsed / 60)))
