"""Queue Run/Submit jobs, lease them to authenticated workers, and accept signed results.

The worker protocol (heartbeat → claim → result) and the signed JobEnvelope are unchanged
from the original execution plane, so services/execution/src/runner/worker.py runs as-is.
Hidden test inputs and outputs never leave the server; workers already blank hidden output.
"""

import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.schema import Problem
from socrat.config import Settings
from socrat.execution.protocol import (
    COMMANDS,
    JobEnvelope,
    JobManifest,
    ResultEnvelope,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
    verify,
)
from socrat.models import JudgeWorker, Submission, identifier

LEASE_SECONDS = 600
WORKER_FRESH_SECONDS = 30
CUSTOM_INPUT_LIMIT = 20_000


def profile_for(settings: Settings, language: str) -> RuntimeProfile:
    for raw in settings.execution_profiles:
        profile = RuntimeProfile.model_validate(raw)
        if profile.language == language:
            return profile
    raise HTTPException(503, "execution_unavailable")


def healthy_images(db: Session, settings: Settings, now: int) -> set[str]:
    allowed = {x["image"] for x in settings.execution_profiles}
    workers = db.scalars(
        select(JudgeWorker).where(JudgeWorker.seen_at >= now - WORKER_FRESH_SECONDS)
    )
    return {image for worker in workers for image in worker.images if image in allowed}


def runtimes(db: Session, settings: Settings, now: int) -> dict[str, bool]:
    healthy = healthy_images(db, settings, now)
    return {x["language"]: x["image"] in healthy for x in settings.execution_profiles}


def create(
    db: Session,
    settings: Settings,
    user_id: str,
    enrollment_id: str | None,
    problem: Problem,
    language: str,
    source: str,
    mode: str,
    custom_input: str | None,
    assistance: int,
    now: int,
) -> Submission:
    profile = profile_for(settings, language)
    if profile.image not in healthy_images(db, settings, now):
        raise HTTPException(503, "runtime_offline")
    if not source.strip():
        raise HTTPException(422, "empty_source")
    today_count = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(Submission.user_id == user_id, Submission.created_at >= now - 86400)
    )
    if (today_count or 0) >= settings.execution_daily_quota:
        raise HTTPException(429, "daily_run_quota")
    pending = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(Submission.user_id == user_id, Submission.status.in_(["queued", "running"]))
    )
    if (pending or 0) >= settings.execution_queue_limit:
        raise HTTPException(429, "too_many_pending_runs")
    if mode == "run" and custom_input is not None:
        if len(custom_input) > CUSTOM_INPUT_LIMIT:
            raise HTTPException(422, "custom_input_too_large")
        tests = [dict(input=custom_input, expected=None, visibility="public")]
    else:
        tests = [
            dict(
                input=t.input,
                expected=t.expected,
                visibility="public" if t.public else "hidden",
            )
            for t in problem.tests
            if mode == "submit" or t.public
        ]
    if not tests:
        raise HTTPException(409, "problem_has_no_tests")
    job_id = identifier()
    manifest = JobManifest(
        job_id=job_id,
        attempt_id=identifier(),
        nonce=secrets.token_hex(32),
        issued_at=now,
        expires_at=now + LEASE_SECONDS,
        language=profile.language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(source.encode()),
        test_digest=hashed(canonical(tests)),
        pack_digest=hashed(problem.id.encode()),
        mode="submit" if mode == "submit" else "run",
        limits=profile.limits,
        compile_config=COMMANDS[profile.language],
    ).model_dump()
    submission = Submission(
        id=job_id,
        user_id=user_id,
        enrollment_id=enrollment_id,
        problem_id=problem.id,
        language=language,
        mode=mode,
        source=source,
        custom_input=custom_input,
        status="queued",
        total=len(tests),
        assistance=assistance,
        manifest=manifest,
        signature=sign(manifest, settings.execution_signing_secret.get_secret_value()),
        tests=tests,
        created_at=now,
    )
    db.add(submission)
    db.flush()
    return submission


def heartbeat(db: Session, settings: Settings, worker_id: str, images: list[str], now: int):
    allowed = {x["image"] for x in settings.execution_profiles}
    if len(images) != len(set(images)) or not set(images) <= allowed:
        raise HTTPException(422, "worker_runtime_mismatch")
    worker = db.get(JudgeWorker, worker_id)
    if worker is None:
        db.add(JudgeWorker(id=worker_id, images=images, seen_at=now))
    else:
        worker.images, worker.seen_at = images, now


def claim(db: Session, worker_id: str, now: int) -> dict | None:
    worker = db.get(JudgeWorker, worker_id)
    if worker is None or worker.seen_at < now - WORKER_FRESH_SECONDS:
        raise HTTPException(403, "worker_capability_expired")
    for stale in db.scalars(
        select(Submission)
        .where(
            Submission.status.in_(["queued", "running"]),
            Submission.created_at < now - LEASE_SECONDS,
        )
        .with_for_update(skip_locked=True)
    ):
        stale.status, stale.verdict, stale.finished_at = "failed", "system_error", now
    for job in db.scalars(
        select(Submission)
        .where(Submission.status == "queued")
        .order_by(Submission.created_at, Submission.id)
        .limit(20)
        .with_for_update(skip_locked=True)
    ):
        if job.manifest["image"] not in worker.images:
            continue
        job.status, job.worker_id, job.lease_until = (
            "running",
            worker_id,
            job.manifest["expires_at"],
        )
        return JobEnvelope(
            manifest=JobManifest.model_validate(job.manifest),
            signature=job.signature,
            source=job.source,
            tests=[TestInput.model_validate(x) for x in job.tests],
        ).model_dump()
    return None


def verdict_of(cases: list[dict], mode: str, custom: bool) -> str:
    statuses = [case["status"] for case in cases]
    if "compile_error" in statuses:
        return "compile_error"
    if custom:
        return next((s for s in statuses if s != "executed"), "ran")
    for status in statuses:
        if status != "passed":
            return status
    return "accepted"


def finalize(db: Session, settings: Settings, worker_id: str, envelope: ResultEnvelope, now: int):
    result = envelope.result
    try:
        verify(
            result.model_dump(),
            envelope.signature,
            settings.execution_signing_secret.get_secret_value(),
        )
    except ValueError as exc:
        raise HTTPException(409, "execution_signature_invalid") from exc
    job = db.get(Submission, result.job_id)
    if job is None or job.worker_id != worker_id:
        raise HTTPException(404, "not_found")
    for field in ("nonce", "code_hash", "test_digest", "image"):
        if getattr(result, field) != job.manifest[field]:
            raise HTTPException(409, "execution_result_mismatch")
    if job.status in {"done", "failed"}:
        return job, False  # Duplicate delivery after a retry: idempotent.
    if job.status != "running" or job.lease_until is None or now > job.lease_until:
        raise HTTPException(409, "execution_lease_expired")
    job.finished_at = now
    if result.operational_status != "healthy":
        job.status, job.verdict = "failed", "system_error"
        return job, True
    if [x.index for x in result.cases] != list(range(len(job.tests))):
        raise HTTPException(409, "execution_result_incomplete")
    cases = []
    for case, test in zip(result.cases, job.tests, strict=True):
        public = test["visibility"] == "public"
        cases.append(
            dict(
                status=case.status,
                wall_ms=case.wall_ms,
                public=public,
                input=test["input"][:4000] if public else None,
                expected=(test["expected"] or "")[:4000]
                if public and test["expected"] is not None
                else None,
                stdout=case.stdout[:4000] if public else None,
                stderr=case.stderr[:4000] if public or case.status == "compile_error" else None,
            )
        )
    job.cases = cases
    job.passed = sum(c["status"] == "passed" for c in cases)
    job.verdict = verdict_of(cases, job.mode, job.custom_input is not None)
    job.status = "done"
    return job, True


def view(job: Submission) -> dict:
    return dict(
        id=job.id,
        problem_id=job.problem_id,
        language=job.language,
        mode=job.mode,
        status=job.status,
        verdict=job.verdict,
        passed=job.passed,
        total=job.total,
        cases=job.cases,
        assistance=job.assistance,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )
