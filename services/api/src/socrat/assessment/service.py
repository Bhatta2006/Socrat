"""Caller holds the learner lock. Answers, exposure, evidence and outbox commit together."""

from sqlalchemy import select

from socrat.assessment.contracts import AssessmentForm
from socrat.database import record_event
from socrat.diagnostics.scoring import score_response
from socrat.learnerstate.policy import POLICIES, SPACED_POLICY, digest
from socrat.learnerstate.projector import EvidenceFact, state_key
from socrat.learnerstate.service import append_fact, facts_for, project
from socrat.models import (
    AssessmentAnswer,
    AssessmentDispute,
    AssessmentItem,
    AssessmentResponse,
    AssessmentReview,
    AssessmentSession,
    CodeAttempt,
    DiagnosticAttempt,
    DiagnosticSession,
    LearnerState,
    SkillPackHead,
    SkillPackVersion,
    identifier,
)
from socrat.skillpacks.service import load


class AssessmentError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status


def content(db, session):
    record = db.get(SkillPackVersion, session.pack_id)
    if record:
        db.scalar(
            select(SkillPackHead).where(SkillPackHead.pack_key == record.pack_key).with_for_update()
        )
        db.refresh(record)
    if (
        record is None
        or record.status != "released"
        or record.digest != session.snapshot["pack_digest"]
    ):
        raise AssessmentError("assessment_content_unavailable", 503)
    return load(record)


def items_for(db, session):
    return list(
        db.scalars(
            select(AssessmentItem)
            .where(AssessmentItem.session_id == session.id)
            .order_by(AssessmentItem.position)
        )
    )


def spec_for(session, item):
    form = AssessmentForm.model_validate(session.snapshot["form"])
    return next(x for x in form.items if x.exercise_id == item.exercise_id)


def effective_response(db, item):
    response = db.get(AssessmentResponse, item.id)
    if response is None:
        return None
    reviews = list(
        db.scalars(
            select(AssessmentReview)
            .where(AssessmentReview.item_id == item.id)
            .order_by(AssessmentReview.created_at.desc(), AssessmentReview.id.desc())
        )
    )
    # A dispute resolution follows the original review even when both share the
    # same second. Random UUID ordering is not an ordering of human decisions.
    review = next(
        (x for x in reviews if x.outcome.get("dispute_resolution")), reviews[0] if reviews else None
    )
    return review.outcome if review else response.outcome


def near_boundary(score, form):
    return round(abs(score - form.pass_score), 12) <= form.boundary_margin


def pending_dispute(db, item):
    dispute = db.get(AssessmentDispute, item.id)
    resolved = any(
        x.outcome.get("dispute_resolution")
        for x in db.scalars(select(AssessmentReview).where(AssessmentReview.item_id == item.id))
    )
    return dispute if dispute and not resolved else None


def dispute(db, session, item, body, stamp):
    old = db.get(AssessmentDispute, item.id)
    if old:
        if old.request_digest != digest(body):
            raise AssessmentError("assessment_already_disputed")
        return public_view(db, session, stamp)
    if session.result is None or session.result["status"] != "scored":
        raise AssessmentError("finalized_assessment_required")
    db.add(
        AssessmentDispute(
            item_id=item.id,
            idempotency_key=body["idempotency_key"],
            request_digest=digest(body),
            rationale=body["rationale"],
            created_at=stamp,
        )
    )
    session.revision += 1
    db.flush()
    record_event(db, session.user_id, "assessment.disputed", item.id)
    return public_view(db, session, stamp)


def exposed_families(db, user_id, pack_key, language):
    # Issuance counts even when the learner never submits, reports an item, or changes pack version.
    pack_ids = set(
        db.scalars(select(SkillPackVersion.id).where(SkillPackVersion.pack_key == pack_key))
    )
    families = {f.family_id for f in facts_for(db, user_id) if f.pack_id in pack_ids}
    for session in db.scalars(
        select(AssessmentSession).where(
            AssessmentSession.user_id == user_id, AssessmentSession.pack_id.in_(pack_ids)
        )
    ):
        families.update(x.family_id for x in items_for(db, session))
    exercise_ids = set()
    for attempt in db.scalars(
        select(CodeAttempt).where(CodeAttempt.user_id == user_id, CodeAttempt.pack_id.in_(pack_ids))
    ):
        exercise_ids.add((attempt.pack_id, attempt.exercise_id))
    for diagnostic in db.scalars(
        select(DiagnosticSession).where(
            DiagnosticSession.user_id == user_id, DiagnosticSession.pack_id.in_(pack_ids)
        )
    ):
        exercise_ids.update(
            (diagnostic.pack_id, x.exercise_id)
            for x in db.scalars(
                select(DiagnosticAttempt).where(DiagnosticAttempt.diagnostic_id == diagnostic.id)
            )
        )
    for pack_id, exercise_id in exercise_ids:
        pack = load(db.get(SkillPackVersion, pack_id))
        families.update(x.family_id for x in pack.exercises if x.id == exercise_id)
    return families


def retention_due(db, goal, stamp):
    state = db.get(LearnerState, goal.user_id)
    if state is None or state.active_policy != "1.1.0":
        return []
    projection = project(db, goal.user_id, state.active_policy if state else "1.0.0", stamp)
    pins = {(x["key"], x["version"]) for x in goal.snapshot["pack_versions"]}
    language = goal.snapshot["goal"]["language"]
    result = []
    for record in db.scalars(select(SkillPackVersion)):
        if (record.pack_key, record.version) not in pins or record.status != "released":
            continue
        pack = load(record)
        overlay = next(x for x in pack.tracks if x.id == goal.snapshot["active_track"])
        for concept in overlay.concept_ids:
            value = projection["concepts"].get(state_key(record.id, language, concept), {})
            if value.get("due_at") is not None and stamp >= value["due_at"]:
                result.append(
                    dict(
                        pack_id=record.id,
                        concept_id=concept,
                        due_at=value["due_at"],
                        representation=value.get("review_representation", "retention_assessment"),
                        repair_required=value.get("repair_required", False),
                        failing_prerequisite=any(
                            edge.prerequisite == concept for edge in pack.edges
                        )
                        and value.get("effective_mastery", 0) < 0.6,
                    )
                )
    return sorted(result, key=lambda x: (x["due_at"], x["concept_id"]))


def start(db, goal, body, stamp):
    request_digest = digest(dict(goal_id=goal.id, **body))
    previous = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.user_id == goal.user_id,
            AssessmentSession.idempotency_key == body["idempotency_key"],
        )
    )
    if previous:
        if previous.request_digest != request_digest:
            raise AssessmentError("idempotency_key_reused")
        return previous
    if not goal.snapshot["routing_outcome"].startswith("accept_"):
        raise AssessmentError("accepted_goal_required", 422)
    active = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.goal_id == goal.id,
            AssessmentSession.result.is_(None),
            AssessmentSession.deadline_at > stamp,
        )
    )
    if active:
        raise AssessmentError("assessment_already_active")
    language = goal.snapshot["goal"]["language"]
    kind = body["kind"]
    completed = list(
        db.scalars(
            select(AssessmentSession).where(
                AssessmentSession.goal_id == goal.id, AssessmentSession.status == "completed"
            )
        )
    )
    if kind != "baseline" and not any(x.snapshot["kind"] == "baseline" for x in completed):
        raise AssessmentError("baseline_required")
    if kind == "baseline" and any(x.snapshot["kind"] == "baseline" for x in completed):
        raise AssessmentError("baseline_already_completed")
    if kind == "weekly" and any(
        x.snapshot["kind"] == "weekly" and stamp < x.result["completed_at"] + 7 * 86400
        for x in completed
    ):
        raise AssessmentError("weekly_not_due")
    due = retention_due(db, goal, stamp) if kind == "retention" else []
    state = db.get(LearnerState, goal.user_id)
    if kind == "retention" and (state is None or state.active_policy != "1.1.0"):
        raise AssessmentError("retention_policy_review_required")
    if kind == "retention" and not due:
        raise AssessmentError("retention_not_due")
    candidates = []
    for pin in sorted(goal.snapshot["pack_versions"], key=lambda x: x["key"]):
        db.scalar(
            select(SkillPackHead).where(SkillPackHead.pack_key == pin["key"]).with_for_update()
        )
        record = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == pin["key"], SkillPackVersion.version == pin["version"]
            )
        )
        if record is None or record.status != "released":
            continue
        pack = load(record)
        exposures = exposed_families(db, goal.user_id, record.pack_key, language)
        exercises = {x.id: x for x in pack.exercises}
        for form in pack.assessment_forms:
            blueprint = next(x for x in pack.blueprints if x.id == form.blueprint_id)
            if (
                blueprint.kind != kind
                or form.track != goal.snapshot["active_track"]
                or (pack.languages and language not in form.languages)
            ):
                continue
            if any(exercises[x.exercise_id].family_id in exposures for x in form.items):
                continue
            if kind == "retention" and not set(blueprint.concept_ids) <= {
                x["concept_id"] for x in due if x["pack_id"] == record.id
            }:
                continue
            if kind == "retention":
                relevant = [
                    x
                    for x in due
                    if x["pack_id"] == record.id and x["concept_id"] in blueprint.concept_ids
                ]
                if any(x["representation"] != form.retention_representation for x in relevant):
                    continue
                budget = (
                    goal.snapshot["goal"]["minutes_per_session"]
                    * SPACED_POLICY["ordinary_session_review_fraction"]
                )
                if (
                    not any(x["failing_prerequisite"] for x in relevant)
                    and sum(exercises[x.exercise_id].estimated_minutes for x in form.items) > budget
                ):
                    continue
            candidates.append((form.blueprint_id, record, pack, form))
    if not candidates:
        raise AssessmentError("fresh_assessment_form_unavailable", 503)
    _, record, pack, form = sorted(candidates, key=lambda x: (x[0], x[1].pack_key))[0]
    allotted_seconds = form.maximum_seconds
    if kind == "retention":
        relevant = [
            x
            for x in due
            if x["pack_id"] == record.id
            and x["concept_id"]
            in next(b.concept_ids for b in pack.blueprints if b.id == form.blueprint_id)
        ]
        if not any(x["failing_prerequisite"] for x in relevant):
            allotted_seconds = min(
                allotted_seconds,
                int(
                    goal.snapshot["goal"]["minutes_per_session"]
                    * SPACED_POLICY["ordinary_session_review_fraction"]
                    * 60
                ),
            )
    state = db.get(LearnerState, goal.user_id)
    session = AssessmentSession(
        user_id=goal.user_id,
        goal_id=goal.id,
        pack_id=record.id,
        idempotency_key=body["idempotency_key"],
        request_digest=request_digest,
        snapshot=dict(
            kind=kind,
            language=language,
            track=goal.snapshot["declared_track"],
            pack_digest=record.digest,
            form=form.model_dump(),
            policy_version=state.active_policy if state else "1.0.0",
            allotted_seconds=allotted_seconds,
        ),
        status="in_progress",
        revision=0,
        started_at=stamp,
        deadline_at=stamp + allotted_seconds,
    )
    db.add(session)
    db.flush()
    for position, spec in enumerate(form.items):
        exercise = next(x for x in pack.exercises if x.id == spec.exercise_id)
        db.add(
            AssessmentItem(
                session_id=session.id,
                exercise_id=exercise.id,
                family_id=exercise.family_id,
                position=position,
                issued_at=stamp,
            )
        )
    db.flush()
    record_event(db, goal.user_id, "assessment.started", session.id)
    return session


def public_view(db, session, stamp):
    pack = content(db, session)
    result = session.result
    if result is not None:
        sources = {x.id for x in items_for(db, session)}
        facts = facts_for(db, session.user_id)
        invalidated = {x.target_event_id for x in facts if x.kind == "invalidated"}
        result = {
            **result,
            "evidence_current": not any(
                x.source_id in sources and x.event_id in invalidated for x in facts
            ),
            "dispute_pending": any(pending_dispute(db, x) for x in items_for(db, session)),
        }
    rows = []
    for item in items_for(db, session):
        exercise = next(x for x in pack.exercises if x.id == item.exercise_id)
        response = effective_response(db, item)
        spec = spec_for(session, item)
        rows.append(
            dict(
                id=item.id,
                exercise_id=exercise.id,
                title=exercise.title,
                statement=exercise.statement,
                modality=exercise.modality,
                response_kind=spec.response.kind,
                choices=[x.model_dump() for x in spec.response.choices],
                rubric_criteria=spec.rubric_criteria,
                status=response["status"] if response else "available",
            )
        )
    return dict(
        id=session.id,
        kind=session.snapshot["kind"],
        revision=session.revision,
        status="expired" if result is None and stamp >= session.deadline_at else session.status,
        deadline_at=session.deadline_at,
        items=rows,
        result=result,
        independence="No tutor or solutions. Independently assessed in Socrat's environment.",
    )


def active(db, session, stamp):
    content(db, session)
    if (
        session.result is not None
        or stamp >= session.deadline_at
        or session.status != "in_progress"
    ):
        raise AssessmentError("assessment_not_active")


def store_response(db, session, item, key, request_digest, outcome, stamp, answer=None):
    db.add(
        AssessmentResponse(
            item_id=item.id,
            session_id=session.id,
            idempotency_key=key,
            request_digest=request_digest,
            outcome=outcome,
            created_at=stamp,
        )
    )
    if answer is not None:
        db.add(AssessmentAnswer(item_id=item.id, answer=answer))
    session.revision += 1
    db.flush()
    record_event(db, session.user_id, "assessment.item_completed", item.id)


def respond(db, session, body, stamp):
    old = db.scalar(
        select(AssessmentResponse).where(
            AssessmentResponse.session_id == session.id,
            AssessmentResponse.idempotency_key == body["idempotency_key"],
        )
    )
    if old:
        if old.request_digest != digest(body):
            raise AssessmentError("idempotency_key_reused")
        return public_view(db, session, stamp)
    active(db, session, stamp)
    item = db.get(AssessmentItem, body["item_id"])
    if item is None or item.session_id != session.id:
        raise AssessmentError("not_found", 404)
    if session.revision != body["revision"] or db.get(AssessmentResponse, item.id):
        raise AssessmentError("assessment_response_stale")
    spec = spec_for(session, item)
    if spec.response.kind == "implementation" and not body["report_problem"]:
        raise AssessmentError("verified_submit_required")
    if (
        spec.response.kind == "choice"
        and body["answer"] not in {x.id for x in spec.response.choices}
        and not body["report_problem"]
    ):
        raise AssessmentError("invalid_choice", 422)
    outcome = score_response(
        spec.response, body["answer"], False, body["report_problem"]
    ).model_dump()
    form = AssessmentForm.model_validate(session.snapshot["form"])
    if outcome["status"] == "scored" and near_boundary(outcome["score"], form):
        outcome.update(status="pending_review", reason_code="boundary_review_required")
    store_response(
        db, session, item, body["idempotency_key"], digest(body), outcome, stamp, body["answer"]
    )
    return public_view(db, session, stamp)


def complete(db, session, stamp):
    if session.result is not None:
        return public_view(db, session, stamp)
    pack = content(db, session)
    items = items_for(db, session)
    outcomes = [(x, effective_response(db, x)) for x in items]
    if any(value is None for _, value in outcomes):
        if stamp < session.deadline_at:
            raise AssessmentError("assessment_responses_pending")
        session.status = "expired"
        session.result = dict(
            status="unscored", reason_code="assessment_expired", completed_at=stamp
        )
        record_event(db, session.user_id, "assessment.expired", session.id)
        return public_view(db, session, stamp)
    if any(value["status"] == "pending_review" for _, value in outcomes):
        session.status = "pending_review"
        return public_view(db, session, stamp)
    # Incomplete/ambiguous forms are replaced as a whole; none of their scores affect mastery.
    if any(value["status"] == "excluded" for _, value in outcomes):
        session.status = "excluded"
        session.result = dict(
            status="unscored", reason_code="replacement_form_required", completed_at=stamp
        )
        record_event(db, session.user_id, "assessment.excluded", session.id)
        return public_view(db, session, stamp)
    form = AssessmentForm.model_validate(session.snapshot["form"])
    mean = sum(value["score"] for _, value in outcomes) / len(outcomes)
    reviewed = all(
        db.scalar(select(AssessmentReview).where(AssessmentReview.item_id == item.id))
        for item, _ in outcomes
    )
    if near_boundary(mean, form) and not reviewed:
        session.status = "pending_review"
        record_event(db, session.user_id, "assessment.boundary_review_required", session.id)
        return public_view(db, session, stamp)
    for item, outcome in outcomes:
        exercise = next(x for x in pack.exercises if x.id == item.exercise_id)
        version = session.snapshot["policy_version"]
        fact = EvidenceFact(
            event_id=identifier(),
            user_id=session.user_id,
            goal_id=session.goal_id,
            track=session.snapshot["track"],
            sequence=len(facts_for(db, session.user_id)) + 1,
            source_id=item.id,
            pack_id=session.pack_id,
            pack_digest=session.snapshot["pack_digest"],
            language=session.snapshot["language"],
            concept_ids=exercise.concept_ids,
            mode="retention" if session.snapshot["kind"] == "retention" else "assessment",
            evidence_type=exercise.evidence_mode,
            family_id=exercise.family_id,
            score=outcome["score"],
            quality=outcome["quality"],
            hint_level=0,
            elapsed_seconds=float(
                min(2700, db.get(AssessmentResponse, item.id).created_at - item.issued_at)
            ),
            expected_seconds=float(exercise.estimated_minutes * 60),
            difficulty=exercise.difficulty,
            valid=True,
            unseen=True,
            finalized=True,
            occurred_at=db.get(AssessmentResponse, item.id).created_at,
            scoring_version=outcome["scoring_version"],
            policy_version=version,
            policy_digest=digest(POLICIES[version].model_dump()),
            reason_code="assessment_finalized",
            review_group_id=session.id if session.snapshot["kind"] == "retention" else None,
        )
        append_fact(db, session.user_id, fact)
    session.status = "completed"
    session.result = dict(
        status="scored",
        score=mean,
        passed=mean >= form.pass_score,
        completed_at=stamp,
        form_digest=digest(session.snapshot["form"]),
        policy_version=session.snapshot["policy_version"],
    )
    session.revision += 1
    record_event(
        db,
        session.user_id,
        "retention.completed"
        if session.snapshot["kind"] == "retention"
        else "assessment.completed",
        session.id,
    )
    return public_view(db, session, stamp)


def review(db, session, item, actor, body, stamp):
    old = db.scalar(
        select(AssessmentReview).where(
            AssessmentReview.item_id == item.id,
            AssessmentReview.idempotency_key == body["idempotency_key"],
        )
    )
    if old:
        if old.request_digest != digest(body):
            raise AssessmentError("idempotency_key_reused")
        return public_view(db, session, stamp)
    content(db, session)
    if actor == session.user_id:
        raise AssessmentError("independent_reviewer_required", 403)
    response = db.get(AssessmentResponse, item.id)
    disputed = pending_dispute(db, item)
    if (
        (session.result is not None and not disputed)
        or response is None
        or session.revision != body["revision"]
    ):
        raise AssessmentError("assessment_review_stale")
    if not disputed and db.scalar(
        select(AssessmentReview).where(AssessmentReview.item_id == item.id)
    ):
        raise AssessmentError("assessment_already_reviewed")
    spec = spec_for(session, item)
    scores = body["criterion_scores"]
    if disputed:
        if scores:
            raise AssessmentError("dispute_requires_uphold_or_exclude", 422)
        outcome = {**effective_response(db, item), "dispute_resolution": True}
        if body["decision"] == "exclude":
            facts = facts_for(db, session.user_id)
            target = next(x for x in facts if x.source_id == item.id and x.kind == "scored")
            if not any(x.target_event_id == target.event_id for x in facts):
                state = db.get(LearnerState, session.user_id)
                version = state.active_policy if state else "1.0.0"
                correction = EvidenceFact.model_validate(
                    {
                        **target.model_dump(),
                        "event_id": identifier(),
                        "sequence": len(facts) + 1,
                        "kind": "invalidated",
                        "target_event_id": target.event_id,
                        "score": 0.0,
                        "quality": 0.0,
                        "valid": False,
                        "occurred_at": stamp,
                        "policy_version": version,
                        "policy_digest": digest(POLICIES[version].model_dump()),
                        "reason_code": "assessment_dispute_upheld",
                    }
                )
                append_fact(db, session.user_id, correction)
            outcome.update(
                status="excluded", score=None, quality=0.0, reason_code="assessment_dispute_upheld"
            )
    elif body["decision"] == "accept":
        if response.outcome["status"] == "excluded":
            raise AssessmentError("excluded_item_requires_replacement")
        if set(scores) != set(spec.rubric_criteria):
            raise AssessmentError("rubric_criteria_mismatch", 422)
        value = sum(scores.values()) / (4 * len(scores)) if scores else response.outcome["score"]
        if value is None:
            raise AssessmentError("deterministic_score_required")
        outcome = dict(
            status="scored",
            score=value,
            quality=1.0,
            scoring_version="human_rubric_1.0.0" if scores else response.outcome["scoring_version"],
            reason_code="human_review_accepted",
        )
    else:
        outcome = dict(
            status="excluded",
            score=None,
            quality=0.0,
            scoring_version="human_review_1.0.0",
            reason_code="human_review_excluded",
        )
    db.add(
        AssessmentReview(
            item_id=item.id,
            actor_id=actor,
            idempotency_key=body["idempotency_key"],
            request_digest=digest(body),
            outcome=outcome,
            evidence_reference=body["evidence_reference"],
            rationale=body["rationale"],
            created_at=stamp,
        )
    )
    session.revision += 1
    db.flush()
    record_event(db, actor, "assessment.reviewed", item.id)
    return public_view(db, session, stamp)


def code_admission(db, attempt, stamp):
    item_id = attempt.snapshot.get("assessment_item_id")
    if not item_id:
        return None
    item = db.get(AssessmentItem, item_id)
    session = db.get(AssessmentSession, item.session_id) if item else None
    if session is None or (session.user_id, session.pack_id, session.goal_id) != (
        attempt.user_id,
        attempt.pack_id,
        attempt.goal_id,
    ):
        return "assessment_attempt_mismatch"
    if (
        session.result is not None
        or session.status != "in_progress"
        or stamp >= session.deadline_at
        or db.get(AssessmentResponse, item.id)
    ):
        return "assessment_not_active"
    return None


def code_response(db, attempt, run, stamp):
    item = db.get(AssessmentItem, attempt.snapshot["assessment_item_id"])
    session = db.get(AssessmentSession, item.session_id)
    if db.get(AssessmentResponse, item.id):
        return
    # Admission timestamp determines timeliness; queue/worker latency never costs a learner points.
    rejection = code_admission(db, attempt, run.created_at)
    healthy = not rejection and run.status == "completed"
    value = (
        sum(x["status"] == "passed" for x in run.result["cases"]) / len(run.tests)
        if healthy
        else None
    )
    outcome = dict(
        status="scored" if healthy else "excluded",
        score=value,
        quality=1.0 if healthy else 0.0,
        scoring_version="implementation_1.0.0",
        reason_code="verified_implementation" if healthy else "execution_unverified",
    )
    form = AssessmentForm.model_validate(session.snapshot["form"])
    if value is not None and near_boundary(value, form):
        outcome.update(status="pending_review", reason_code="boundary_review_required")
    store_response(db, session, item, run.id, digest(run.manifest), outcome, run.created_at)
