import json
from collections import Counter
from dataclasses import replace

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic import ValidationError
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.foundry.config import FoundrySettings
from socrat.foundry.jobs import (
    STAGES,
    FoundryStopped,
    JobRequest,
    RetryableError,
    StageResult,
    claim,
    digest,
    enqueue,
    run_once,
    stub,
)
from socrat.foundry.models import Chunk, Control, Job, Skill, Source, StageRun
from socrat.models import Base, User

from .conftest import migrate


def request(slug="git", **payload):
    return JobRequest(slug=slug, title=slug.title(), payload=payload)


def row(engine, job_id):
    with Session(engine) as db:
        return db.get(Job, job_id)


def handlers(first):
    return {**dict.fromkeys(STAGES, stub), "S0": first}


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_docs_per_job", 0),
        ("max_tokens_per_job", -1),
        ("max_wall_seconds", 0),
        ("max_attempts", 0),
        ("min_delay_ms", 1),
        ("max_concurrency_per_domain", 3),
        ("min_link_health", float("nan")),
        ("github_pushed_after", "2025-02-30"),
        ("tier", "verified"),
        ("live_enabled", True),
    ],
)
def test_config_fails_closed(field, value):
    with pytest.raises(ValidationError):
        FoundrySettings(_env_file=None, **{field: value})


def test_config_uses_prefixed_environment(monkeypatch):
    monkeypatch.setenv("SOCRAT_FOUNDRY_MAX_DOCS_PER_JOB", "8")
    settings = FoundrySettings(_env_file=None)
    assert settings.max_docs_per_job == 8 and not settings.enabled and not settings.live_enabled


def test_migration_reverses_without_losing_existing_data(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = migrate(url, "0007_learning_sessions")
    from socrat.database import make_engine

    engine = make_engine(url)
    with Session(engine) as db, db.begin():
        db.add(User(id="preserved", issuer="test", subject="existing"))
    command.upgrade(config, "head")
    assert len([t for t in inspect(engine).get_table_names() if t.startswith("foundry_")]) == 12
    with engine.connect() as db:
        context = MigrationContext.configure(
            db,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    type_ != "table" or name.startswith("foundry_")
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
    command.downgrade(config, "0007_learning_sessions")
    assert not any(t.startswith("foundry_") for t in inspect(engine).get_table_names())
    with Session(engine) as db:
        assert db.get(User, "preserved").subject == "existing"
    command.upgrade(config, "head")
    engine.dispose()


def test_disabled_runner_and_enqueue_do_nothing(engine, clock):
    settings = FoundrySettings(_env_file=None)
    with pytest.raises(FoundryStopped, match="disabled"):
        enqueue(engine, settings, request())
    assert not run_once(engine, settings, clock=clock)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Skill)) == 0


def test_stub_completes_once_without_content_or_learner_writes(engine, settings, clock, caplog):
    caplog.set_level("INFO", logger="socrat.foundry")
    job_id = enqueue(engine, settings, request(b=2, a=1))
    assert enqueue(engine, settings, request(a=1, b=2)) == job_id
    assert run_once(engine, settings, clock=clock)
    result = row(engine, job_id)
    assert result.state == "needs_human" and result.error_code == "stub_pipeline_complete"
    assert result.next_stage == len(STAGES) and result.spent_tokens == result.spent_docs == 0
    assert enqueue(engine, settings, request(a=1, b=2)) == job_id
    assert not run_once(engine, settings, clock=clock)
    with Session(engine) as db:
        runs = db.scalars(
            select(StageRun)
            .where(StageRun.job_id == job_id)
            .order_by(StageRun.created_at, StageRun.stage)
        ).all()
        assert {r.stage for r in runs} == set(STAGES)
        by_stage = {r.stage: r for r in runs}
        assert by_stage["S0"].input_hash == result.input_hash
        for previous, following in zip(STAGES, STAGES[1:], strict=False):
            assert by_stage[following].input_hash == by_stage[previous].output_hash
        for name in (
            "users",
            "enrollments",
            "evidence",
            "concept_states",
            "foundry_sources",
            "foundry_chunks",
            "foundry_concepts",
            "foundry_skill_pack_versions",
        ):
            assert db.scalar(select(func.count()).select_from(Base.metadata.tables[name])) == 0
    records = [json.loads(r.message) for r in caplog.records if r.name == "socrat.foundry"]
    assert all(r["job_id"] == job_id for r in records)
    assert any(r["event"] == "stage_completed" and r["stage"] == "S10" for r in records)


def test_active_build_blocks_new_input_but_pipeline_version_is_part_of_identity(
    engine, settings, clock
):
    first = enqueue(engine, settings, request(version=1))
    with pytest.raises(FoundryStopped, match="skill_build_active"):
        enqueue(engine, settings, request(version=2))
    run_once(engine, settings, clock=clock)
    changed = settings.model_copy(update={"pipeline_version": "foundry-m1.1"})
    assert enqueue(engine, changed, request(version=1)) != first


def test_crash_resumes_after_last_committed_stage(engine, settings, clock):
    job_id = enqueue(engine, settings, request())
    calls = Counter()

    def prepare(context):
        calls["S0"] += 1
        source = Source(
            skill_id=context.skill_id,
            url="https://example.test/git",
            canonical_url="https://example.test/git",
            pipeline_version="foundry-m1",
        )
        return StageResult({"source": "git"}, (source,))

    class Crash(BaseException):
        pass

    def crash(context):
        raise Crash()

    stages = {**handlers(prepare), "S1": crash}
    with pytest.raises(Crash):
        run_once(engine, settings, stages, clock=clock)
    assert row(engine, job_id).next_stage == 1
    assert not run_once(engine, settings, handlers(prepare), clock=clock)
    clock.stamp += settings.lease_seconds
    assert run_once(engine, settings, handlers(prepare), clock=clock)
    assert calls["S0"] == 1 and row(engine, job_id).next_stage == len(STAGES)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(StageRun)) == len(STAGES)


def test_stage_effects_and_checkpoint_roll_back_together(engine, settings, clock):
    job_id = enqueue(engine, settings, request())

    def bad(context):
        sources = tuple(
            Source(
                skill_id=context.skill_id,
                url="https://example.test/",
                canonical_url="https://example.test/",
                pipeline_version="m1",
            )
            for _ in range(2)
        )
        return StageResult({"x": 1}, sources)

    run_once(engine, settings, handlers(bad), clock=clock)
    assert row(engine, job_id).attempt == 1 and row(engine, job_id).next_stage == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 0
        assert db.scalar(select(func.count()).select_from(StageRun)) == 0


def test_retry_backoff_poison_and_secret_safe_logs(engine, settings, clock, caplog):
    caplog.set_level("INFO", logger="socrat.foundry")
    job_id = enqueue(engine, settings, request())

    def broken(context):
        context.reserve(tokens=7)
        raise RetryableError("secret=https://password@example.test/")

    for attempt in range(1, 4):
        assert run_once(engine, settings, handlers(broken), clock=clock)
        job = row(engine, job_id)
        assert job.attempt == attempt and job.spent_tokens == attempt * 7
        if attempt < 3:
            assert job.next_attempt_at == clock.stamp + settings.retry_seconds * 2 ** (attempt - 1)
            assert not run_once(engine, settings, handlers(broken), clock=clock)
            clock.stamp = job.next_attempt_at
    assert job.state == "needs_human" and job.error_code == "attempts_exhausted"
    assert "password" not in caplog.text and "secret=" not in caplog.text
    assert str(FoundryStopped("secret")) == "stage_blocked"


@pytest.mark.parametrize(
    "limits,reservation,reason",
    [
        ({"max_docs_per_job": 1}, {"documents": 2}, "budget_documents"),
        ({"max_tokens_per_job": 1}, {"tokens": 2}, "budget_tokens"),
        ({"max_tokens_per_day": 1}, {"tokens": 2}, "budget_daily_tokens"),
        ({}, {"live": True}, "live_disabled"),
    ],
)
def test_reservation_parks_before_unbounded_work(
    engine, settings, clock, limits, reservation, reason
):
    settings = settings.model_copy(update=limits)
    job_id = enqueue(engine, settings, request())
    performed = []

    def external(context):
        context.reserve(**reservation)
        performed.append(True)
        return stub(context)

    run_once(engine, settings, handlers(external), clock=clock)
    result = row(engine, job_id)
    assert result.state == "needs_human" and result.error_code == reason
    assert not performed and result.next_stage == 0


def test_wall_clock_budget_survives_restart(engine, settings, clock):
    settings = settings.model_copy(update={"max_wall_seconds": 10})
    job_id = enqueue(engine, settings, request())

    def slow(context):
        clock.stamp += 10
        return stub(context)

    run_once(engine, settings, handlers(slow), clock=clock)
    assert row(engine, job_id).error_code == "budget_wall_time"
    assert row(engine, job_id).state == "needs_human"


def test_kill_switch_is_reloaded_before_each_operation(engine, settings, clock):
    job_id = enqueue(engine, settings, request())

    def killed(context):
        context.reserve(tokens=1)
        with Session(engine) as db, db.begin():
            db.get(Control, "global").kill_switch = True
        context.reserve(tokens=1)
        pytest.fail("kill switch did not stop work")

    run_once(engine, settings, handlers(killed), clock=clock)
    assert row(engine, job_id).error_code == "kill_switch"
    assert row(engine, job_id).spent_tokens == 1


def test_missing_controls_fail_closed(engine, settings, clock):
    job_id = enqueue(engine, settings, request())
    with Session(engine) as db, db.begin():
        db.delete(db.get(Control, "global"))
    assert not run_once(engine, settings, clock=clock)
    assert row(engine, job_id).error_code == "controls_unavailable"


def test_daily_jobs_and_tokens_are_shared_and_reset_only_forward(engine, settings, clock):
    settings = settings.model_copy(update={"max_jobs_per_day": 1, "max_tokens_per_day": 5})
    first = enqueue(engine, settings, request())
    run_once(
        engine, settings, handlers(lambda ctx: (ctx.reserve(tokens=5), stub(ctx))[1]), clock=clock
    )
    second = enqueue(engine, settings, request("sql"))
    run_once(engine, settings, clock=clock)
    assert row(engine, second).error_code == "budget_daily_jobs"
    clock.stamp += 86400
    third = enqueue(engine, settings, request("python"))
    run_once(engine, settings, clock=clock)
    assert row(engine, third).error_code == "stub_pipeline_complete"
    with Session(engine) as db:
        control = db.get(Control, "global")
        assert control.jobs_started == 1 and control.spent_tokens == 0
    assert row(engine, first).spent_tokens == 5


def test_stale_owner_cannot_commit_stage_records(engine, settings, clock):
    job_id = enqueue(engine, settings, request())

    def stolen(context):
        with Session(engine) as db, db.begin():
            db.get(Job, job_id).owner = "another-claim"
        return StageResult(
            {"result": 1},
            (
                Source(
                    skill_id=context.skill_id,
                    url="https://example.test/",
                    canonical_url="https://example.test/",
                    pipeline_version="m1",
                ),
            ),
        )

    run_once(engine, settings, handlers(stolen), clock=clock)
    assert row(engine, job_id).next_stage == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 0


def test_records_cannot_target_learner_tables(engine, settings, clock):
    job_id = enqueue(engine, settings, request())

    def bad(ctx):
        return StageResult({}, (User(issuer="test", subject="should-not-exist"),))

    run_once(engine, settings, handlers(bad), clock=clock)
    assert row(engine, job_id).next_stage == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_schema_rejects_raw_unknown_license_and_link_only_chunks(engine, settings):
    job_id = enqueue(engine, settings, request())
    skill_id = row(engine, job_id).skill_id
    with pytest.raises(IntegrityError), Session(engine) as db, db.begin():
        db.add(
            Source(
                skill_id=skill_id,
                url="https://example.test/",
                canonical_url="https://example.test/",
                raw_object_key="forbidden",
                pipeline_version="m1",
            )
        )
    with Session(engine) as db, db.begin():
        source = Source(
            skill_id=skill_id,
            url="https://example.test/",
            canonical_url="https://example.test/",
            pipeline_version="m1",
        )
        db.add(source)
        db.flush()
        source_id = source.id
    with pytest.raises(IntegrityError), Session(engine) as db, db.begin():
        db.add(
            Chunk(
                source_id=source_id,
                skill_id=skill_id,
                ordinal=0,
                text="forbidden",
                content_hash=digest({}),
                pipeline_version="m1",
                attribution_text="test",
            )
        )


def test_invalid_input_and_hashes_are_rejected():
    with pytest.raises(ValidationError):
        request("../escape")
    with pytest.raises(ValueError):
        digest({"bad": float("nan")})
    with pytest.raises(ValueError, match="too_large"):
        digest({"large": "x" * 65536})


def test_repeated_process_crashes_are_parked(engine, settings, clock):
    job_id = enqueue(engine, settings, request())

    class Crash(BaseException):
        pass

    def crash(context):
        raise Crash()

    for _ in range(settings.max_attempts):
        with pytest.raises(Crash):
            run_once(engine, settings, handlers(crash), clock=clock)
        clock.stamp += settings.lease_seconds
    assert not run_once(engine, settings, handlers(crash), clock=clock)
    assert row(engine, job_id).error_code == "attempts_exhausted"


def test_settings_kill_and_pipeline_change_park_before_stages(engine, settings, clock):
    killed = enqueue(engine, settings, request())
    assert not run_once(engine, settings.model_copy(update={"kill_switch": True}), clock=clock)
    assert row(engine, killed).error_code == "kill_switch"
    changed = enqueue(engine, settings, request("sql"))
    assert not run_once(
        engine, settings.model_copy(update={"pipeline_version": "changed"}), clock=clock
    )
    assert row(engine, changed).error_code == "pipeline_version_changed"


def test_forged_owner_fails_before_reservation(engine, settings, clock):
    job_id = enqueue(engine, settings, request())
    with claim(engine, settings, clock) as lease:
        from socrat.foundry.jobs import LeaseLost, StageContext

        context = StageContext(
            replace(lease, owner="wrong"), settings, clock, "S0", row(engine, job_id).skill_id, {}
        )
        with pytest.raises(LeaseLost):
            context.reserve(tokens=1)


def test_worker_cli_is_offline_and_disabled_by_default(monkeypatch, engine):
    import sys

    from socrat.foundry import worker

    monkeypatch.setattr(sys, "argv", ["foundry", "--once"])
    monkeypatch.setattr(worker, "FoundrySettings", lambda: FoundrySettings(_env_file=None))
    with pytest.raises(SystemExit, match="2"):
        worker.main()
    monkeypatch.setattr(
        worker, "FoundrySettings", lambda: FoundrySettings(_env_file=None, enabled=True)
    )
    monkeypatch.setattr(worker, "make_engine", lambda _: engine)
    monkeypatch.setattr(sys, "argv", ["foundry", "--once", "--stub-skill", "sql-basics"])
    worker.main()
    with Session(engine) as db:
        job = db.scalar(select(Job))
        assert job.error_code == "stub_pipeline_complete"
        assert job.spent_tokens == job.spent_docs == 0
