import time
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def identifier() -> str:
    return str(uuid.uuid4())


def now() -> int:
    return int(time.time())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("issuer", "subject"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    adult_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    delivered_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class DeliveredEvent(Base):
    __tablename__ = "delivered_events"
    event_id: Mapped[str] = mapped_column(ForeignKey("outbox_events.id"), primary_key=True)
    delivered_at: Mapped[int] = mapped_column(Integer, default=now)


class SkillPackVersion(Base):
    __tablename__ = "skill_pack_versions"
    __table_args__ = (UniqueConstraint("pack_key", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    pack_key: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(64))
    domain: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class SkillPackHead(Base):
    __tablename__ = "skill_pack_heads"
    pack_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    active_id: Mapped[str | None] = mapped_column(
        ForeignKey("skill_pack_versions.id"), nullable=True
    )
    previous_id: Mapped[str | None] = mapped_column(
        ForeignKey("skill_pack_versions.id"), nullable=True
    )


class ContentReview(Base):
    __tablename__ = "content_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    version_id: Mapped[str] = mapped_column(ForeignKey("skill_pack_versions.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(32))
    evidence_reference: Mapped[str] = mapped_column(String(512))
    reason: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LearnerGoal(Base):
    __tablename__ = "learner_goals"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    review_digest: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    confirmation_at: Mapped[int] = mapped_column(Integer, default=now)


class CurriculumRevision(Base):
    __tablename__ = "curriculum_revisions"
    __table_args__ = (UniqueConstraint("goal_id", "revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class CurriculumHead(Base):
    __tablename__ = "curriculum_heads"
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"), primary_key=True)
    active_id: Mapped[str] = mapped_column(ForeignKey("curriculum_revisions.id"))
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="draft")


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (UniqueConstraint("goal_id", "local_date"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"))
    curriculum_id: Mapped[str] = mapped_column(ForeignKey("curriculum_revisions.id"))
    pack_id: Mapped[str] = mapped_column(ForeignKey("skill_pack_versions.id"))
    local_date: Mapped[str] = mapped_column(String(10))
    snapshot: Mapped[dict] = mapped_column(JSON)
    progress: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SessionCommand(Base):
    __tablename__ = "session_commands"
    __table_args__ = (UniqueConstraint("session_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    session_id: Mapped[str] = mapped_column(ForeignKey("learning_sessions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class CodeAttempt(Base):
    __tablename__ = "code_attempts"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"))
    pack_id: Mapped[str] = mapped_column(ForeignKey("skill_pack_versions.id"))
    exercise_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class CodeDraft(Base):
    __tablename__ = "code_drafts"
    attempt_id: Mapped[str] = mapped_column(ForeignKey("code_attempts.id"), primary_key=True)
    source: Mapped[str] = mapped_column(String(64000))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class CodeRun(Base):
    __tablename__ = "code_runs"
    __table_args__ = (UniqueConstraint("attempt_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("code_attempts.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    client_key: Mapped[str] = mapped_column(String(64), index=True)
    manifest: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(String(64))
    tests: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class CodeRunSource(Base):
    __tablename__ = "code_run_sources"
    run_id: Mapped[str] = mapped_column(ForeignKey("code_runs.id"), primary_key=True)
    source: Mapped[str] = mapped_column(String(64000))


class TutorTurn(Base):
    __tablename__ = "tutor_turns"
    __table_args__ = (
        UniqueConstraint("attempt_id", "idempotency_key"),
        UniqueConstraint("attempt_id", "position"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("code_attempts.id"), index=True)
    scope_id: Mapped[str] = mapped_column(String(36), index=True)
    position: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    context_digest: Mapped[str] = mapped_column(String(64))
    action_digest: Mapped[str] = mapped_column(String(64))
    granted_level: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[dict] = mapped_column(JSON)
    telemetry: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class TutorArtifact(Base):
    """Separable sensitive content; never copied to analytics or audit payloads."""

    __tablename__ = "tutor_artifacts"
    turn_id: Mapped[str] = mapped_column(ForeignKey("tutor_turns.id"), primary_key=True)
    reasoning: Mapped[str] = mapped_column(String(2000))
    context: Mapped[dict] = mapped_column(JSON)
    response: Mapped[dict] = mapped_column(JSON)


class SubmitAssistance(Base):
    __tablename__ = "submit_assistance"
    run_id: Mapped[str] = mapped_column(ForeignKey("code_runs.id"), primary_key=True)
    hint_level: Mapped[int] = mapped_column(Integer)


class AdvisorShadow(Base):
    __tablename__ = "advisor_shadows"
    __table_args__ = (UniqueConstraint("curriculum_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    curriculum_id: Mapped[str] = mapped_column(ForeignKey("curriculum_revisions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ExecutionWorker(Base):
    __tablename__ = "execution_workers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    images: Mapped[list] = mapped_column(JSON)
    seen_at: Mapped[int] = mapped_column(Integer)


class ExecutionCapacity(Base):
    """Singleton lock serializes admission across learners and IP quotas."""

    __tablename__ = "execution_capacity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class PlanningCommand(Base):
    __tablename__ = "planning_commands"
    __table_args__ = (UniqueConstraint("goal_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (UniqueConstraint("goal_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"))
    pack_id: Mapped[str] = mapped_column(ForeignKey("skill_pack_versions.id"))
    blueprint_id: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    snapshot: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[int] = mapped_column(Integer, default=now)
    deadline_at: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DiagnosticAttempt(Base):
    __tablename__ = "diagnostic_attempts"
    __table_args__ = (UniqueConstraint("diagnostic_id", "position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    diagnostic_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_sessions.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer)
    selection: Mapped[dict] = mapped_column(JSON)
    issued_at: Mapped[int] = mapped_column(Integer, default=now)


class DiagnosticResponse(Base):
    __tablename__ = "diagnostic_responses"
    __table_args__ = (UniqueConstraint("diagnostic_id", "idempotency_key"),)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_attempts.id"), primary_key=True)
    diagnostic_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_sessions.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    answer_digest: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class DiagnosticAnswer(Base):
    """Restricted response artifact, separable from retained scoring/audit facts."""

    __tablename__ = "diagnostic_answers"
    attempt_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_attempts.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    answer: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LearningEvidence(Base):
    __tablename__ = "learning_evidence"
    __table_args__ = (
        UniqueConstraint("user_id", "sequence"),
        UniqueConstraint("user_id", "source_id", "kind"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    source_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LearnerState(Base):
    __tablename__ = "learner_states"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    active_policy: Mapped[str] = mapped_column(String(64), default="1.0.0")
    previous_policy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    projection: Mapped[dict] = mapped_column(JSON)


class MasteryEvent(Base):
    __tablename__ = "mastery_events"
    __table_args__ = (UniqueConstraint("evidence_id", "concept_key", "policy_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("learning_evidence.id"))
    concept_key: Mapped[str] = mapped_column(String(160))
    policy_version: Mapped[str] = mapped_column(String(64))
    before_state: Mapped[dict] = mapped_column(JSON)
    after_state: Mapped[dict] = mapped_column(JSON)
    reason_code: Mapped[str] = mapped_column(String(64))


class LearningPolicyReview(Base):
    __tablename__ = "learning_policy_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    policy_version: Mapped[str] = mapped_column(String(64))
    policy_digest: Mapped[str] = mapped_column(String(64))
    evidence_reference: Mapped[str] = mapped_column(String(512))
    projection_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("learner_goals.id"), index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("skill_pack_versions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    revision: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[int] = mapped_column(Integer)
    deadline_at: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AssessmentItem(Base):
    """Issuance is also the durable family exposure ledger, including excluded items."""

    __tablename__ = "assessment_items"
    __table_args__ = (UniqueConstraint("session_id", "position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    session_id: Mapped[str] = mapped_column(ForeignKey("assessment_sessions.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(64))
    family_id: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer)
    issued_at: Mapped[int] = mapped_column(Integer)


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"
    __table_args__ = (UniqueConstraint("session_id", "idempotency_key"),)
    item_id: Mapped[str] = mapped_column(ForeignKey("assessment_items.id"), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("assessment_sessions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer)


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    item_id: Mapped[str] = mapped_column(ForeignKey("assessment_items.id"), primary_key=True)
    answer: Mapped[str] = mapped_column(String(2000))


class AssessmentReview(Base):
    __tablename__ = "assessment_reviews"
    __table_args__ = (UniqueConstraint("item_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    item_id: Mapped[str] = mapped_column(ForeignKey("assessment_items.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[dict] = mapped_column(JSON)
    evidence_reference: Mapped[str] = mapped_column(String(512))
    rationale: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[int] = mapped_column(Integer)


class AssessmentDispute(Base):
    __tablename__ = "assessment_disputes"
    item_id: Mapped[str] = mapped_column(ForeignKey("assessment_items.id"), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    rationale: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[int] = mapped_column(Integer)
