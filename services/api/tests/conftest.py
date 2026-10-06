"""Keep synthetic API tests independent of private developer deployment settings."""

import pytest

from socrat.config import DatabaseSettings, Settings


@pytest.fixture(autouse=True)
def isolate_private_dotenv(monkeypatch):
    # Explicit _env_file arguments remain usable by configuration tests.
    # Never load live credentials or rollout switches into synthetic fixtures.
    monkeypatch.setitem(DatabaseSettings.model_config, "env_file", None)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
