"""Foundry-owned draft records; PostgreSQL indexing is introduced in M3."""

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from socrat.models import Base, identifier, now

ACTIVE = "state IN ('requested', 'probing', 'building')"


class Skill(Base):
    __tablename__ = "foundry_skills"
    __table_args__ = (
        CheckConstraint(
            "domain_type IN ('code','math','structured_writing','quiz_only','unsupported')"
        ),
        CheckConstraint("status IN ('requested','draft','waitlisted','rejected')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    domain_type: Mapped[str] = mapped_column(String(24), default="unsupported")
    status: Mapped[str] = mapped_column(String(24), default="requested")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class Job(Base):
    __tablename__ = "foundry_jobs"
    __table_args__ = (
        UniqueConstraint("skill_id", "input_hash", "pipeline_version"),
        Index(
            "uq_foundry_active_skill",
            "skill_id",
            unique=True,
            postgresql_where=text(ACTIVE),
            sqlite_where=text(ACTIVE),
        ),
        Index("ix_foundry_jobs_ready", "state", "next_attempt_at", "created_at"),
        CheckConstraint(
            "state IN ('requested','probing','building','draft_ready','in_review',"
            "'published','rejected','needs_human')"
        ),
        CheckConstraint("next_stage BETWEEN 0 AND 10 AND attempt >= 0"),
        CheckConstraint("budget_docs > 0 AND budget_tokens > 0 AND budget_seconds > 0"),
        CheckConstraint("spent_docs >= 0 AND spent_tokens >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    skill_id: Mapped[str] = mapped_column(ForeignKey("foundry_skills.id"))
    input_hash: Mapped[str] = mapped_column(String(64))
    input: Mapped[dict] = mapped_column(JSON)
    pipeline_version: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="requested")
    next_stage: Mapped[int] = mapped_column(Integer, default=0)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[int] = mapped_column(Integer, default=0)
    budget_docs: Mapped[int] = mapped_column(Integer)
    budget_tokens: Mapped[int] = mapped_column(Integer)
    budget_seconds: Mapped[int] = mapped_column(Integer)
    spent_docs: Mapped[int] = mapped_column(Integer, default=0)
    spent_tokens: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    started_at: Mapped[int | None] = mapped_column(Integer)
    finished_at: Mapped[int | None] = mapped_column(Integer)


class StageRun(Base):
    __tablename__ = "foundry_stage_runs"
    __table_args__ = (UniqueConstraint("job_id", "stage"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    job_id: Mapped[str] = mapped_column(ForeignKey("foundry_jobs.id", ondelete="CASCADE"))
    stage: Mapped[str] = mapped_column(String(4))
    input_hash: Mapped[str] = mapped_column(String(64))
    output_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class Control(Base):
    __tablename__ = "foundry_controls"
    __table_args__ = (CheckConstraint("day >= 0 AND jobs_started >= 0 AND spent_tokens >= 0"),)
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    day: Mapped[int] = mapped_column(Integer, default=0)
    jobs_started: Mapped[int] = mapped_column(Integer, default=0)
    spent_tokens: Mapped[int] = mapped_column(Integer, default=0)


class DomainPolicy(Base):
    __tablename__ = "foundry_domain_policies"
    __table_args__ = (
        CheckConstraint("mode IN ('allow','api_only','link_only','blocked')"),
        CheckConstraint("min_delay_ms >= 2000 AND max_concurrency BETWEEN 1 AND 2"),
    )
    domain: Mapped[str] = mapped_column(String(253), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), default="link_only")
    tos_reviewed_at: Mapped[int | None] = mapped_column(Integer)
    tos_notes: Mapped[str] = mapped_column(Text, default="")
    min_delay_ms: Mapped[int] = mapped_column(Integer, default=2000)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=2)
    next_allowed_at: Mapped[float] = mapped_column(Float, default=0)
    blocked_until: Mapped[float] = mapped_column(Float, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    leases: Mapped[dict] = mapped_column(JSON, default=dict)


class RobotsSnapshot(Base):
    __tablename__ = "foundry_robots_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    origin: Mapped[str] = mapped_column(String(300), index=True)
    user_agent: Mapped[str] = mapped_column(String(512))
    fetched_at: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int] = mapped_column(Integer)
    status: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    pipeline_version: Mapped[str] = mapped_column(String(64))


class FetchRecord(Base):
    __tablename__ = "foundry_fetch_records"
    __table_args__ = (
        CheckConstraint("policy_decision IN ('store','link_only','blocked')"),
        CheckConstraint("policy_decision = 'store' OR raw_object_key IS NULL"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    job_id: Mapped[str] = mapped_column(ForeignKey("foundry_jobs.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("foundry_sources.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    fetched_at: Mapped[int] = mapped_column(Integer)
    status: Mapped[int] = mapped_column(Integer)
    headers: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    robots_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("foundry_robots_snapshots.id")
    )
    policy_decision: Mapped[str] = mapped_column(String(16), default="link_only")
    license_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    pipeline_version: Mapped[str] = mapped_column(String(64))
    raw_object_key: Mapped[str | None] = mapped_column(String(512))
    reason: Mapped[str] = mapped_column(String(64))


class ApiCache(Base):
    __tablename__ = "foundry_api_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    etag: Mapped[str] = mapped_column(String(256))
    # Only selected repository metadata; never README, snippets, code or API error bodies.
    payload: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[int] = mapped_column(Integer)


class Source(Base):
    __tablename__ = "foundry_sources"
    __table_args__ = (
        UniqueConstraint("skill_id", "canonical_url"),
        UniqueConstraint("id", "skill_id", "policy_decision"),
        CheckConstraint("policy_decision IN ('store','link_only','blocked')"),
        CheckConstraint(
            "license_class IN ('open_permissive','open_sharealike',"
            "'noncommercial','noderivs','all_rights','unknown')"
        ),
        CheckConstraint("license_confidence BETWEEN 0 AND 1"),
        CheckConstraint(
            "policy_decision != 'store' OR (license_class IN "
            "('open_permissive','open_sharealike') AND license_confidence >= 0.8)"
        ),
        CheckConstraint("policy_decision = 'store' OR raw_object_key IS NULL"),
        CheckConstraint("status IN ('draft','quarantined')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    skill_id: Mapped[str] = mapped_column(ForeignKey("foundry_skills.id"))
    url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(160), default="")
    author: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(24), default="page")
    descriptor: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    license_spdx: Mapped[str | None] = mapped_column(String(64))
    license_url: Mapped[str | None] = mapped_column(String(2048))
    license_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    license_class: Mapped[str] = mapped_column(String(24), default="unknown")
    license_confidence: Mapped[float] = mapped_column(Float, default=0)
    policy_decision: Mapped[str] = mapped_column(String(16), default="link_only")
    pipeline_version: Mapped[str] = mapped_column(String(64))
    robots_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    raw_object_key: Mapped[str | None] = mapped_column(String(512))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    fetched_at: Mapped[int | None] = mapped_column(Integer)
    last_checked_at: Mapped[int | None] = mapped_column(Integer)
    link_status: Mapped[int | None] = mapped_column(Integer)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)


class Chunk(Base):
    __tablename__ = "foundry_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "skill_id", "policy_decision"],
            ["foundry_sources.id", "foundry_sources.skill_id", "foundry_sources.policy_decision"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("source_id", "content_hash", "pipeline_version", "ordinal"),
        CheckConstraint("policy_decision = 'store' AND ordinal >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    source_id: Mapped[str] = mapped_column(String(36))
    skill_id: Mapped[str] = mapped_column(String(36), index=True)
    policy_decision: Mapped[str] = mapped_column(String(16), default="store")
    ordinal: Mapped[int] = mapped_column(Integer)
    heading_path: Mapped[list] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64))
    pipeline_version: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(8), default="en")
    difficulty: Mapped[int | None] = mapped_column(Integer)
    attribution_text: Mapped[str] = mapped_column(Text)


class PackVersion(Base):
    __tablename__ = "foundry_skill_pack_versions"
    __table_args__ = (
        CheckConstraint("tier = 'explorer' AND status = 'draft'"),
        UniqueConstraint("id", "skill_id"),
        UniqueConstraint("skill_id", "version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    skill_id: Mapped[str] = mapped_column(ForeignKey("foundry_skills.id"))
    version: Mapped[str] = mapped_column(String(32))
    tier: Mapped[str] = mapped_column(String(16), default="explorer")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    manifest: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class Concept(Base):
    __tablename__ = "foundry_concepts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["pack_id", "skill_id"],
            ["foundry_skill_pack_versions.id", "foundry_skill_pack_versions.skill_id"],
        ),
        UniqueConstraint("pack_id", "slug"),
        UniqueConstraint("id", "pack_id"),
        CheckConstraint("confidence BETWEEN 0 AND 1 AND level BETWEEN 1 AND 5"),
        CheckConstraint("origin IN ('sources','llm') AND status = 'draft'"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    skill_id: Mapped[str] = mapped_column(String(36))
    pack_id: Mapped[str] = mapped_column(String(36))
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    can_do_statement: Mapped[str] = mapped_column(String(500))
    misconceptions: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    level: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    origin: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="draft")


class ConceptEdge(Base):
    __tablename__ = "foundry_concept_edges"
    __table_args__ = (
        ForeignKeyConstraint(
            ["from_id", "pack_id"], ["foundry_concepts.id", "foundry_concepts.pack_id"]
        ),
        ForeignKeyConstraint(
            ["to_id", "pack_id"], ["foundry_concepts.id", "foundry_concepts.pack_id"]
        ),
        CheckConstraint(
            "from_id != to_id AND support BETWEEN 0 AND 1 AND confidence BETWEEN 0 AND 1"
        ),
        CheckConstraint("origin IN ('sources','llm') AND review_state = 'pending'"),
    )
    from_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    to_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pack_id: Mapped[str] = mapped_column(String(36))
    support: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    origin: Mapped[str] = mapped_column(String(16))
    evidence: Mapped[list] = mapped_column(JSON)
    review_state: Mapped[str] = mapped_column(String(16), default="pending")


class ResourceAlignment(Base):
    __tablename__ = "foundry_resource_alignments"
    __table_args__ = (
        Index(
            "uq_foundry_link_alignment",
            "source_id",
            "concept_id",
            unique=True,
            postgresql_where=text("chunk_id IS NULL"),
            sqlite_where=text("chunk_id IS NULL"),
        ),
        UniqueConstraint("source_id", "concept_id", "chunk_id"),
        CheckConstraint("relevance BETWEEN 0 AND 1 AND level BETWEEN 1 AND 5"),
        CheckConstraint("role IN ('explanation','example','exercise','reference')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    source_id: Mapped[str] = mapped_column(ForeignKey("foundry_sources.id", ondelete="CASCADE"))
    chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("foundry_chunks.id", ondelete="CASCADE")
    )
    concept_id: Mapped[str] = mapped_column(ForeignKey("foundry_concepts.id", ondelete="CASCADE"))
    relevance: Mapped[float] = mapped_column(Float)
    role: Mapped[str] = mapped_column(String(16))
    level: Mapped[int] = mapped_column(Integer)


class TakedownRequest(Base):
    __tablename__ = "foundry_takedown_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    received_at: Mapped[int] = mapped_column(Integer, default=now)
    url: Mapped[str] = mapped_column(String(2048))
    private_reference: Mapped[str] = mapped_column(String(160))
    action_taken: Mapped[str] = mapped_column(String(64), default="pending")
    resolved_at: Mapped[int | None] = mapped_column(Integer)
