import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

from socrat.database import make_engine
from socrat.foundry.config import FoundrySettings


def migrate(url: str, revision: str = "head"):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, revision)
    return config


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'foundry.db'}"
    migrate(url)
    db_engine = make_engine(url)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def settings():
    return FoundrySettings(_env_file=None, enabled=True)


@pytest.fixture
def clock():
    class Clock:
        stamp = 1_800_000_000

        def __call__(self):
            return self.stamp

    return Clock()


@pytest.fixture
def postgres_engine(monkeypatch):
    url = os.environ.get("SOCRAT_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set SOCRAT_TEST_POSTGRES_URL for isolated PostgreSQL integration tests")
    admin = make_engine(url)
    schema = "foundry_test_" + uuid4().hex
    try:
        with admin.begin() as db:
            db.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
        scoped_url = scoped.render_as_string(hide_password=False)
        monkeypatch.setenv("SOCRAT_DATABASE_URL", scoped_url)
        migrate(scoped_url)
        db_engine = make_engine(scoped_url)
        try:
            yield db_engine
        finally:
            db_engine.dispose()
    finally:
        # This random schema is created by this fixture; never drop the supplied database.
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()
