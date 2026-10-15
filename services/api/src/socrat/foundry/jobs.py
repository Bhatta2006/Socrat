"""Durable claims and bounded stage execution, independent of the learner engine."""

import hashlib
import json
import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, Engine, or_, select, text
from sqlalchemy.orm import Session

from socrat.foundry.config import FoundrySettings
from socrat.foundry.models import Control, Job, Skill, StageRun
from socrat.models import Base, identifier, now

STAGES = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S10")
logger = logging.getLogger("socrat.foundry")


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    title: str = Field(min_length=2, max_length=160)
    payload: dict = Field(default_factory=dict)


class FoundryStopped(RuntimeError):
    """A fixed reason code; never embed exception messages or remote content."""

    def __init__(self, code: str):
        codes = {
            "disabled",
            "controls_unavailable",
            "skill_build_active",
            "kill_switch",
            "budget_wall_time",
            "pipeline_version_changed",
            "budget_daily_jobs",
            "live_disabled",
            "budget_documents",
            "budget_tokens",
            "budget_daily_tokens",
            "worker_failed",
            "attempts_exhausted",
        }
        super().__init__(code if code in codes else "stage_blocked")


class LeaseLost(RuntimeError):
    pass


class RetryableError(RuntimeError):
    pass


def digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > 65536:
        raise ValueError("foundry_input_too_large")
    return hashlib.sha256(encoded).hexdigest()


def log(event: str, job: Job, stage: str | None = None):
    logger.info(
        json.dumps(
            {
                "event": event,
                "job_id": job.id,
                "stage": stage,
                "state": job.state,
                "reason": job.error_code,
            }
        )
    )


def control(db: Session, stamp: int) -> Control:
    row = db.scalar(select(Control).where(Control.id == "global").with_for_update())
    if row is None:
        raise FoundryStopped("controls_unavailable")
    day = stamp // 86400
    # A backwards clock must not reset reservations or reopen an earlier day's quota.
    if day > row.day:
        row.day, row.jobs_started, row.spent_tokens = day, 0, 0
    return row


def enqueue(engine: Engine, settings: FoundrySettings, request: JobRequest) -> str:
    if not settings.enabled:
        raise FoundryStopped("disabled")
    payload = request.model_dump()
    content_hash = digest(payload)
    with Session(engine) as db, db.begin():
        # A single global enqueue lock also serializes first creation of a canonical skill.
        control(db, now())
        skill = db.scalar(select(Skill).where(Skill.slug == request.slug).with_for_update())
        if skill is None:
            skill = Skill(slug=request.slug, title=request.title)
            db.add(skill)
            db.flush()
        previous = db.scalar(
            select(Job).where(
                Job.skill_id == skill.id,
                Job.input_hash == content_hash,
                Job.pipeline_version == settings.pipeline_version,
            )
        )
        if previous is not None:
            return previous.id
        if db.scalar(
            select(Job.id).where(
                Job.skill_id == skill.id, Job.state.in_(["requested", "probing", "building"])
            )
        ):
            raise FoundryStopped("skill_build_active")
        job = Job(
            skill_id=skill.id,
            input_hash=content_hash,
            input=payload,
            pipeline_version=settings.pipeline_version,
            budget_docs=settings.max_docs_per_job,
            budget_tokens=settings.max_tokens_per_job,
            budget_seconds=settings.max_wall_seconds,
        )
        db.add(job)
        db.flush()
        log("job_requested", job)
        return job.id


def park(job: Job, reason: str, stamp: int):
    job.state, job.error_code, job.finished_at = "needs_human", reason, stamp
    job.owner, job.lease_until = None, None
    log("job_parked", job, STAGES[job.next_stage] if job.next_stage < len(STAGES) else None)


def guard(job: Job, controls: Control, settings: FoundrySettings, stamp: int) -> None:
    if not settings.enabled or settings.kill_switch or controls.kill_switch:
        raise FoundryStopped("kill_switch")
    if job.started_at is not None and stamp >= job.started_at + job.budget_seconds:
        raise FoundryStopped("budget_wall_time")
    if job.pipeline_version != settings.pipeline_version:
        raise FoundryStopped("pipeline_version_changed")


@dataclass(frozen=True)
class Claim:
    job_id: str
    owner: str
    connection: Connection


@contextmanager
def claim(
    engine: Engine, settings: FoundrySettings, clock: Callable[[], int]
) -> Iterator[Claim | None]:
    with engine.connect() as connection:
        advisory_key = None
        claimed = None
        try:
            if settings.enabled:
                with Session(connection) as db, db.begin():
                    stamp = clock()
                    candidates = db.scalars(
                        select(Job)
                        .where(
                            Job.state.in_(["requested", "probing", "building"]),
                            Job.next_attempt_at <= stamp,
                            or_(Job.owner.is_(None), Job.lease_until <= stamp),
                        )
                        .order_by(Job.created_at, Job.id)
                        .limit(20)
                        .with_for_update(skip_locked=True)
                    )
                    for job in candidates:
                        if connection.dialect.name == "postgresql":
                            key = int.from_bytes(
                                hashlib.sha256(job.skill_id.encode()).digest()[:8],
                                "big",
                                signed=True,
                            )
                            if not db.scalar(
                                text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
                            ):
                                continue
                            advisory_key = key
                        try:
                            controls = control(db, stamp)
                            guard(job, controls, settings, stamp)
                            if job.owner is not None:
                                job.attempt += 1
                                if job.attempt >= settings.max_attempts:
                                    raise FoundryStopped("attempts_exhausted")
                            if job.started_at is None:
                                if controls.jobs_started >= settings.max_jobs_per_day:
                                    raise FoundryStopped("budget_daily_jobs")
                                controls.jobs_started += 1
                                job.started_at = stamp
                            job.owner = identifier()
                            job.lease_until = min(
                                stamp + settings.lease_seconds, job.started_at + job.budget_seconds
                            )
                            job.state = "probing" if job.next_stage < 2 else "building"
                            claimed = Claim(job.id, job.owner, connection)
                            log("job_claimed", job, STAGES[job.next_stage])
                        except FoundryStopped as exc:
                            park(job, str(exc), stamp)
                        break
            yield claimed
        finally:
            if advisory_key is not None:
                # Session locks survive commits; always release on this same connection.
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": advisory_key})
                connection.commit()


def owned(db: Session, lease: Claim, stamp: int) -> Job:
    job = db.scalar(select(Job).where(Job.id == lease.job_id).with_for_update())
    if (
        job is None
        or job.owner != lease.owner
        or job.lease_until is None
        or job.state not in {"probing", "building"}
    ):
        raise LeaseLost("lease_lost")
    if job.started_at is not None and stamp >= job.started_at + job.budget_seconds:
        raise FoundryStopped("budget_wall_time")
    if stamp >= job.lease_until:
        raise LeaseLost("lease_lost")
    return job


@dataclass(frozen=True)
class StageResult:
    content: dict
    records: tuple[Base, ...] = ()


@dataclass(frozen=True)
class StageContext:
    lease: Claim
    settings: FoundrySettings
    clock: Callable[[], int]
    stage: str
    skill_id: str
    input: dict

    def reserve(self, *, documents: int = 0, tokens: int = 0, live: bool = False):
        """Call immediately before EACH external attempt; failed attempts remain charged."""
        if type(documents) is not int or type(tokens) is not int or documents < 0 or tokens < 0:
            raise ValueError("invalid_reservation")
        reason = None
        with Session(self.lease.connection) as db, db.begin():
            stamp = self.clock()
            job = owned(db, self.lease, stamp)
            try:
                controls = control(db, stamp)
                guard(job, controls, self.settings, stamp)
                if live and not self.settings.live_enabled:
                    raise FoundryStopped("live_disabled")
                if job.spent_docs + documents > job.budget_docs:
                    raise FoundryStopped("budget_documents")
                if job.spent_tokens + tokens > job.budget_tokens:
                    raise FoundryStopped("budget_tokens")
                if controls.spent_tokens + tokens > self.settings.max_tokens_per_day:
                    raise FoundryStopped("budget_daily_tokens")
                job.spent_docs += documents
                job.spent_tokens += tokens
                controls.spent_tokens += tokens
                job.lease_until = min(
                    stamp + self.settings.lease_seconds,
                    (job.started_at or stamp) + job.budget_seconds,
                )
            except FoundryStopped as exc:
                reason = str(exc)
                park(job, reason, stamp)
        if reason:
            raise FoundryStopped(reason)


Handler = Callable[[StageContext], StageResult]


def stub(context: StageContext) -> StageResult:
    return StageResult({"stub": True, "stage": context.stage})


def run_once(
    engine: Engine,
    settings: FoundrySettings,
    handlers: Mapping[str, Handler] | None = None,
    *,
    clock: Callable[[], int] = now,
) -> bool:
    """Handlers prepare records outside transactions; effects/checkpoint then commit together."""
    stages = handlers if handlers is not None else dict.fromkeys(STAGES, stub)
    with claim(engine, settings, clock) as lease:
        if lease is None:
            return False
        stage = None
        while True:
            try:
                with Session(lease.connection) as db:
                    job = owned(db, lease, clock())
                    stage = STAGES[job.next_stage]
                    context = StageContext(lease, settings, clock, stage, job.skill_id, job.input)
                context.reserve()
                result = stages[stage](context)
                output_hash = digest(result.content)
                with Session(lease.connection) as db, db.begin():
                    stamp = clock()
                    job = owned(db, lease, stamp)
                    guard(job, control(db, stamp), settings, stamp)
                    for record in result.records:
                        if not getattr(record, "__tablename__", "").startswith("foundry_"):
                            raise ValueError("non_foundry_record")
                        db.add(record)
                    previous = (
                        db.scalar(
                            select(StageRun).where(
                                StageRun.job_id == job.id,
                                StageRun.stage == STAGES[job.next_stage - 1],
                            )
                        )
                        if job.next_stage
                        else None
                    )
                    db.add(
                        StageRun(
                            job_id=job.id,
                            stage=stage,
                            input_hash=previous.output_hash if previous else job.input_hash,
                            output_hash=output_hash,
                            created_at=stamp,
                        )
                    )
                    job.next_stage += 1
                    job.attempt, job.error_code = 0, None
                    job.state = "building" if job.next_stage >= 2 else "probing"
                    job.lease_until = min(
                        stamp + settings.lease_seconds,
                        (job.started_at or stamp) + job.budget_seconds,
                    )
                    log("stage_completed", job, stage)
                    if job.next_stage == len(STAGES):
                        # Stub success is not a gate pass or a publishable course.
                        park(job, "stub_pipeline_complete", stamp)
                        return True
            except LeaseLost:
                logger.info(
                    json.dumps({"event": "lease_lost", "job_id": lease.job_id, "stage": stage})
                )
                return True
            except Exception as exc:
                with Session(lease.connection) as db, db.begin():
                    stamp = clock()
                    current = db.get(Job, lease.job_id, with_for_update=True)
                    if current is None or current.owner != lease.owner:
                        return True
                    current.attempt += 1
                    if isinstance(exc, FoundryStopped):
                        park(current, str(exc), stamp)
                    elif (
                        current.started_at is not None
                        and stamp >= current.started_at + current.budget_seconds
                    ):
                        park(current, "budget_wall_time", stamp)
                    elif current.attempt >= settings.max_attempts:
                        park(current, "attempts_exhausted", stamp)
                    else:
                        current.error_code = (
                            "retryable_error" if isinstance(exc, RetryableError) else "stage_failed"
                        )
                        current.next_attempt_at = stamp + min(
                            300, settings.retry_seconds * 2 ** (current.attempt - 1)
                        )
                        current.owner, current.lease_until = None, None
                        log("stage_retry", current, stage)
                return True
