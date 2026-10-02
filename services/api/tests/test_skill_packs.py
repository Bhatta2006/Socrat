"""Skill-pack contract, editorial authorization, immutability, and recovery acceptance."""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_foundation import login
from test_foundation import platform as platform

from socrat.config import ContentAdminIdentity
from socrat.models import AuditEvent, ContentReview, OutboxEvent, SkillPackHead, SkillPackVersion
from socrat.skillpacks import cli
from socrat.skillpacks.schema import SkillPack
from socrat.skillpacks.service import import_pack, load

FIXTURES = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "skill-packs"


def fixture(name="dsa-1.0.0"):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def administrators(app):
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="local-development", subject=subject)
        for subject in ("author", "reviewer")
    ]


def headers(client, subject):
    login(client, subject)
    return {
        "Origin": "http://localhost:3000",
        "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"],
    }


def action(client, pack, name, auth, languages=None):
    return client.post(
        f"/api/v1/admin/skill-packs/{pack['key']}/versions/{pack['version']}/actions",
        json={
            "action": name,
            "evidence_reference": "synthetic-test-record",
            "reason": "Automated fixture only; not a human content approval.",
            "verified_languages": languages or [],
        },
        headers=auth,
    )


def release(client, pack, auth):
    for stage in ("technical_review", "learning_review", "language_verified", "staged", "publish"):
        response = action(
            client, pack, stage, auth, pack["languages"] if stage == "language_verified" else []
        )
        assert response.status_code == 200, response.text


@pytest.mark.parametrize("name", ["dsa-1.0.0", "dsa-1.1.0", "clear-writing-1.0.0"])
def test_domain_neutral_contract_and_determinism(name):
    pack = SkillPack.model_validate(fixture(name))
    reordered = dict(reversed(list(pack.model_dump(mode="json").items())))
    assert SkillPack.model_validate(reordered).digest() == pack.digest()
    assert pack.topological_order() == pack.topological_order()
    assert len(pack.topological_order()) == len(pack.concepts)


@pytest.mark.parametrize(
    "corruption",
    [
        "cycle",
        "missing_edge",
        "duplicate_id",
        "missing_overlay",
        "unknown_modality",
        "arbitrary_plugin",
        "shared_inventory",
        "missing_blueprint",
        "invalid_goal",
        "extra_language",
        "nan_mastery",
        "missing_prerequisite",
        "passive_mastery",
        "same_migration",
    ],
)
def test_invalid_contracts_fail_closed(corruption):
    data = fixture()
    if corruption == "cycle":
        edge = copy.deepcopy(data["edges"][0])
        edge["prerequisite"], edge["concept"] = edge["concept"], edge["prerequisite"]
        data["edges"].append(edge)
    elif corruption == "missing_edge":
        data["edges"][0]["prerequisite"] = "missing"
    elif corruption == "duplicate_id":
        data["concepts"].append(copy.deepcopy(data["concepts"][0]))
    elif corruption == "missing_overlay":
        data["tracks"][0]["concept_ids"].append("missing")
    elif corruption == "unknown_modality":
        data["modalities"] = ["shell"]
    elif corruption == "arbitrary_plugin":
        data["plugin"] = "import os; os.system('never execute')"
    elif corruption == "shared_inventory":
        data["exercises"][1]["family_id"] = data["exercises"][0]["family_id"]
    elif corruption == "missing_blueprint":
        data["blueprints"][0]["exercise_ids"] = ["missing"]
    elif corruption == "invalid_goal":
        data["goals"][0]["track_id"] = "missing"
    elif corruption == "extra_language":
        data["languages"] = ["python"]
    elif corruption == "nan_mastery":
        data["edges"][0]["minimum_mastery"] = float("nan")
    elif corruption == "missing_prerequisite":
        data["tracks"][0]["concept_ids"] = ["linear_search"]
    elif corruption == "passive_mastery":
        data["mastery_policy"]["passive_weight"] = 1
    else:
        data["migration"] = {
            "from_version": data["version"],
            "concept_mapping": {},
            "rationale": "Invalid self migration.",
        }
    with pytest.raises(ValidationError):
        SkillPack.model_validate(data)


def test_missing_language_variant_is_explicitly_unavailable():
    data = fixture()
    data["exercises"][0]["variants"] = data["exercises"][0]["variants"][:1]
    pack = SkillPack.model_validate(data)
    assert pack.variant_for("sum_sequence", "python") is not None
    assert pack.variant_for("sum_sequence", "java") is None
    assert pack.coverage()["sum_sequence"] == {"python": True, "cpp": False, "java": False}


def test_code_and_test_io_whitespace_is_preserved():
    data = fixture()
    source = "\n# Preserve source layout\ndef solve(values):\n    return sum(values)\n"
    data["exercises"][0]["variants"][0]["reference_solution"] = source
    data["exercises"][0]["tests"][0].update(input="", expected="  answer\n")
    pack = SkillPack.model_validate(data)
    assert pack.exercises[0].variants[0].reference_solution == source
    assert pack.exercises[0].tests[0].input == ""
    assert pack.exercises[0].tests[0].expected == "  answer\n"


def test_admin_requires_exact_identity_csrf_and_origin(platform):
    app, client = platform
    assert client.get("/api/v1/admin/skill-packs").status_code == 401
    author = headers(client, "author")
    assert (
        client.post("/api/v1/admin/skill-packs", json=fixture(), headers=author).status_code == 403
    )
    app.state.settings.content_admin_identities = [
        ContentAdminIdentity(issuer="wrong-issuer", subject="author")
    ]
    assert client.get("/api/v1/admin/skill-packs").status_code == 403
    administrators(app)
    assert (
        client.post(
            "/api/v1/admin/skill-packs", json=fixture(), headers={"Origin": author["Origin"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/admin/skill-packs",
            json=fixture(),
            headers={**author, "Origin": "https://wrong.invalid"},
        ).status_code
        == 403
    )
    assert (
        client.post("/api/v1/admin/skill-packs", json=fixture(), headers=author).status_code == 201
    )


def test_import_both_domains_idempotent_and_version_conflict(platform):
    app, client = platform
    administrators(app)
    auth = headers(client, "author")
    ids = []
    for name in ("dsa-1.0.0", "clear-writing-1.0.0"):
        response = client.post("/api/v1/admin/skill-packs", json=fixture(name), headers=auth)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    repeated = client.post("/api/v1/admin/skill-packs", json=fixture(), headers=auth)
    assert repeated.json()["id"] == ids[0]
    changed = fixture()
    changed["title"] = "Different content at same immutable version"
    assert client.post("/api/v1/admin/skill-packs", json=changed, headers=auth).status_code == 409
    invalid = fixture("dsa-1.1.0")
    invalid["migration"]["concept_mapping"]["missing_source"] = "linear_search"
    assert client.post("/api/v1/admin/skill-packs", json=invalid, headers=auth).status_code == 422
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(SkillPackVersion)) == 2
        events = db.scalars(select(OutboxEvent).where(OutboxEvent.kind == "content.imported")).all()
        assert len(events) == 2
        assert {event.payload["resource_id"] for event in events} == set(ids)
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.kind == "content.imported")
            )
            == 2
        )


def test_review_independence_language_gates_and_bad_content_rollback(platform):
    app, client = platform
    administrators(app)
    author = headers(client, "author")
    first = fixture()
    created = client.post("/api/v1/admin/skill-packs", json=first, headers=author).json()
    assert action(client, first, "technical_review", author).status_code == 403
    reviewer = headers(client, "reviewer")
    assert action(client, first, "publish", reviewer).status_code == 409
    assert action(client, first, "technical_review", reviewer).status_code == 200
    assert action(client, first, "learning_review", reviewer).status_code == 200
    assert action(client, first, "language_verified", reviewer, ["python"]).status_code == 422
    assert (
        action(client, first, "language_verified", reviewer, first["languages"]).status_code == 200
    )
    assert action(client, first, "staged", reviewer).status_code == 200
    assert action(client, first, "publish", reviewer).status_code == 200
    second = fixture("dsa-1.1.0")
    author = headers(client, "author")
    new = client.post("/api/v1/admin/skill-packs", json=second, headers=author).json()
    reviewer = headers(client, "reviewer")
    release(client, second, reviewer)
    assert action(client, first, "activate", reviewer).status_code == 200
    assert action(client, second, "activate", reviewer).status_code == 200
    assert action(client, second, "quarantine", reviewer).status_code == 200
    with Session(app.state.engine) as db:
        assert db.get(SkillPackHead, "dsa").active_id == created["id"]
        assert load(db.get(SkillPackVersion, new["id"])).digest() == new["digest"]
        assert db.get(SkillPackVersion, new["id"]).status == "quarantined"
    assert action(client, second, "activate", reviewer).status_code == 409
    assert action(client, first, "quarantine", reviewer).status_code == 200
    with Session(app.state.engine) as db:
        assert db.get(SkillPackHead, "dsa").active_id is None


def test_fixture_not_public_and_launch_manifest_has_no_protected_content(platform):
    app, client = platform
    administrators(app)
    author = headers(client, "author")
    first = fixture()
    client.post("/api/v1/admin/skill-packs", json=first, headers=author)
    reviewer = headers(client, "reviewer")
    release(client, first, reviewer)
    assert client.get("/api/v1/skill-packs").json() == {"items": []}
    launch = fixture()
    launch["key"], launch["purpose"] = "synthetic_launch", "launch"
    author = headers(client, "author")
    client.post("/api/v1/admin/skill-packs", json=launch, headers=author)
    reviewer = headers(client, "reviewer")
    release(client, launch, reviewer)
    response = client.get("/api/v1/skill-packs")
    assert len(response.json()["items"]) == 1
    for private in (
        "reference_solution",
        "rubric",
        "search_trace",
        "hidden",
        "evidence_reference",
        "starter_code",
    ):
        assert private not in response.text
    regular = headers(client, "learner")
    assert (
        client.get(
            "/api/v1/admin/skill-packs/synthetic_launch/versions/1.0.0", headers=regular
        ).status_code
        == 403
    )


def test_database_enforces_immutable_payload_and_append_only_reviews(platform):
    app, client = platform
    administrators(app)
    author = headers(client, "author")
    created = client.post("/api/v1/admin/skill-packs", json=fixture(), headers=author).json()
    reviewer = headers(client, "reviewer")
    assert action(client, fixture(), "technical_review", reviewer).status_code == 200
    with Session(app.state.engine) as db:
        with pytest.raises(IntegrityError):
            db.execute(
                update(SkillPackVersion)
                .where(SkillPackVersion.id == created["id"])
                .values(payload={"tampered": True})
            )
        db.rollback()
        row = db.scalar(select(ContentReview))
        with pytest.raises(IntegrityError):
            db.execute(
                update(ContentReview).where(ContentReview.id == row.id).values(reason="rewritten")
            )
        db.rollback()
        assert load(db.get(SkillPackVersion, created["id"])).digest() == created["digest"]


def test_import_rollback_leaves_no_content_or_events(platform):
    app, client = platform
    administrators(app)
    headers(client, "author")
    with Session(app.state.engine) as db:
        actor = client.get("/api/v1/me").json()["id"]
        import_pack(db, SkillPack.model_validate(fixture()), actor)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(SkillPackVersion)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.kind == "content.imported")
            )
            == 0
        )


def test_schema_artifact_matches_code():
    artifact = FIXTURES.parents[1] / "schemas" / "skill-pack.schema.json"
    assert json.loads(artifact.read_text(encoding="utf-8")) == SkillPack.model_json_schema()


def test_editorial_read_history_and_withdrawal_preserve_pinned_version(platform):
    app, client = platform
    administrators(app)
    author = headers(client, "author")
    assert client.get("/api/v1/admin/skill-packs/missing/versions/1.0.0").status_code == 404
    created = client.post(
        "/api/v1/admin/skill-packs", json=fixture("clear-writing-1.0.0"), headers=author
    ).json()
    reviewer = headers(client, "reviewer")
    pack = fixture("clear-writing-1.0.0")
    release(client, pack, reviewer)
    assert action(client, pack, "retire", reviewer).status_code == 200
    response = client.get("/api/v1/admin/skill-packs/clear_writing/versions/1.0.0")
    assert response.status_code == 200
    assert response.json()["digest"] == created["digest"]
    assert len(response.json()["reviews"]) == 6
    assert response.json()["status"] == "retired"
    assert len(client.get("/api/v1/admin/skill-packs").json()["items"]) == 1
    assert action(client, pack, "activate", reviewer).status_code == 409


def test_offline_cli_schema_export_and_private_validation(tmp_path, monkeypatch, capsys):
    import sys

    schema = tmp_path / "schema.json"
    monkeypatch.setattr(sys, "argv", ["skillpacks", "schema", str(schema)])
    assert cli.main() == 0
    assert json.loads(schema.read_text(encoding="utf-8")) == SkillPack.model_json_schema()
    monkeypatch.setattr(sys, "argv", ["skillpacks", "validate", str(FIXTURES / "dsa-1.0.0.json")])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["key"] == "dsa"
    bad = tmp_path / "invalid.json"
    bad.write_text('{"secret_value":"do-not-echo-this"}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["skillpacks", "validate", str(bad)])
    assert cli.main() == 1
    assert "do-not-echo-this" not in capsys.readouterr().out


def test_additive_migration_preserves_m1_identity_and_supports_development_downgrade(tmp_path):
    import sqlite3

    from alembic import command
    from alembic.config import Config

    database = tmp_path / "upgrade.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0001")
    with sqlite3.connect(database) as db:
        db.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("existing-m1-user", "synthetic-test", "existing", "Existing learner", "UTC", 1, 1),
        )
    command.upgrade(config, "head")
    with sqlite3.connect(database) as db:
        assert (
            db.execute(
                "SELECT display_name FROM users WHERE id = ?", ("existing-m1-user",)
            ).fetchone()[0]
            == "Existing learner"
        )
        from socrat.schema_revision import SCHEMA_REVISION

        assert (
            db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == SCHEMA_REVISION
        )
    command.downgrade(config, "0001")
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    command.upgrade(config, "head")
