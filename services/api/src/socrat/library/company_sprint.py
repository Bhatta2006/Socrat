"""Company sprints: "Amazon SDE-1 in 6 weeks" on top of the adaptive roadmap and company bank.

A sprint reads one company's question bank, weighs each Socrat skill by how often that
company asks questions that use it, and lays the skills the learner still needs (with their
prerequisites, in teaching order) across the weeks. Each week also gets that company's most
asked questions for the skills learned so far; the last week of a sprint of three or more
weeks is kept for mixed review of the company's questions.

Starting a sprint changes nothing in the roadmap by itself. It files a goal proposal (target
date, role and the company's top skills as focus) that the learner accepts or declines, like
every other roadmap change. The weekly plan is frozen at the start; progress is live.
"""

from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.adaptive import proposals
from socrat.adaptive.suggest import Draft
from socrat.catalog import practice
from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.library import service as library
from socrat.mastery.model import ConceptState, band
from socrat.models import CompanySprint, Enrollment, User

WEEKS = (4, 6, 8)
ROLES = {"intern": "internship", "sde1": "new-grad", "sde2": "mid-level", "senior": "senior"}
ROLE_LABEL = {"intern": "Intern", "sde1": "SDE-1", "sde2": "SDE-2", "senior": "Senior SDE"}
QUESTIONS_PER_WEEK = 6
MIN_QUESTIONS = 15  # companies with fewer mapped questions are not offered
DONE_BANDS = {"strong", "likely_known"}


def weights(catalog: Catalog, entry: dict, scope: set[str]) -> dict[str, float]:
    """Skill -> summed frequency of the company's questions that use it (in this course)."""
    index = practice.default_index()
    out: dict[str, float] = {}
    for problem_id, frequency, _ in entry["problems"]:
        problem = index.problems.get(problem_id)
        if problem is None:
            continue
        for concept in problem["concepts"]:
            if concept in scope and concept in catalog.concepts:
                out[concept] = out.get(concept, 0.0) + max(float(frequency), 1.0)
    return out


def companies(catalog: Catalog, scope: set[str], q: str = "", limit: int = 40) -> list[dict]:
    index = practice.default_index()
    needle = q.strip().lower()
    items = []
    for slug, entry in index.companies.items():
        if needle and needle not in entry["name"].lower():
            continue
        mapped = sum(
            1
            for problem_id, _, _ in entry["problems"]
            if (p := index.problems.get(problem_id))
            and p["concepts"]
            and set(p["concepts"]) <= scope
        )
        if mapped >= MIN_QUESTIONS:
            items.append(dict(slug=slug, name=entry["name"], questions=mapped))
    items.sort(key=lambda c: (-c["questions"], c["name"]))
    return items[:limit]


def build(
    catalog: Catalog,
    entry: dict,
    scope: set[str],
    states: dict[str, ConceptState],
    ready: set[str],
    weeks: int,
    stamp: int,
) -> dict:
    """The frozen weekly plan: skills to finish and question ids per week."""
    weight = weights(catalog, entry, scope)
    if not weight:
        raise HTTPException(409, "company_not_covered")
    # Skills that carry real weight for this company, then everything they depend on.
    total = sum(weight.values())
    ranked = sorted(weight, key=lambda c: (-weight[c], c))
    targets = [c for c in ranked if weight[c] / total >= 0.01][:24] or ranked[:8]
    ordered = [c for c in catalog.closure(targets) if c in scope]

    def done(concept: str) -> bool:
        return concept in ready or band(states.get(concept, ConceptState()), stamp) in DONE_BANDS

    todo = [c for c in ordered if not done(c)]
    study_weeks = weeks - 1 if weeks >= 3 else weeks
    per_week = max(1, -(-len(todo) // study_weeks)) if todo else 0
    plan_weeks: list[dict] = []
    known = {c for c in ordered if done(c)}
    used: set[str] = set()
    index = practice.default_index()
    for number in range(weeks):
        new = todo[number * per_week : (number + 1) * per_week] if number < study_weeks else []
        known |= set(new)
        questions = []
        for problem_id, _, _ in entry["problems"]:  # most frequent first
            problem = index.problems.get(problem_id)
            if (
                problem is None
                or problem_id in used
                or not problem["concepts"]
                or not set(problem["concepts"]) <= known
            ):
                continue
            questions.append(problem_id)
            used.add(problem_id)
            if len(questions) == QUESTIONS_PER_WEEK + (2 if not new else 0):
                break
        plan_weeks.append(dict(number=number + 1, concepts=new, questions=questions))
    return dict(
        weeks=plan_weeks,
        already=[c for c in ordered if c not in todo],
        focus=[c for c in ranked if c in todo][: proposals.MAX_PRIORITY],
    )


def active(db: Session, enrollment: Enrollment) -> CompanySprint | None:
    return db.scalar(
        select(CompanySprint)
        .where(CompanySprint.enrollment_id == enrollment.id, CompanySprint.finished_at.is_(None))
        .order_by(CompanySprint.created_at.desc())
    )


def start(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    slug: str,
    role: str,
    weeks: int,
    stamp: int,
) -> CompanySprint:
    index = practice.default_index()
    entry = index.companies.get(slug)
    if entry is None:
        raise HTTPException(404, "not_found")
    scope = learn.curriculum(catalog, enrollment)
    states = learn.states_for(db, enrollment)
    ready = learn.practice_topics(db, catalog, enrollment, stamp)
    plan = build(catalog, entry, scope, states, ready, weeks, stamp)
    running = active(db, enrollment)
    if running is not None:
        running.finished_at = stamp
    today = learn.local_day(user, stamp)
    ends = today + timedelta(days=7 * weeks - 1)
    sprint = CompanySprint(
        enrollment_id=enrollment.id,
        company=slug,
        company_name=entry["name"],
        role=role,
        weeks=weeks,
        started_on=today.isoformat(),
        ends_on=ends.isoformat(),
        plan=plan,
        created_at=stamp,
    )
    db.add(sprint)
    db.flush()
    title = f"{entry['name']} {ROLE_LABEL[role]} in {weeks} weeks"
    focus_titles = ", ".join(catalog.concept(c).title for c in plan["focus"])
    draft = Draft(
        kind="goal",
        key=f"company-sprint:{sprint.id}",
        group="",
        title=f"Aim your plan at {title}",
        reason=(
            f"Sets your target date to {ends.strftime('%d %b %Y')} and your role to "
            f"{ROLE_LABEL[role]}"
            + (
                f", and moves {focus_titles} up: {entry['name']} asks about them most."
                if focus_titles
                else "."
            )
        ),
        payload=proposals.validate(
            catalog,
            enrollment,
            "goal",
            dict(target_role=ROLES[role], target_date=ends.isoformat(), focus=plan["focus"]),
        ),
    )
    proposal = proposals.add(db, enrollment, draft, "company_sprint", stamp)
    sprint.proposal_id = proposal.id if proposal else None
    return sprint


def view(db: Session, catalog: Catalog, user: User, sprint: CompanySprint, stamp: int) -> dict:
    enrollment = db.get(Enrollment, sprint.enrollment_id)
    if enrollment is None:  # the sprint row cascades with its enrollment
        raise HTTPException(404, "not_found")
    states = learn.states_for(db, enrollment)
    learner = library.learner_for(db, catalog, user, enrollment, stamp)
    ready = learner.ready_concepts or set()
    index = practice.default_index()
    today = learn.local_day(user, stamp)
    started = date.fromisoformat(sprint.started_on)
    current = min(sprint.weeks, max(1, (today - started).days // 7 + 1))
    elapsed = min(1.0, max(0.0, ((today - started).days + 1) / (7 * sprint.weeks)))
    concepts_total = concepts_done = questions_total = questions_solved = 0
    weeks = []
    for week in sprint.plan["weeks"]:
        concepts = []
        for concept in week["concepts"]:
            if concept not in catalog.concepts:
                continue
            state = states.get(concept, ConceptState())
            finished = concept in ready or band(state, stamp) in DONE_BANDS
            concepts_total += 1
            concepts_done += finished
            concepts.append(
                dict(
                    id=concept,
                    title=catalog.concept(concept).title,
                    band=band(state, stamp),
                    done=finished,
                )
            )
        questions = []
        hidden = 0
        for problem_id in week["questions"]:
            problem = index.problems.get(problem_id)
            if problem is None:
                continue
            questions_total += 1
            solved = problem_id in learner.solved
            questions_solved += solved
            if not learner.can_practice(problem):
                hidden += 1  # the company bank only shows questions for finished skills
                continue
            questions.append(dict(practice.public(problem), solved=solved))
        start_day = started + timedelta(days=7 * (week["number"] - 1))
        weeks.append(
            dict(
                number=week["number"],
                starts=start_day.isoformat(),
                ends=(start_day + timedelta(days=6)).isoformat(),
                review=not week["concepts"],
                concepts=concepts,
                questions=questions,
                locked_questions=hidden,
            )
        )
    progress = (concepts_done + questions_solved) / max(1, concepts_total + questions_total)
    proposal = None
    if sprint.proposal_id:
        from socrat.models import PlanProposal

        row = db.get(PlanProposal, sprint.proposal_id)
        proposal = proposals.view(row) if row else None
    return dict(
        id=sprint.id,
        company=dict(slug=sprint.company, name=sprint.company_name),
        role=sprint.role,
        role_label=ROLE_LABEL.get(sprint.role, sprint.role),
        title=f"{sprint.company_name} {ROLE_LABEL.get(sprint.role, sprint.role)} in {sprint.weeks} weeks",
        weeks_total=sprint.weeks,
        started_on=sprint.started_on,
        ends_on=sprint.ends_on,
        current_week=current,
        finished=sprint.finished_at is not None or today > date.fromisoformat(sprint.ends_on),
        progress=round(progress, 3),
        on_track=progress + 0.1 >= elapsed,
        counts=dict(
            concepts=concepts_total,
            concepts_done=concepts_done,
            questions=questions_total,
            questions_solved=questions_solved,
            already_known=len(sprint.plan.get("already", [])),
        ),
        weeks=weeks,
        proposal=proposal,
    )


def stop(sprint: CompanySprint, stamp: int) -> None:
    if sprint.finished_at is None:
        sprint.finished_at = stamp
