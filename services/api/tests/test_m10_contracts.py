import importlib.util
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform

from socrat.accountability.preferences import PreferencesUpdate
from socrat.accountability.routes import CleanupInput, DeferInput, DeleteInput
from socrat.models import User


def test_m10_exported_schemas_match_runtime():
    for name, contract in (
        ("preferences-update", PreferencesUpdate),
        ("privacy-delete", DeleteInput),
        ("privacy-cleanup", CleanupInput),
        ("assessment-deferral", DeferInput),
    ):
        assert (
            json.loads(Path(f"contracts/schemas/{name}.schema.json").read_text())
            == contract.model_json_schema()
        )


def test_restore_erasure_manifest_scrubs_before_traffic(platform):
    app, client = platform
    login(client)
    owner = client.get("/api/v1/me").json()["id"]
    spec = importlib.util.spec_from_file_location(
        "restore_erasure", "scripts/operations/reapply-erasure.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.reapply(app.state.engine, [owner]) == 1
    assert module.reapply(app.state.engine, [owner]) == 0
    assert client.get("/api/v1/me").status_code == 401
    with Session(app.state.engine) as db:
        assert db.scalar(select(User).where(User.id == owner)) is None
