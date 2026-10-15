"""Opt-in database integration gates; each test owns a disposable PostgreSQL schema."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from alembic import command
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from socrat.foundry.jobs import STAGES, JobRequest, enqueue, run_once, stub
from socrat.foundry.models import Control, Job, Skill, StageRun
from socrat.models import User

from .conftest import migrate


def test_concurrent_requests_reuse_one_skill_and_job(postgres_engine, settings):
    request = JobRequest(slug="git", title="Git")
    with ThreadPoolExecutor(max_workers=4) as workers:
        ids = list(workers.map(lambda _: enqueue(postgres_engine, settings, request), range(8)))
    assert len(set(ids)) == 1
    with Session(postgres_engine) as db:
        assert db.scalar(select(func.count()).select_from(Skill)) == 1
        assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_advisory_lock_excludes_expired_but_still_running_worker(postgres_engine, settings, clock):
    job_id = enqueue(postgres_engine, settings, JobRequest(slug="git", title="Git"))
    entered, release = Event(), Event()

    def slow(context):
        entered.set()
        assert release.wait(10)
        return stub(context)

    stages = {**dict.fromkeys(STAGES, stub), "S0": slow}
    with ThreadPoolExecutor(max_workers=1) as workers:
        running = workers.submit(run_once, postgres_engine, settings, stages, clock=clock)
        try:
            assert entered.wait(10)
            clock.stamp += settings.lease_seconds
            assert not run_once(postgres_engine, settings, clock=clock)
            with Session(postgres_engine) as db:
                assert db.scalar(select(func.count()).select_from(StageRun)) == 0
        finally:
            release.set()
        assert running.result(timeout=10)
    # The old worker released its session advisory lock; the next claim can recover.
    assert run_once(postgres_engine, settings, clock=clock)
    with Session(postgres_engine) as db:
        assert db.get(Job, job_id).next_stage == len(STAGES)
        assert db.scalar(select(func.count()).select_from(StageRun)) == len(STAGES)


def test_global_token_reservations_are_atomic_across_workers(postgres_engine, settings, clock):
    settings = settings.model_copy(update={"max_tokens_per_day": 1})
    for slug in ("git", "sql"):
        enqueue(postgres_engine, settings, JobRequest(slug=slug, title=slug.title()))
    entered = Event()
    barrier = Barrier(2)

    def reserve(context):
        entered.set()
        barrier.wait(timeout=10)
        context.reserve(tokens=1)
        return stub(context)

    stages = {**dict.fromkeys(STAGES, stub), "S0": reserve}
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(run_once, postgres_engine, settings, stages, clock=clock)
        assert entered.wait(10)
        second = workers.submit(run_once, postgres_engine, settings, stages, clock=clock)
        assert first.result(timeout=15) and second.result(timeout=15)
    with Session(postgres_engine) as db:
        assert db.get(Control, "global").spent_tokens == 1
        assert set(db.scalars(select(Job.error_code))) == {
            "stub_pipeline_complete",
            "budget_daily_tokens",
        }
        assert sum(db.scalars(select(Job.spent_tokens))) == 1


def test_postgres_migration_roundtrip_preserves_users(postgres_engine):
    url = postgres_engine.url.render_as_string(hide_password=False)
    with Session(postgres_engine) as db, db.begin():
        db.add(User(id="preserved", issuer="fixture", subject="existing"))
    config = migrate(url)
    command.downgrade(config, "0007_learning_sessions")
    assert not any(
        name.startswith("foundry_") for name in inspect(postgres_engine).get_table_names()
    )
    with Session(postgres_engine) as db:
        assert db.get(User, "preserved").subject == "existing"
    command.upgrade(config, "head")
    assert (
        len(
            [
                name
                for name in inspect(postgres_engine).get_table_names()
                if name.startswith("foundry_")
            ]
        )
        == 12
    )
