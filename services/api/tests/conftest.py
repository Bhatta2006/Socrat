"""Shared migrated API fixture for platform and content acceptance tests."""

import pytest


@pytest.fixture
def platform(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'test.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    settings = Settings(database_url=url, environment="test", dev_login_enabled=True)
    app = create_app(settings)
    with TestClient(app, base_url="http://localhost:3000") as client:
        yield app, client
    app.state.engine.dispose()
