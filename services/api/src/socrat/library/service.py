"""Library state for one learner: marks, linked accounts, listings and recommendations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import practice
from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.library import ladder, recommend
from socrat.models import Enrollment, LinkedAccount, PracticeMark, Submission, User

STATUSES = ("todo", "attempted", "solved")
MAX_VERIFIED_PER_SYNC = 10  # a burst of old solves must not swamp the mastery estimate


def marks_for(db: Session, user_id: str) -> dict[str, PracticeMark]:
    rows = db.scalars(select(PracticeMark).where(PracticeMark.user_id == user_id))
    return {m.problem_id: m for m in rows}


def account_for(db: Session, user_id: str) -> LinkedAccount | None:
    return db.get(LinkedAccount, (user_id, "codeforces"))


def native_solved(db: Session, user_id: str) -> set[str]:
    return set(
        db.scalars(
            select(Submission.problem_id).where(
                Submission.user_id == user_id,
                Submission.mode == "submit",
                Submission.verdict == "accepted",
            )
        )
    )


def learner_for(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment | None, now: int
) -> recommend.Learner:
    states = learn.states_for(db, enrollment) if enrollment else {}
    marks = marks_for(db, user.id)
    account = account_for(db, user.id)
    solved = {pid for pid, m in marks.items() if m.status == "solved"}
    attempted = {pid for pid, m in marks.items() if m.status == "attempted"}
    if account is not None:
        solved |= set(account.solved)
        attempted |= set(account.attempted)
    course = enrollment.course_id if enrollment else "dsa"
    return recommend.Learner(
        course=course,
        states=states,
        now=now,
        rating=ladder.estimate_rating(states, now, account.rating if account else None),
        solved=solved,
        attempted=attempted - solved,
        seed=f"{user.id}:{learn.local_day(user, now).isoformat()}",
        course_concepts=set(catalog.closure(catalog.course_concepts(course))),
        native_solved=native_solved(db, user.id),
    )


def concept_ref(catalog: Catalog, learner: recommend.Learner, concept: str | None) -> dict | None:
    if not concept or concept not in catalog.concepts:
        return None
    return dict(id=concept, title=catalog.concept(concept).title, band=learner.band(concept))


def row(catalog: Catalog, learner: recommend.Learner, problem: dict, marks: dict) -> dict:
    mark = marks.get(problem["id"])
    status = mark.status if mark else None
    if problem["id"] in learner.solved:
        status = "solved"
    elif status is None and problem["id"] in learner.attempted:
        status = "attempted"
    return dict(
        practice.public(problem),
        status=status,
        bookmarked=bool(mark and mark.bookmarked),
        concept=concept_ref(
            catalog, learner, problem["concepts"][0] if problem["concepts"] else None
        ),
    )


def listing(
    db: Session,
    catalog: Catalog,
    user: User,
    now: int,
    *,
    q: str,
    platforms: tuple[str, ...],
    concept: str,
    difficulty: str,
    rating_min: int,
    rating_max: int,
    sheet: str,
    status: str,
    sort: str,
    offset: int,
    limit: int,
) -> dict:
    index = practice.default_index()
    enrollment = learn.active_enrollment(db, user.id)
    learner = learner_for(db, catalog, user, enrollment, now)
    marks = marks_for(db, user.id)
    ids: set[str] | None = None
    if status == "bookmarked":
        ids = {pid for pid, m in marks.items() if m.bookmarked}
    elif status == "solved":
        ids = set(learner.solved)
    elif status == "attempted":
        ids = set(learner.attempted)
    elif status == "todo":
        ids = {pid for pid, m in marks.items() if m.status == "todo"}
    items = index.search(q, platforms, concept, difficulty, rating_min, rating_max, sheet, ids)
    if status == "unsolved":
        items = [p for p in items if p["id"] not in learner.solved]
    if sort == "recommended":

        def fit(p: dict) -> float:
            primary = concept or (p["concepts"][0] if p["concepts"] else "")
            value = recommend.score(learner, p, primary)
            return -(value if value is not None else -1.0)

        items.sort(key=lambda p: (fit(p), p["id"]))
    elif sort == "easiest":
        items.sort(key=lambda p: (practice.rating_of(p), p["id"]))
    elif sort == "hardest":
        items.sort(key=lambda p: (-practice.rating_of(p), p["id"]))
    elif sort == "popular":
        items.sort(key=lambda p: (-p.get("companies", 0), -p.get("solvers", 0), p["id"]))
    else:
        items.sort(key=lambda p: (p["title"].lower(), p["id"]))
    offset = max(0, offset)
    page = items[offset : offset + max(1, min(limit, 100))]
    return {
        "total": len(items),
        "items": [row(catalog, learner, p, marks) for p in page],
        "level": recommend.level_view(learner.rating),
    }


def meta(catalog: Catalog) -> dict:
    index = practice.default_index()
    platforms: dict[str, int] = {}
    sheets: dict[str, int] = {}
    for p in index.problems.values():
        platforms[p["platform"]] = platforms.get(p["platform"], 0) + 1
        for sheet in p["sheets"]:
            sheets[sheet] = sheets.get(sheet, 0) + 1
    concepts = []
    for course_id in catalog.courses:
        for concept in catalog.course_concepts(course_id):
            if concept.startswith(f"{course_id}:") and index.by_concept.get(concept):
                concepts.append(
                    dict(
                        id=concept,
                        title=catalog.concept(concept).title,
                        course=catalog.course(course_id).title,
                        problems=len(index.by_concept[concept]),
                    )
                )
    return {"platforms": platforms, "sheets": sheets, "concepts": concepts}


def recommendations(db: Session, catalog: Catalog, user: User, now: int, limit: int = 6) -> dict:
    index = practice.default_index()
    enrollment = learn.active_enrollment(db, user.id)
    learner = learner_for(db, catalog, user, enrollment, now)
    plan = learn.plan_for(db, catalog, user, enrollment, now) if enrollment else None
    account = account_for(db, user.id)
    return {
        "level": recommend.level_view(learner.rating),
        "problems": recommend.next_problems(index, catalog, learner, plan, limit),
        "topics": recommend.next_topics(catalog, learner, plan),
        "solved_external": len(learner.solved),
        "codeforces": account_view(account),
    }


def mark(
    db: Session,
    catalog: Catalog,
    user: User,
    problem_id: str,
    now: int,
    status: str | None = None,
    bookmarked: bool | None = None,
    opened: bool = False,
) -> dict:
    index = practice.default_index()
    problem = index.problems[problem_id]
    row_ = db.get(PracticeMark, (user.id, problem_id))
    if row_ is None:
        row_ = PracticeMark(user_id=user.id, problem_id=problem_id, status="todo", bookmarked=False)
        db.add(row_)
    newly_solved = status == "solved" and row_.status != "solved"
    if opened:
        row_.opened_at = now
        if row_.status == "todo" and status is None:
            row_.status = "attempted"
    if status is not None:
        row_.status = status
        row_.solved_at = now if status == "solved" else None
    if bookmarked is not None:
        row_.bookmarked = bookmarked
    row_.updated_at = now
    enrollment = learn.active_enrollment(db, user.id)
    if newly_solved and enrollment is not None:
        primary = problem["concepts"][0] if problem["concepts"] else None
        if primary in catalog.concepts:
            learn.record_evidence(
                db, enrollment, primary, "external", 1.0, f"external:{problem_id}", now
            )
        learn.bump_daily(db, user, now, solved=1)
    return {"id": problem_id, "status": row_.status, "bookmarked": row_.bookmarked}


def account_view(account: LinkedAccount | None) -> dict | None:
    if account is None:
        return None
    weak = sorted(
        (
            (tag, s["solved"], s["unsolved"])
            for tag, s in account.tag_stats.items()
            if s["unsolved"] >= 2 and not tag.startswith("*")
        ),
        key=lambda x: (x[2] / (x[1] + x[2]), x[2]),
        reverse=True,
    )
    return {
        "handle": account.handle,
        "rating": account.rating,
        "max_rating": account.max_rating,
        "rank": account.rank,
        "solved": len(account.solved),
        "attempted": len(account.attempted),
        "weak_tags": [t for t, _, _ in weak[:5]],
        "synced_at": account.synced_at,
        "sync_error": account.sync_error,
    }


def apply_profile(
    db: Session, catalog: Catalog, user: User, profile: dict, now: int
) -> LinkedAccount:
    account = account_for(db, user.id)
    first = account is None or account.handle.lower() != profile["handle"].lower()
    previous = set() if first or account is None else set(account.solved)
    if account is None:
        account = LinkedAccount(user_id=user.id, platform="codeforces", created_at=now)
        db.add(account)
    account.handle = profile["handle"]
    account.rating = profile["rating"]
    account.max_rating = profile["max_rating"]
    account.rank = profile["rank"]
    account.solved = profile["solved"]
    account.attempted = profile["attempted"]
    account.tag_stats = profile["tag_stats"]
    account.synced_at = now
    account.sync_error = ""
    enrollment = learn.active_enrollment(db, user.id)
    if not first and enrollment is not None:
        # New accepted solutions since the last sync count as verified practice.
        index = practice.default_index()
        fresh = [p for p in profile["solved"] if p not in previous and p in index.problems]
        for problem_id in fresh[:MAX_VERIFIED_PER_SYNC]:
            concepts = index.problems[problem_id]["concepts"]
            if concepts and concepts[0] in catalog.concepts:
                learn.record_evidence(
                    db, enrollment, concepts[0], "verified", 1.0, f"external:{problem_id}", now
                )
    return account


def concept_practice(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment | None,
    concept: str,
    now: int,
    curated: list[str] | None = None,
) -> list[dict]:
    """Personalised "practice more" list for a lesson page; authored picks come first."""
    index = practice.default_index()
    learner = learner_for(db, catalog, user, enrollment, now)
    marks = marks_for(db, user.id)
    authored = [p for p in (index.find_url(u) for u in curated or []) if p is not None]
    taken = {p["id"] for p in authored}
    ranked = recommend.best_for(index, learner, concept, 8 + len(taken))
    picks = authored + [p for p in ranked if p["id"] not in taken][: max(0, 8 - len(authored))]
    if len(picks) < 8:  # widen beyond the ideal window rather than show nothing
        extra = sorted(
            (
                index.problems[i]
                for i in index.by_concept.get(concept, [])
                if i not in {p["id"] for p in picks} and i not in learner.solved
            ),
            key=lambda p: abs(practice.rating_of(p) - recommend.window(learner, concept)[0]),
        )
        picks += extra[: 8 - len(picks)]
    return [row(catalog, learner, p, marks) for p in picks]
