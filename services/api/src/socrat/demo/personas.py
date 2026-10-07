"""Create labelled sample histories using normal services and actual Docker results.

Run once by the demo bootstrap container. No synthetic execution callbacks or
hand-written mastery projections are used. All dates are sample historical dates.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.assessment import service as assessments
from socrat.clock import demo_offset, now, offset_for
from socrat.config import Settings
from socrat.database import make_engine, record_event
from socrat.diagnostics import service as diagnostics
from socrat.execution import service as execution
from socrat.execution.protocol import JobEnvelope, ResultEnvelope, RuntimeProfile
from socrat.learnerstate.policy import digest
from socrat.learnerstate.service import project, promote_policy
from socrat.learning import service as learning
from socrat.learning.contracts import SessionAction
from socrat.models import (
    CodeAttempt,
    CodeDraft,
    ExecutionWorker,
    LearnerGoal,
    LearningSession,
    SkillPackHead,
    SkillPackVersion,
    User,
    identifier,
)
from socrat.onboarding.policy import GoalInput, route
from socrat.planning import service as planning
from socrat.planning.contracts import PlanCommand
from socrat.skillpacks.service import load


def bootstrap(settings: Settings):
    if not settings.demo_mode or settings.environment != "development":
        raise ValueError("Sample histories require development demo mode")
    from runner.backend import make_backend
    from runner.worker import execute

    profiles = [RuntimeProfile.model_validate(x) for x in settings.execution_profiles]
    backend = make_backend(settings)
    backend.preflight()
    engine = make_engine(settings.database_url_value)
    token = demo_offset.set(offset_for(engine))
    current = now()
    worker_id = "demo-bootstrap"
    try:
        with Session(engine) as db, db.begin():
            db.info["execution_settings"] = settings
            heads = list(db.scalars(select(SkillPackHead)))
            records = [db.get(SkillPackVersion, head.active_id) for head in heads if head.active_id]
            record = next(
                x
                for x in records
                if x is not None
                and x.payload["title"].startswith("Socrat original sample curriculum")
            )
            pack = load(record)
            for persona, track, language in (
                ("beginner", "foundations", "python"),
                ("interview", "interview", "java"),
                ("competitive", "competitive", "cpp"),
            ):
                if hasattr(backend, "available_images") and not any(
                    p.language == language and p.image in backend.available_images()
                    for p in profiles
                ):
                    print(
                        f"Sample history skipped for {persona}: toolchain not installed", flush=True
                    )
                    continue
                user = db.scalar(
                    select(User).where(
                        User.subject == "demo-" + persona, User.issuer == "local-development"
                    )
                )
                if user is None:
                    raise ValueError("Seed the demo content and users before histories")
                if db.scalar(select(LearnerGoal.id).where(LearnerGoal.user_id == user.id)):
                    continue
                stamp = current - (4 * 86400 if persona != "beginner" else 0)
                goal_input = GoalInput.model_validate(
                    dict(
                        goal_template_id=track,
                        language=language,
                        target_outcome={
                            "foundations": "programming_readiness",
                            "interview": "screen_readiness",
                            "competitive": "rating_band",
                        }[track],
                        target_date="no_fixed_date",
                        days_per_week=6,
                        minutes_per_session=30 if persona == "beginner" else 60,
                        timezone=user.timezone,
                        language_experience="none" if persona == "beginner" else "professional",
                        dsa_experience="never" if persona == "beginner" else "comfortable",
                        role_level="new_grad" if track == "interview" else None,
                        platform_or_format="codeforces" if track == "competitive" else None,
                        target_value="1200" if track == "competitive" else None,
                    )
                )
                snapshot = route(
                    goal_input,
                    True,
                    [pack],
                    datetime.fromtimestamp(stamp, ZoneInfo(user.timezone)).date(),
                )
                goal = LearnerGoal(
                    user_id=user.id,
                    idempotency_key="sample-history",
                    review_digest=digest({"user_id": user.id, "snapshot": snapshot}),
                    snapshot=snapshot,
                    confirmation_at=stamp,
                )
                db.add(goal)
                db.flush()
                record_event(db, user.id, "goal.created", goal.id)
                record_event(db, user.id, "route.confirmed", goal.id)
                promote_policy(
                    db,
                    user.id,
                    user.id,
                    "1.1.0",
                    stamp,
                    "Development sample history, not release approval",
                    digest(project(db, user.id, "1.1.0", stamp)),
                )
                diagnostic = diagnostics.create_diagnostic(db, goal, stamp)
                definition = next(
                    x for x in pack.diagnostics if x.blueprint_id == diagnostic.blueprint_id
                )
                while (view := diagnostics.public_view(db, diagnostic, stamp))["item"]:
                    item = view["item"]
                    spec = next(
                        x.response for x in definition.items if x.exercise_id == item["exercise_id"]
                    )
                    answer = spec.answer if persona != "beginner" else "other"
                    diagnostics.respond(
                        db,
                        diagnostic,
                        dict(
                            attempt_id=item["attempt_id"],
                            revision=diagnostic.revision,
                            idempotency_key=identifier(),
                            answer=answer,
                            report_problem=False,
                        ),
                        stamp,
                    )
                diagnostics.complete(db, diagnostic, stamp)
                baseline = assessments.start(
                    db, goal, dict(kind="baseline", idempotency_key="sample-baseline"), stamp
                )
                form = baseline.snapshot["form"]
                for item in assessments.items_for(db, baseline):
                    spec = next(x for x in form["items"] if x["exercise_id"] == item.exercise_id)
                    assessments.respond(
                        db,
                        baseline,
                        dict(
                            item_id=item.id,
                            revision=baseline.revision,
                            idempotency_key=identifier(),
                            answer=spec["response"]["answer"] if persona != "beginner" else "0",
                            report_problem=False,
                        ),
                        stamp,
                    )
                assessments.complete(db, baseline, stamp)

                def plan(action, at, goal=goal, user=user):
                    worker = db.get(ExecutionWorker, worker_id)
                    if worker is None:
                        db.add(
                            ExecutionWorker(
                                id=worker_id, images=[p.image for p in profiles], seen_at=at
                            )
                        )
                    else:
                        worker.seen_at = at
                    db.flush()
                    prior = planning.current(db, goal) if action != "generate" else None
                    weekday = datetime.fromtimestamp(at, ZoneInfo(user.timezone)).weekday()
                    weekdays = sorted({weekday, *(i for i in range(7) if i != (weekday + 1) % 7)})
                    draft = planning.command(
                        db,
                        goal,
                        PlanCommand(
                            action=action,
                            expected_revision=prior["revision"] if prior else 0,
                            idempotency_key=identifier(),
                            weekdays=weekdays,
                        ),
                        at,
                    )
                    return planning.command(
                        db,
                        goal,
                        PlanCommand(
                            action="confirm",
                            expected_revision=draft["revision"],
                            reviewed_digest=draft["review_digest"],
                            idempotency_key=identifier(),
                        ),
                        at,
                    )

                plan("generate", stamp)
                if persona != "beginner":
                    for day in range(4):
                        at = stamp + day * 86400
                        if day:
                            plan("refresh", at)
                        started = learning.start(
                            db, goal, planning.current(db, goal)["revision"], settings, at
                        )
                        session = db.get(LearningSession, started["id"])
                        assert session is not None
                        while session.status != "completed":
                            visible = learning.view(db, session, at)
                            block = next(x for x in visible["blocks"] if x["status"] == "available")
                            extra = {}
                            if block["timed"] and "deadline_at" not in block:
                                learning.command(
                                    db,
                                    goal,
                                    session,
                                    SessionAction(
                                        action="start_timed",
                                        expected_revision=session.revision,
                                        idempotency_key=identifier(),
                                    ),
                                    at,
                                    settings,
                                )
                            if block["mode"] == "independent":
                                attempt = db.get(CodeAttempt, block["attempt_id"])
                                assert attempt is not None
                                draft = db.get(CodeDraft, attempt.id)
                                variant = pack.variant_for(attempt.exercise_id, language)
                                assert draft is not None and variant is not None
                                draft.source = variant.reference_solution
                                draft.revision += 1
                                db.flush()
                                registered_worker = db.get(ExecutionWorker, worker_id)
                                assert registered_worker is not None
                                registered_worker.seen_at = at
                                run = execution.enqueue(
                                    db,
                                    attempt,
                                    "submit",
                                    dict(
                                        idempotency_key=identifier(),
                                        draft_revision=draft.revision,
                                        stdin=None,
                                    ),
                                    settings,
                                    at,
                                    "demo-bootstrap",
                                )
                                job = JobEnvelope.model_validate(
                                    execution.claim(db, worker_id, settings, at)
                                )
                                result = execute(
                                    job,
                                    backend,
                                    settings.execution_signing_secret.get_secret_value(),
                                    at,
                                )
                                if result["result"]["operational_status"] != "healthy" or any(
                                    x["status"] != "passed" for x in result["result"]["cases"]
                                ):
                                    raise ValueError(
                                        "Actual sample-history code failed: " + attempt.exercise_id
                                    )
                                execution.finalize(
                                    db,
                                    worker_id,
                                    ResultEnvelope.model_validate(result),
                                    settings,
                                    at,
                                )
                                extra["run_id"] = run.id
                            elif block["mode"] != "instruction":
                                lesson = next(
                                    x
                                    for x in pack.learning_lessons
                                    if x.id == block["lesson_ids"][0]
                                )
                                check = (
                                    lesson.retrieval_check
                                    if block["mode"] == "retrieval"
                                    else lesson.exit_check
                                )
                                extra["answer"] = (
                                    check.response.answer
                                    if block["mode"] != "guided"
                                    else "Trace the accumulator after every visited element and check the empty input."
                                )
                                if block["mode"] == "exit_check":
                                    extra["reflection"] = "none"
                            learning.command(
                                db,
                                goal,
                                session,
                                SessionAction(
                                    action="advance",
                                    expected_revision=session.revision,
                                    idempotency_key=identifier(),
                                    **extra,
                                ),
                                at,
                                settings,
                            )
                        print(f"Saved actual sample session: {persona}, day {day + 1}", flush=True)
                    plan("refresh", current)
                print(f"Sample persona ready: {persona}", flush=True)
    finally:
        demo_offset.reset(token)
        engine.dispose()


if __name__ == "__main__":
    bootstrap(Settings())
