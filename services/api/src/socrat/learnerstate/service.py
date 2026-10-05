"""Transactional projection writes and audited repairs. Caller holds the learner lock."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.learnerstate.policy import POLICIES, digest
from socrat.learnerstate.projector import EvidenceFact, empty_state, replay, state_key
from socrat.models import (
    LearnerState,
    LearningEvidence,
    LearningPolicyReview,
    MasteryEvent,
    SkillPackVersion,
)
from socrat.skillpacks.service import load


def facts_for(db: Session, user_id: str) -> list[EvidenceFact]:
    records = db.scalars(
        select(LearningEvidence)
        .where(LearningEvidence.user_id == user_id)
        .order_by(LearningEvidence.sequence)
    ).all()
    facts = []
    for record in records:
        fact = EvidenceFact.model_validate(record.payload)
        if (
            fact.user_id != user_id
            or fact.policy_version not in POLICIES
            or fact.policy_digest != digest(POLICIES[fact.policy_version].model_dump())
        ):
            raise ValueError("Evidence policy or ownership mismatch")
        if (fact.event_id, fact.sequence, fact.source_id, fact.kind) != (
            record.id,
            record.sequence,
            record.source_id,
            record.kind,
        ):
            raise ValueError("Evidence envelope mismatch")
        facts.append(fact)
    return facts


def requirements_for(db: Session, facts: list[EvidenceFact]) -> dict:
    result = {}
    scopes = {(fact.pack_id, fact.pack_digest, fact.language) for fact in facts}
    for pack_id, expected_digest, language in sorted(scopes):
        record = db.get(SkillPackVersion, pack_id)
        if record is None or record.digest != expected_digest:
            raise ValueError("Evidence content version missing")
        pack = load(record)
        for concept in pack.concepts:
            result[state_key(pack_id, language, concept.id)] = {
                "minimum_independent": pack.mastery_policy.minimum_independent,
                "minimum_families": pack.mastery_policy.minimum_families,
                "retention_days": pack.mastery_policy.retention_days,
                "prerequisites": {
                    state_key(pack_id, language, edge.prerequisite): max(0.75, edge.minimum_mastery)
                    for edge in pack.edges
                    if edge.concept == concept.id
                },
            }
    return result


def project(db: Session, user_id: str, version: str, as_of: int) -> dict:
    facts = facts_for(db, user_id)
    return replay(facts, version, as_of, requirements_for(db, facts))


def append_fact(db: Session, user_id: str, fact: EvidenceFact) -> dict:
    current = db.get(LearnerState, user_id)
    version = current.active_policy if current else "1.0.0"
    before = project(db, user_id, version, fact.occurred_at)
    if fact.sequence != before["watermark"] + 1:
        raise ValueError("Evidence sequence conflict")
    record = LearningEvidence(
        id=fact.event_id,
        user_id=user_id,
        sequence=fact.sequence,
        source_id=fact.source_id,
        kind=fact.kind,
        payload=fact.model_dump(),
    )
    db.add(record)
    db.flush()
    after = project(db, user_id, version, fact.occurred_at)
    if current is None:
        current = LearnerState(user_id=user_id, active_policy=version, projection=after)
        db.add(current)
    current.projection = after
    for key, state in after["concepts"].items():
        prior = before["concepts"].get(key, empty_state(POLICIES[version]))
        if any(
            prior.get(name) != state.get(name)
            for name in ("alpha", "beta", "evidence_count", "misconceptions")
        ):
            db.add(
                MasteryEvent(
                    user_id=user_id,
                    evidence_id=record.id,
                    concept_key=key,
                    policy_version=version,
                    before_state=prior,
                    after_state=state,
                    reason_code=fact.reason_code,
                )
            )
    record_event(db, user_id, "learning.evidence_recorded", record.id)
    return after


def promote_policy(
    db: Session, user_id: str, actor: str, version: str, as_of: int, reference: str, expected: str
) -> dict:
    projection = project(db, user_id, version, as_of)
    if digest(projection) != expected:
        raise ValueError("Policy review stale")
    state = db.get(LearnerState, user_id)
    if state is None:
        state = LearnerState(user_id=user_id, active_policy="1.0.0", projection=projection)
        db.add(state)
    if state.active_policy != version:
        state.previous_policy, state.active_policy = state.active_policy, version
    state.projection = projection
    db.add(
        LearningPolicyReview(
            user_id=user_id,
            actor_id=actor,
            policy_version=version,
            policy_digest=digest(POLICIES[version].model_dump()),
            evidence_reference=reference,
            projection_digest=expected,
        )
    )
    record_event(db, actor, "learning.policy_promoted", user_id)
    return projection
