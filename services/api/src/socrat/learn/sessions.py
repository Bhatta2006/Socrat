"""Durable session blocks; completion and progress come from server-owned evidence."""

import copy
import random
from collections import Counter
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.database import record_event
from socrat.learn import service as learn
from socrat.mastery.model import ConceptState, EvidenceKind, band
from socrat.models import AssistantThread, Enrollment, Evidence, LearningSession, Submission, User
from socrat.planner.sessions import compose

REFLECTIONS = {"clear", "syntax", "strategy", "boundaries", "tired", "need-example"}
SCORED_ATOMS: dict[str, EvidenceKind] = {
    "faded": "guided",
    "trace": "trace",
    "predict": "retrieval",
    "debug": "debug",
    "explanation": "explanation",
}


def current(db: Session, user: User, enrollment: Enrollment, now: int) -> LearningSession | None:
    return db.scalar(
        select(LearningSession)
        .where(
            LearningSession.enrollment_id == enrollment.id,
            LearningSession.day == learn.local_day(user, now).isoformat(),
        )
        .with_for_update()
    )


def owned(db: Session, user: User, session_id: str, now: int) -> tuple[LearningSession, Enrollment]:
    row = db.scalar(
        select(LearningSession)
        .join(Enrollment)
        .where(
            LearningSession.id == session_id,
            Enrollment.user_id == user.id,
        )
        .with_for_update()
    )
    if row is None:
        raise HTTPException(404, "not_found")
    enrollment = db.get(Enrollment, row.enrollment_id)
    if enrollment is None:
        raise HTTPException(404, "not_found")
    if not enrollment.active and row.finished_at is None:
        raise HTTPException(409, "enrollment_changed")
    if row.day != learn.local_day(user, now).isoformat() and row.finished_at is None:
        raise HTTPException(409, "session_expired")
    return row, enrollment


def instruction_blocked(db: Session, enrollment: Enrollment, now: int) -> bool:
    user = db.get(User, enrollment.user_id)
    row = current(db, user, enrollment, now) if user else None
    if row is None or row.finished_at is not None:
        return False
    blocks = row.payload["blocks"]
    index = row.payload["index"]
    return index < len(blocks) and blocks[index].get("mode") == "independent"


def guard_problem_turn(db: Session, user: User, enrollment: Enrollment, problem_id: str, now: int):
    row = current(db, user, enrollment, now)
    if row is None or row.finished_at is not None:
        return
    for index, block in enumerate(row.payload["blocks"]):
        if (
            index > row.payload["index"]
            and block.get("problem") == problem_id
            and block.get("mode") == "independent"
        ):
            raise HTTPException(409, "session_block_not_started")


def start(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    now: int,
    minutes: int | None = None,
    allow_drafts: bool = False,
    pattern_planner: bool = False,
) -> LearningSession:
    from socrat.assessments import service as assessments

    if assessments.in_progress(db, enrollment, now):
        raise HTTPException(409, "assessment_in_progress")
    existing = current(db, user, enrollment, now)
    if existing is not None:
        return existing
    states = learn.states_for(db, enrollment)
    plan = learn.plan_for(db, catalog, user, enrollment, now, record=False)
    locked = learn.locked_concepts(db, catalog, enrollment, now)
    candidates = [a.concept for a in plan.queue if a.kind not in {"checkpoint", "review"}]
    candidates += catalog.closure(catalog.course_concepts(enrollment.course_id))
    solved = set(
        db.scalars(
            select(Submission.problem_id).where(
                Submission.user_id == user.id,
                Submission.mode == "submit",
                Submission.verdict == "accepted",
            )
        )
    )
    helped = {
        t.scope.removeprefix("problem:")
        for t in db.scalars(
            select(AssistantThread).where(
                AssistantThread.user_id == user.id,
            )
        )
        if t.scope.startswith("problem:") and t.ladder.get("max_level", 0) > 0
    }
    focus = next(
        (
            q
            for q in candidates
            if q in catalog.concepts
            and q not in locked
            and not any(p in locked for p in catalog.prerequisites[q])
            and any(pid not in solved | helped for pid in catalog.concept(q).problems)
        ),
        None,
    )
    if focus is None:
        raise HTTPException(409, "fresh_independent_problem_unavailable")
    problems = [pid for pid in catalog.concept(focus).problems if pid not in solved | helped]
    problems.sort(
        key=lambda p: ({"easy": 0, "medium": 1, "hard": 2}[catalog.problem(p).difficulty], p)
    )
    evidence = list(
        db.scalars(
            select(Evidence)
            .where(
                Evidence.enrollment_id == enrollment.id,
                Evidence.concept == focus,
            )
            .order_by(Evidence.created_at.desc(), Evidence.seq.desc())
            .limit(30)
        )
    )
    failures: Counter[str] = Counter()
    resolved = set()
    for item in evidence:
        tag = item.details.get("misconception")
        if not tag or tag in resolved:
            continue
        if item.score >= 0.7:
            resolved.add(tag)
        else:
            failures[str(tag)] += 1
    recent_jobs = list(
        db.scalars(
            select(Submission)
            .where(
                Submission.user_id == user.id,
                Submission.status == "done",
                Submission.created_at >= now - 86400,
                Submission.language == enrollment.language,
            )
            .order_by(Submission.created_at.desc())
            .limit(3)
        )
    )
    syntax_friction = len(recent_jobs) == 3 and all(
        j.verdict == "compile_error" for j in recent_jobs
    )
    slow_correct = bool(
        evidence
        and evidence[0].kind == "code"
        and evidence[0].score == 1
        and evidence[0].expected_seconds > 0
        and evidence[0].elapsed_seconds > evidence[0].expected_seconds
    )
    diverse = (
        len(
            {
                e.activity_id
                for e in evidence
                if e.kind == "code" and e.score == 1 and e.assistance == 0
            }
        )
        >= 2
    )
    recovery = learn.days_away(db, user, enrollment, now) >= 2
    previous = db.scalar(
        select(LearningSession)
        .where(
            LearningSession.enrollment_id == enrollment.id,
            LearningSession.finished_at.is_not(None),
        )
        .order_by(LearningSession.created_at.desc())
    )
    fatigue = bool(previous and previous.payload.get("reflection") == "tired")
    repair = bool(
        previous
        and (
            previous.payload.get("reflection") == "need-example"
            or any(
                o.get("mode") == "independent" and not o.get("accepted")
                for o in previous.payload["outcomes"]
            )
        )
    )
    if repair:
        problems = problems[:1]
    budget = minutes or (
        min(20, enrollment.minutes_per_day) if recovery or fatigue else enrollment.minutes_per_day
    )
    due = next(
        (
            q
            for q, s in sorted(states.items(), key=lambda pair: pair[1].next_review_at)
            if s.due(now) and q not in locked
        ),
        None,
    )
    level = next(
        item
        for item in catalog.course(enrollment.course_id).levels
        if item.id == enrollment.level_id
    )
    transfer = next(
        (
            pid
            for q, state in states.items()
            if q != focus and q not in locked and state.mastered(now)
            for pid in catalog.concept(q).problems
            if pid not in solved | helped
        ),
        None,
    )
    pattern_plan = None
    if pattern_planner:
        from socrat.learn import pattern_sessions

        last = (previous.payload.get("pattern_plan") or {}).get("pattern") if previous else None
        pattern_plan = pattern_sessions.plan(
            db,
            catalog,
            enrollment,
            states,
            locked,
            learn.curriculum(catalog, enrollment),
            solved,
            helped,
            budget,
            level.start_concept is None or repair,
            recovery,
            now,
            allow_drafts,
            last,
        )
    if pattern_plan is not None:
        focus, blocks = pattern_plan.concept, pattern_plan.blocks
    else:
        blocks = compose(
            catalog,
            focus,
            states,
            problems,
            budget,
            level.start_concept is None or repair,
            recovery,
            due,
            dict(failures),
            syntax_friction,
            slow_correct,
            now,
            enrollment.language,
            diverse,
            allow_drafts,
            transfer,
        )
    if not recovery and not any(b.get("mode") == "independent" for b in blocks):
        raise HTTPException(409, "fresh_independent_problem_unavailable")
    row = LearningSession(
        enrollment_id=enrollment.id,
        day=learn.local_day(user, now).isoformat(),
        created_at=now,
        payload=dict(
            blocks=blocks,
            index=0,
            step=0,
            answers={},
            started=now,
            minutes=budget,
            recovery=recovery,
            language=enrollment.language,
            concept=focus,
            before={q: s.to_dict() for q, s in states.items()},
            content_digest=catalog.digest,
            feedback=None,
            outcomes=[],
        ),
    )
    if pattern_plan is not None:
        row.payload["pattern_plan"] = dict(
            pattern=pattern_plan.pattern,
            type=pattern_plan.kind,
            triggers=list(pattern_plan.fired),
            scores=[
                dict(pattern=s.pattern, total=s.total, parts=s.parts) for s in pattern_plan.scores
            ],
        )
    db.add(row)
    db.flush()
    record_event(db, user.id, "learning.session_started", row.id)
    return row


def answer(
    db: Session,
    catalog: Catalog,
    user: User,
    row: LearningSession,
    enrollment: Enrollment,
    block_index: int,
    step_index: int,
    choice: int,
    now: int,
) -> None:
    if row.finished_at is not None:
        raise HTTPException(409, "session_completed")
    data = copy.deepcopy(row.payload)
    if block_index != data["index"] or step_index != data["step"]:
        raise HTTPException(409, "stale_session_block")
    block = data["blocks"][block_index]
    ensure_content(catalog, block)
    if block["kind"] != "atom" or not block["atom"]["steps"]:
        raise HTTPException(409, "block_has_no_check")
    key = f"{block_index}:{step_index}"
    if key in data["answers"]:
        return
    step = block["atom"]["steps"][step_index]
    order = option_order(row.id, block_index, step_index, len(step["options"]))
    if not 0 <= choice < len(order):
        raise HTTPException(422, "invalid_choice")
    correct = order[choice] == step["answer"]
    data["answers"][key] = correct
    data["feedback"] = dict(
        correct=correct,
        explanation=step["explanation"],
        copy="You predicted that step correctly."
        if correct
        else "Compare the state with your prediction, then try the next step.",
    )
    last = step_index == len(block["atom"]["steps"]) - 1
    atom_kind = block["atom"]["kind"]
    if last and atom_kind in SCORED_ATOMS and counts_as_evidence(block):
        score = sum(data["answers"][f"{block_index}:{i}"] for i in range(step_index + 1)) / (
            step_index + 1
        )
        learn.record_evidence(
            db,
            enrollment,
            block["concept"],
            SCORED_ATOMS[atom_kind],
            score,
            f"atom:{row.id}:{block_index}",
            now,
            assistance=2 if atom_kind == "faded" else 0,
            details=dict(
                session_id=row.id,
                atom_id=block["atom"]["id"],
                version=block["version"],
                misconception=block["atom"].get("misconception"),
            ),
        )
    record_event(db, user.id, "learning.prediction_committed", row.id)
    row.payload = data


def option_order(session_id: str, block: int, step: int, count: int) -> list[int]:
    order = list(range(count))
    random.Random(f"{session_id}:{block}:{step}").shuffle(order)
    return order


def advance(
    db: Session,
    catalog: Catalog,
    user: User,
    row: LearningSession,
    enrollment: Enrollment,
    block_index: int,
    now: int,
    reflection: str | None = None,
) -> None:
    if row.finished_at is not None:
        return
    data = copy.deepcopy(row.payload)
    if block_index != data["index"]:
        raise HTTPException(409, "stale_session_block")
    block = data["blocks"][block_index]
    ensure_content(catalog, block)
    outcome = dict(kind=block["kind"], title=block["title"])
    if block["kind"] == "atom" and block["atom"]["steps"]:
        if f"{block_index}:{data['step']}" not in data["answers"]:
            raise HTTPException(409, "prediction_required")
        if data["step"] + 1 < len(block["atom"]["steps"]):
            data["step"] += 1
            data["feedback"] = None
            row.payload = data
            return
    elif block["kind"] == "problem":
        job = db.scalar(
            select(Submission)
            .where(
                Submission.enrollment_id == enrollment.id,
                Submission.problem_id == block["problem"],
                Submission.mode == "submit",
                Submission.status == "done",
                Submission.created_at >= data["started"],
                Submission.verdict.not_in(["", "system_error"]),
            )
            .order_by(Submission.created_at.desc())
        )
        if job is None:
            raise HTTPException(
                409,
                "independent_attempt_required"
                if block["mode"] == "independent"
                else "practice_attempt_required",
            )
        if block["mode"] == "independent" and job.assistance > 0:
            raise HTTPException(409, "assisted_attempt_not_independent")
        outcome.update(mode=block["mode"], submission_id=job.id, accepted=job.verdict == "accepted")
        if block["mode"] == "independent" and job.verdict != "accepted":
            data["next_focus"] = (
                "A simpler fresh variant with a worked example; today's attempt showed what to repair."
            )
    elif block["kind"] == "review":
        check = db.scalar(
            select(Evidence.id).where(
                Evidence.enrollment_id == enrollment.id,
                Evidence.activity_id == block["activity"],
                Evidence.created_at >= data["started"],
            )
        )
        if check is None:
            raise HTTPException(409, "retrieval_required")
    elif block["kind"] == "reflection":
        if reflection not in REFLECTIONS:
            raise HTTPException(422, "reflection_required")
        data["reflection"] = reflection
    if block["kind"] == "atom":
        atom_kind = block["atom"]["kind"]
        outcome["atom_kind"] = atom_kind
        if atom_kind in {"worked", "concept", "explanation"} and not block.get("pattern"):
            kind = "quiz" if atom_kind == "explanation" else "lesson"
            learn.complete_activity(
                db,
                user,
                enrollment,
                f"{kind}:{block['concept']}",
                now,
                outcome={"session_id": row.id, "source": "content_atoms"},
            )
    data["outcomes"].append(outcome)
    data["index"] += 1
    data["step"] = 0
    data["feedback"] = None
    data["started"] = now
    row.payload = data
    if data["index"] == len(data["blocks"]):
        row.finished_at = now
        db.flush()
        frozen_summary = summary(db, catalog, user, row, enrollment, now)
        row.payload = {**data, "summary": frozen_summary}
        record_event(db, user.id, "learning.session_completed", row.id)


def summary(
    db: Session,
    catalog: Catalog,
    user: User,
    row: LearningSession,
    enrollment: Enrollment,
    now: int,
) -> dict:
    data = row.payload
    evidence = [
        e
        for e in db.scalars(
            select(Evidence)
            .where(
                Evidence.enrollment_id == enrollment.id,
                Evidence.created_at >= row.created_at,
                Evidence.created_at <= (row.finished_at or now),
            )
            .order_by(Evidence.created_at, Evidence.seq, Evidence.id)
        )
        if e.details.get("session_id") == row.id
    ]
    independent = [e for e in evidence if e.kind == "code" and e.score == 1 and e.assistance == 0]
    assisted = [e for e in evidence if e.kind == "code" and e.score == 1 and e.assistance > 0]
    states = learn.states_for(db, enrollment)
    changes = []
    for concept in dict.fromkeys(e.concept for e in evidence):
        before = ConceptState.from_dict(data["before"].get(concept))
        after = states.get(concept, before)
        changes.append(
            dict(
                concept=concept,
                title=catalog.concept(concept).title,
                before=band(before, row.created_at),
                after=band(after, now),
                evidence=sum(e.concept == concept for e in evidence),
            )
        )
    changed = any(c["before"] != c["after"] for c in changes)
    plan = learn.plan_for(db, catalog, user, enrollment, now, record=False)
    next_item = next((a for a in plan.queue if a.concept != data["concept"]), None)
    next_day = learn.local_day(user, now) + timedelta(days=1)
    while next_day.weekday() not in enrollment.weekdays:
        next_day += timedelta(days=1)
    return dict(
        done=[
            o["title"]
            for o in data["outcomes"]
            if o["kind"] in {"problem", "review"}
            or o.get("atom_kind") in {"faded", "trace", "predict", "debug", "explanation"}
        ][:3],
        independent_solves=len(independent),
        assisted_solves=len(assisted),
        evidence=len(evidence),
        evidence_ids=[e.id for e in evidence],
        changes=changes,
        message="Your evidence changed a skill state."
        if changed
        else "Evidence gained, no band change yet."
        if evidence
        else "Evidence is still building; reading alone does not change mastery.",
        next=dict(
            date=next_day.isoformat(),
            minutes=enrollment.minutes_per_day,
            title=data.get("next_focus")
            or (
                next_item.title
                if next_item
                else "A spaced recall check and a fresh practice problem."
            ),
        ),
    )


def view(
    db: Session,
    catalog: Catalog,
    user: User,
    row: LearningSession,
    enrollment: Enrollment,
    now: int,
) -> dict:
    data = row.payload
    blocks = [{k: v for k, v in b.items() if k not in {"atom"}} for b in data["blocks"]]
    index = data["index"]
    block = copy.deepcopy(blocks[index]) if index < len(blocks) else None
    if block and data["blocks"][index]["kind"] == "atom":
        ensure_content(catalog, data["blocks"][index])
        atom = data["blocks"][index]["atom"]
        block["atom"] = {k: atom[k] for k in ("id", "kind", "objective", "body", "why")}
        adapter = atom["adapters"].get(data["language"])
        block["atom"].update(
            code=adapter["code"] if adapter else None,
            language_available=not atom["adapters"] or adapter is not None,
        )
        if atom["steps"]:
            step = atom["steps"][data["step"]]
            order = option_order(row.id, index, data["step"], len(step["options"]))
            block["atom"]["check"] = dict(
                state=step["state"],
                prompt=step["prompt"],
                options=[step["options"][i] for i in order],
                step=data["step"],
                total=len(atom["steps"]),
            )
    return dict(
        id=row.id,
        day=row.day,
        minutes=data["minutes"],
        recovery=data["recovery"],
        language=data["language"],
        concept=data["concept"],
        index=index,
        blocks=blocks,
        current=block,
        feedback=data["feedback"],
        finished=row.finished_at is not None,
        summary=data.get("summary") if row.finished_at else None,
    )


def counts_as_evidence(block: dict) -> bool:
    """Pattern atoms count only once their pack is released (human-reviewed)."""
    return not block.get("pattern") or block.get("status") == "released"


def ensure_content(catalog: Catalog, block: dict):
    if block["kind"] == "atom" and block.get("pattern"):
        pattern_pack = catalog.pattern_atoms.get(block["pattern"])
        if pattern_pack is None or pattern_pack.status == "quarantined":
            raise HTTPException(423, "content_quarantined")
    elif block["kind"] == "atom":
        pack = catalog.atom_packs.get(block["concept"])
        if pack is None or pack.status == "quarantined":
            raise HTTPException(423, "content_quarantined")
