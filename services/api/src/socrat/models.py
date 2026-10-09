import time
import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class Enrollment(Base):
    """A learner's goal in one course. Exactly one enrollment per user is active."""

    __tablename__ = "enrollments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16))
    level_id: Mapped[str] = mapped_column(String(64))
    goal: Mapped[dict] = mapped_column(JSON, default=dict)
    minutes_per_day: Mapped[int] = mapped_column(Integer)
    weekdays: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="placement")  # placement|active
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    placement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plan_signature: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ConceptState(Base):
    __tablename__ = "concept_states"
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), primary_key=True
    )
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class Evidence(Base):
    """Append-only scored learning evidence; the only input that changes mastery."""

    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_enrollment_created", "enrollment_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"))
    concept: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    assistance: Mapped[int] = mapped_column(Integer, default=0)
    activity_id: Mapped[str] = mapped_column(String(200))
    elapsed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    expected_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ActivityRecord(Base):
    """Start/completion of a plan activity (lesson, quiz, problem, checkpoint, review)."""

    __tablename__ = "activity_records"
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), primary_key=True
    )
    activity_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    started_at: Mapped[int] = mapped_column(Integer, default=now)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    activity_id: Mapped[str] = mapped_column(String(200))
    items: Mapped[list] = mapped_column(JSON)  # [[qualified concept, item id], ...]
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # item id -> {choice, correct}
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlanRevision(Base):
    __tablename__ = "plan_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    pace: Mapped[str] = mapped_column(String(16))
    reasons: Mapped[list] = mapped_column(JSON)
    remaining_minutes: Mapped[int] = mapped_column(Integer)
    projected_finish: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class Draft(Base):
    __tablename__ = "drafts"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class Submission(Base):
    """A Run or Submit, doubling as the signed execution job for the worker."""

    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_status_created", "status", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[str | None] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=True
    )
    problem_id: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(8))  # run|submit
    source: Mapped[str] = mapped_column(Text)
    custom_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|failed
    verdict: Mapped[str] = mapped_column(String(24), default="")
    cases: Mapped[list] = mapped_column(JSON, default=list)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    assistance: Mapped[int] = mapped_column(Integer, default=0)
    manifest: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(String(64))
    tests: Mapped[list] = mapped_column(JSON)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class JudgeWorker(Base):
    __tablename__ = "judge_workers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    images: Mapped[list] = mapped_column(JSON)
    seen_at: Mapped[int] = mapped_column(Integer)


class AssistantThread(Base):
    __tablename__ = "assistant_threads"
    __table_args__ = (UniqueConstraint("user_id", "scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String(200))  # general | problem:<id> | concept:<q>
    ladder: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("assistant_threads.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now, index=True)
    # Strictly increasing order within a thread (several messages can share a second).
    seq: Mapped[int] = mapped_column(BigInteger, default=time.time_ns, index=True)


class LessonVariant(Base):
    __tablename__ = "lesson_variants"
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    style: Mapped[str] = mapped_column(String(16), primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class DailyActivity(Base):
    __tablename__ = "daily_activity"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # local YYYY-MM-DD
    activities: Mapped[int] = mapped_column(Integer, default=0)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    solved: Mapped[int] = mapped_column(Integer, default=0)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    actor_id: Mapped[str] = mapped_column(String(36), index=True)
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


class PracticeMark(Base):
    """A learner's own status for an external (linked, not hosted) practice problem."""

    __tablename__ = "practice_marks"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="todo")  # todo|attempted|solved
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="self")  # self|codeforces
    opened_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solved_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class LinkedAccount(Base):
    """A public competitive-programming profile the learner chose to link (handle only)."""

    __tablename__ = "linked_accounts"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    platform: Mapped[str] = mapped_column(String(16), primary_key=True)  # codeforces
    handle: Mapped[str] = mapped_column(String(64))
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[str] = mapped_column(String(40), default="")
    solved: Mapped[list] = mapped_column(JSON, default=list)  # problem ids, e.g. "cf:1873A"
    attempted: Mapped[list] = mapped_column(JSON, default=list)
    tag_stats: Mapped[dict] = mapped_column(JSON, default=dict)  # tag -> {solved, failed}
    synced_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_error: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)
