"""Real PostgreSQL migration, release locking, and transactional delivery rehearsal.

CI supplies an isolated database service; local runs skip if no URL is supplied.
"""

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from socrat.models import (
    ContentReview,
    DeliveredEvent,
    OutboxEvent,
    SkillPackHead,
    SkillPackVersion,
    User,
)
from socrat.skillpacks.schema import SkillPack
from socrat.skillpacks.service import import_pack, transition
from socrat.worker import drain_once

POSTGRES_URL = os.environ.get("SOCRAT_TEST_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="No isolated PostgreSQL service configured"
)
FIXTURES = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "skill-packs"


@pytest.fixture
def postgres_kernel():
    admin = create_engine(POSTGRES_URL, isolation_level="AUTOCOMMIT")
    database = f"socrat_m2_{uuid.uuid4().hex}"
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    url = admin.url.set(database=database).render_as_string(hide_password=False)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        command.upgrade(config, "head")
        with Session(engine) as db, db.begin():
            author = User(issuer="synthetic-test", subject="author")
            reviewer = User(issuer="synthetic-test", subject="reviewer")
            db.add_all([author, reviewer])
            db.flush()
            identities = author.id, reviewer.id
        yield engine, identities
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()


def test_postgres_serializes_release_pointers_and_preserves_immutable_content(postgres_kernel):
    engine, (author, reviewer) = postgres_kernel
    for name in ("dsa-1.0.0", "dsa-1.1.0"):
        pack = SkillPack.model_validate_json(
            (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
        )
        with Session(engine) as db, db.begin():
            record = import_pack(db, pack, author)
            for stage in ("technical_review", "learning_review", "language_verified", "staged"):
                transition(
                    db,
                    pack.key,
                    pack.version,
                    reviewer,
                    stage,
                    "synthetic-ci-review",
                    "Fixture only",
                    pack.languages,
                )
            assert record.status == "staged"
    barrier = Barrier(2)

    def publish(version):
        barrier.wait(timeout=10)
        with Session(engine) as db, db.begin():
            record = transition(
                db, "dsa", version, reviewer, "publish", "synthetic-ci-release", "Fixture only", []
            )
            return record.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        published = set(executor.map(publish, ("1.0.0", "1.1.0")))
    with Session(engine) as db:
        head = db.get(SkillPackHead, "dsa")
        assert {head.active_id, head.previous_id} == published
        assert (
            db.scalar(
                select(func.count())
                .select_from(ContentReview)
                .where(ContentReview.action == "publish")
            )
            == 2
        )
        with pytest.raises(DBAPIError):
            db.execute(
                update(SkillPackVersion)
                .where(SkillPackVersion.id == head.active_id)
                .values(payload={"tampered": True})
            )
        db.rollback()
        assert all(
            json.dumps(record.payload) != '{"tampered": true}'
            for record in db.scalars(select(SkillPackVersion))
        )


def test_postgres_parallel_outbox_workers_do_not_duplicate_delivery(postgres_kernel):
    engine, (author, _) = postgres_kernel
    with Session(engine) as db, db.begin():
        db.add_all(
            [
                OutboxEvent(kind="synthetic.concurrent", payload={"actor_id": author})
                for _ in range(150)
            ]
        )
    with ThreadPoolExecutor(max_workers=2) as executor:
        counts = list(executor.map(lambda _: drain_once(engine), range(2)))
    assert sum(counts) == 150
    assert drain_once(engine) == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DeliveredEvent)) == 150
