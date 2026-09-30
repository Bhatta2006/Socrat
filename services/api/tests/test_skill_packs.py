"""M2 contract and release-path acceptance tests."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError


def manifest(key="logic", version="1.0.0"):
    reference = {
        "uri": "fixture://release-check",
        "sha256": "0" * 64,
        "summary": "Synthetic evidence reference for API contract tests only",
    }
    return {
        "contract_version": 2,
        "release_stage": "candidate",
        "key": key,
        "version": version,
        "name": "Reasoning basics",
        "domain": "reasoning",
        "evidence_modalities": ["explain", "trace"],
        "language_adapters": [],
        "concepts": [
            {
                "key": "premises",
                "name": "Premises",
                "competency": "Identify premises in a short argument",
                "scope": "Short written arguments",
                "exclusions": [],
                "objectives": ["Distinguish a premise from a conclusion"],
                "evidence_modes": ["explain"],
                "prerequisites": [],
                "misconceptions": [],
                "mastery": {
                    "min_independent": 2,
                    "min_diverse_modes": 1,
                    "assessment_required": True,
                    "retention_days": 7,
                },
                "expected_minutes": 20,
                "accessibility_notes": "Text equivalent available",
                "author": "fixture-author",
                "provenance": "Original Socrat fixture",
            },
            {
                "key": "conclusions",
                "name": "Conclusions",
                "competency": "Identify a conclusion supported by premises",
                "scope": "Short written arguments",
                "exclusions": [],
                "objectives": ["Identify a supported conclusion"],
                "evidence_modes": ["explain", "trace"],
                "prerequisites": [
                    {
                        "key": "premises",
                        "threshold": 0.6,
                        "strength": "required",
                        "rationale": "Premises must be identified first",
                    }
                ],
                "misconceptions": [],
                "mastery": {
                    "min_independent": 2,
                    "min_diverse_modes": 2,
                    "assessment_required": True,
                    "retention_days": 7,
                },
                "expected_minutes": 20,
                "accessibility_notes": "Text equivalent available",
                "author": "fixture-author",
                "provenance": "Original Socrat fixture",
            },
        ],
        "goal_templates": [
            {
                "key": "argument-basics",
                "track": "foundations",
                "outcome": "Identify premises and conclusions independently",
                "required_concepts": ["premises", "conclusions"],
            }
        ],
        "track_policies": [
            {
                "key": "foundations",
                "goal_keys": ["argument-basics"],
                "required_concepts": ["premises", "conclusions"],
                "optional_concepts": [],
                "languages": [],
                "difficulty_ceiling": 1,
            }
        ],
        "coverage": [{"track": "foundations", "language": None, "status": "released"}],
        "release_evidence": {
            "rights": reference,
            "accessibility": reference,
            "concept_quality": reference,
            "exercise_quality": reference,
            "assessment_separation": reference,
            "canary": reference,
        },
        "content": [
            {
                "key": "premise-lesson",
                "kind": "lesson",
                "concept_keys": ["premises"],
                "evidence_modes": ["explain"],
                "language_variants": [],
                "title": "Find a premise",
                "source": {
                    "author": "Socrat",
                    "license": "original",
                    "rights_checked_at": "2026-09-30",
                },
                "accessibility_notes": "Plain text",
            }
        ],
        "assessment_blueprints": [
            {
                "key": "argument-check",
                "track": "foundations",
                "concept_keys": ["premises", "conclusions"],
                "evidence_modes": ["explain", "trace"],
            }
        ],
    }


def test_candidate_requires_complete_explicit_coverage_and_evidence():
    from socrat.skill_packs import PackManifest

    valid = manifest()
    assert PackManifest.model_validate(valid).coverage[0].status == "released"

    missing = deepcopy(valid)
    missing["coverage"] = []
    with pytest.raises(ValidationError, match="coverage must declare"):
        PackManifest.model_validate(missing)

    draft_cell = deepcopy(valid)
    draft_cell["coverage"][0]["status"] = "draft"
    with pytest.raises(ValidationError, match="draft coverage"):
        PackManifest.model_validate(draft_cell)

    no_proof = deepcopy(valid)
    no_proof["release_evidence"] = None
    with pytest.raises(ValidationError, match="evidence bundle"):
        PackManifest.model_validate(no_proof)

    unavailable = deepcopy(valid)
    unavailable["coverage"][0]["status"] = "unavailable"
    with pytest.raises(ValidationError, match="needs a reason"):
        PackManifest.model_validate(unavailable)
    unavailable["coverage"][0]["reason"] = "No reviewed content for this track"
    PackManifest.model_validate(unavailable)


def test_removed_concepts_require_explicit_version_mapping():
    from socrat.skill_packs import PackManifest, verify_concept_migration

    old = PackManifest.model_validate(manifest(version="1.0.0"))
    updated = manifest(version="1.1.0")
    updated["concepts"][0]["key"] = "grounds"
    updated["concepts"][1]["prerequisites"][0]["key"] = "grounds"
    updated["goal_templates"][0]["required_concepts"][0] = "grounds"
    updated["track_policies"][0]["required_concepts"][0] = "grounds"
    updated["content"][0]["concept_keys"][0] = "grounds"
    updated["assessment_blueprints"][0]["concept_keys"][0] = "grounds"
    current = PackManifest.model_validate(updated)
    with pytest.raises(ValueError, match="every removed key"):
        verify_concept_migration(old, current)

    updated["migration_from_version"] = "1.0.0"
    updated["concept_mappings"] = [
        {
            "old_key": "premises",
            "new_keys": ["grounds"],
            "disposition": "replaced",
            "rationale": "The same learner evidence transfers to the renamed concept",
        }
    ]
    verify_concept_migration(old, PackManifest.model_validate(updated))


def test_manifest_rejects_invalid_graph_and_overlay():
    from socrat.skill_packs import PackManifest

    valid = manifest()
    assert PackManifest.model_validate(valid).key == "logic"

    cycle = deepcopy(valid)
    cycle["concepts"][0]["prerequisites"] = [
        {"key": "conclusions", "threshold": 0.6, "strength": "required", "rationale": "bad"}
    ]
    with pytest.raises(ValidationError, match="cycle"):
        PackManifest.model_validate(cycle)

    missing = deepcopy(valid)
    missing["track_policies"][0]["required_concepts"] = ["conclusions"]
    with pytest.raises(ValidationError, match="prerequisite closure"):
        PackManifest.model_validate(missing)

    invalid_mode = deepcopy(valid)
    invalid_mode["evidence_modalities"] = ["telepathy"]
    with pytest.raises(ValidationError):
        PackManifest.model_validate(invalid_mode)


def test_exported_schema_matches_runtime_model():
    from socrat.skill_packs import PackManifest

    path = Path("contracts/schemas/skill-pack.schema.json")
    assert json.loads(path.read_text(encoding="utf-8")) == PackManifest.model_json_schema()


def test_manifest_rejects_unknown_references_and_assessment_exposure():
    from socrat.skill_packs import PackManifest

    bad = manifest()
    bad["concepts"][1]["prerequisites"][0]["key"] = "missing"
    with pytest.raises(ValidationError, match="unknown prerequisite"):
        PackManifest.model_validate(bad)

    bad = manifest()
    bad["content"][0]["kind"] = "assessment"
    bad["content"][0]["language_variants"] = ["python"]
    with pytest.raises(ValidationError, match="language adapter"):
        PackManifest.model_validate(bad)


def test_manifest_rejects_transitive_prerequisite_gap_and_duplicate_overlay():
    from socrat.skill_packs import PackManifest

    bad = manifest()
    third = deepcopy(bad["concepts"][1])
    third["key"] = "synthesis"
    third["prerequisites"][0]["key"] = "conclusions"
    bad["concepts"].append(third)
    bad["track_policies"][0]["required_concepts"] = ["synthesis"]
    bad["track_policies"][0]["optional_concepts"] = ["conclusions"]
    bad["goal_templates"][0]["required_concepts"] = ["synthesis"]
    bad["assessment_blueprints"][0]["concept_keys"] = ["synthesis"]
    with pytest.raises(ValidationError, match="prerequisite closure"):
        PackManifest.model_validate(bad)

    bad = manifest()
    bad["track_policies"][0]["optional_concepts"] = ["premises"]
    with pytest.raises(ValidationError, match="overlap"):
        PackManifest.model_validate(bad)


def test_manifest_rejects_content_or_assessment_mode_outside_concept_contract():
    from socrat.skill_packs import PackManifest

    bad = manifest()
    bad["evidence_modalities"].append("implement")
    bad["content"][0]["evidence_modes"] = ["implement"]
    with pytest.raises(ValidationError, match="content mode"):
        PackManifest.model_validate(bad)

    bad = manifest()
    bad["evidence_modalities"].append("implement")
    bad["assessment_blueprints"][0]["evidence_modes"] = ["implement"]
    with pytest.raises(ValidationError, match="assessment mode"):
        PackManifest.model_validate(bad)


@pytest.fixture
def content_platform(platform):
    from sqlalchemy.orm import Session
    from test_foundation import login

    from socrat.models import ContentOperator, User

    app, client = platform
    for subject, roles in {
        "author": ["author"],
        "domain": ["domain_reviewer"],
        "learning": ["learning_reviewer"],
        "access": ["accessibility_reviewer"],
        "rights": ["rights_reviewer"],
        "assessment": ["assessment_reviewer"],
        "release": ["release_owner"],
    }.items():
        login(client, subject)
        with Session(app.state.engine) as db, db.begin():
            user = db.get(User, client.get("/api/v1/me").json()["id"])
            for role in roles:
                db.add(ContentOperator(user_id=user.id, role=role))
    yield app, client


def test_sample_dsa_and_non_dsa_packs_validate_through_same_contract():
    from socrat.skill_packs import PackManifest

    directory = Path("contracts/skill-packs")
    packs = [
        PackManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in (directory / "dsa-sample.json", directory / "non-dsa-fixture.json")
    ]
    assert [pack.key for pack in packs] == ["dsa", "argument-reasoning"]
    assert {track.key for track in packs[0].track_policies} == {
        "foundations",
        "interview",
        "competitive",
    }
    assert {adapter.language for adapter in packs[0].language_adapters} == {"python", "cpp", "java"}
    assert packs[1].language_adapters == []
    assert all(pack.release_stage == "draft" for pack in packs)


def test_both_draft_fixtures_import_through_admin_path(content_platform):
    _, client = content_platform
    for filename in ("dsa-sample.json", "non-dsa-fixture.json"):
        body = json.loads((Path("contracts/skill-packs") / filename).read_text(encoding="utf-8"))
        response = client.post(
            "/api/v1/admin/skill-packs", json=body, headers=as_actor(client, "author")
        )
        assert response.status_code == 201, response.text
        inspected = client.get(f"/api/v1/admin/skill-packs/{response.json()['id']}")
        assert inspected.status_code == 200
        assert inspected.json()["manifest"]["key"] == body["key"]
    assert client.get("/api/v1/skill-packs").json() == []


def as_actor(client, subject):
    from test_foundation import login

    login(client, subject)
    return {
        "Origin": "http://localhost:3000",
        "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"],
    }


def test_content_import_requires_operator_and_unique_version(content_platform):
    _, client = content_platform
    client.cookies.clear()
    assert client.get("/api/v1/admin/content-roles").status_code == 401
    headers = as_actor(client, "learner")
    assert client.get("/api/v1/admin/content-roles").json() == {"roles": []}
    assert (
        client.post("/api/v1/admin/skill-packs", json=manifest(), headers=headers).status_code
        == 403
    )
    assert client.get("/api/v1/admin/skill-packs").status_code == 403
    headers = as_actor(client, "author")
    assert client.get("/api/v1/admin/content-roles").json() == {"roles": ["author"]}
    imported = client.post("/api/v1/admin/skill-packs", json=manifest(), headers=headers)
    assert imported.status_code == 201, imported.text
    assert (
        client.post("/api/v1/admin/skill-packs", json=manifest(), headers=headers).status_code
        == 409
    )
    inventory = client.get("/api/v1/admin/skill-packs")
    assert inventory.status_code == 200
    assert inventory.json()[0]["id"] == imported.json()["id"]
    assert client.get("/api/v1/skill-packs").json() == []


def test_draft_and_author_self_review_cannot_publish(content_platform):
    from sqlalchemy.orm import Session

    from socrat.models import ContentOperator

    app, client = content_platform
    draft = manifest()
    draft["release_stage"] = "draft"
    draft["coverage"][0]["status"] = "draft"
    draft["release_evidence"] = None
    version_id = client.post(
        "/api/v1/admin/skill-packs", json=draft, headers=as_actor(client, "author")
    ).json()["id"]
    with Session(app.state.engine) as db, db.begin():
        author_id = client.get("/api/v1/me").json()["id"]
        db.add(ContentOperator(user_id=author_id, role="domain_reviewer"))
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/reviews",
            json={"role": "domain_reviewer", "decision": "approve", "note": "Reviewed contract"},
            headers=as_actor(client, "author"),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/publish",
            headers=as_actor(client, "release"),
        ).status_code
        == 409
    )


def test_assessment_blueprint_requires_assessment_review_before_publish(content_platform):
    _, client = content_platform
    version_id = client.post(
        "/api/v1/admin/skill-packs", json=manifest(), headers=as_actor(client, "author")
    ).json()["id"]
    for actor, role in (
        ("domain", "domain_reviewer"),
        ("learning", "learning_reviewer"),
        ("access", "accessibility_reviewer"),
        ("rights", "rights_reviewer"),
    ):
        reviewed = client.post(
            f"/api/v1/admin/skill-packs/{version_id}/reviews",
            json={"role": role, "decision": "approve", "note": "Reviewed release contract"},
            headers=as_actor(client, actor),
        )
        assert reviewed.status_code == 201, reviewed.text
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/publish",
            headers=as_actor(client, "release"),
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/reviews",
            json={
                "role": "assessment_reviewer",
                "decision": "approve",
                "note": "Blueprint reviewed",
            },
            headers=as_actor(client, "assessment"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/publish",
            headers=as_actor(client, "release"),
        ).status_code
        == 200
    )


def test_publish_is_reviewed_immutable_and_quarantine_rolls_back(content_platform):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from socrat.models import AuditEvent, PackQuarantine, PackVersion
    from socrat.skill_packs import load_pack_version

    app, client = content_platform
    version_ids = []
    for version in ("1.0.0", "1.1.0"):
        imported = client.post(
            "/api/v1/admin/skill-packs",
            json=manifest(version=version),
            headers=as_actor(client, "author"),
        )
        version_id = imported.json()["id"]
        version_ids.append(version_id)
        assert (
            client.post(
                f"/api/v1/admin/skill-packs/{version_id}/publish",
                headers=as_actor(client, "release"),
            ).status_code
            == 409
        )
        for actor, role in (
            ("domain", "domain_reviewer"),
            ("learning", "learning_reviewer"),
            ("access", "accessibility_reviewer"),
            ("rights", "rights_reviewer"),
            ("assessment", "assessment_reviewer"),
        ):
            response = client.post(
                f"/api/v1/admin/skill-packs/{version_id}/reviews",
                json={"role": role, "decision": "approve", "note": "Reviewed fixture contract"},
                headers=as_actor(client, actor),
            )
            assert response.status_code == 201, response.text
        as_actor(client, "author")
        inspection = client.get(f"/api/v1/admin/skill-packs/{version_id}").json()
        assert {review["role"] for review in inspection["reviews"]} == {
            "domain_reviewer",
            "learning_reviewer",
            "accessibility_reviewer",
            "rights_reviewer",
            "assessment_reviewer",
        }
        assert inspection["required_reviews"] == sorted(
            [
                "domain_reviewer",
                "learning_reviewer",
                "accessibility_reviewer",
                "rights_reviewer",
                "assessment_reviewer",
            ]
        )
        assert (
            client.post(
                f"/api/v1/admin/skill-packs/{version_id}/publish",
                headers=as_actor(client, "release"),
            ).status_code
            == 200
        )
    listing = client.get("/api/v1/skill-packs").json()
    assert listing[0]["version"] == "1.1.0"
    assert client.get("/api/v1/skill-packs/logic/versions/1.0.0").status_code == 200
    with Session(app.state.engine) as db:
        assert load_pack_version(db, "logic", "1.0.0").version == "1.0.0"
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_ids[1]}/quarantine",
            json={"reason": "Incorrect lesson discovered"},
            headers=as_actor(client, "release"),
        ).status_code
        == 200
    )
    assert client.get("/api/v1/skill-packs").json()[0]["version"] == "1.0.0"
    assert client.get("/api/v1/skill-packs/logic/versions/1.1.0").status_code == 404
    with Session(app.state.engine) as db:
        assert db.get(PackVersion, version_ids[1]).manifest["version"] == "1.1.0"
        kinds = db.scalars(select(AuditEvent.kind)).all()
        assert "skill_pack.published" in kinds
        assert "skill_pack.quarantined" in kinds
        assert "skill_pack.rollback_activated" in kinds
        assert db.scalar(select(PackQuarantine.reason)) == "Incorrect lesson discovered"


def test_item_quarantine_excludes_item_from_runtime_load(content_platform):
    from sqlalchemy.orm import Session

    from socrat.skill_packs import load_active_pack, load_eligible_pack

    app, client = content_platform
    imported = client.post(
        "/api/v1/admin/skill-packs", json=manifest(), headers=as_actor(client, "author")
    )
    version_id = imported.json()["id"]
    for actor, role in (
        ("domain", "domain_reviewer"),
        ("learning", "learning_reviewer"),
        ("access", "accessibility_reviewer"),
        ("rights", "rights_reviewer"),
        ("assessment", "assessment_reviewer"),
    ):
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/reviews",
            json={"role": role, "decision": "approve", "note": "Reviewed fixture contract"},
            headers=as_actor(client, actor),
        )
    client.post(
        f"/api/v1/admin/skill-packs/{version_id}/publish", headers=as_actor(client, "release")
    )
    with Session(app.state.engine) as db:
        eligible = load_eligible_pack(db, "logic", "foundations", None)
        assert eligible is not None
        assert [item.key for item in eligible.content] == ["premise-lesson"]
        assert load_eligible_pack(db, "logic", "foundations", "python") is None
    response = client.post(
        f"/api/v1/admin/skill-packs/{version_id}/items/premise-lesson/quarantine",
        json={"reason": "Incorrect explanation"},
        headers=as_actor(client, "release"),
    )
    assert response.status_code == 200, response.text
    with Session(app.state.engine) as db:
        loaded = load_active_pack(db, "logic")
        assert loaded is not None
        assert loaded.content == []
        eligible = load_eligible_pack(db, "logic", "foundations", None)
        assert eligible is not None
        assert eligible.content == []


def test_runtime_loader_rejects_changed_published_payload(content_platform):
    from sqlalchemy.orm import Session

    from socrat.models import PackVersion
    from socrat.skill_packs import load_active_pack

    app, client = content_platform
    imported = client.post(
        "/api/v1/admin/skill-packs", json=manifest(), headers=as_actor(client, "author")
    )
    version_id = imported.json()["id"]
    for actor, role in (
        ("domain", "domain_reviewer"),
        ("learning", "learning_reviewer"),
        ("access", "accessibility_reviewer"),
        ("rights", "rights_reviewer"),
        ("assessment", "assessment_reviewer"),
    ):
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/reviews",
            json={"role": role, "decision": "approve", "note": "Reviewed fixture contract"},
            headers=as_actor(client, actor),
        )
    assert (
        client.post(
            f"/api/v1/admin/skill-packs/{version_id}/publish", headers=as_actor(client, "release")
        ).status_code
        == 200
    )
    with Session(app.state.engine) as db, db.begin():
        version = db.get(PackVersion, version_id)
        version.manifest = {**version.manifest, "name": "Tampered content"}
    with Session(app.state.engine) as db:
        with pytest.raises(ValueError, match="integrity"):
            load_active_pack(db, "logic")


def test_database_prevents_two_active_versions_of_same_pack(content_platform):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    from socrat.models import PackVersion

    app, client = content_platform
    ids = []
    for name in ("1.0.0", "1.1.0"):
        result = client.post(
            "/api/v1/admin/skill-packs",
            json=manifest(version=name),
            headers=as_actor(client, "author"),
        )
        ids.append(result.json()["id"])
    with Session(app.state.engine) as db:
        for version_id in ids:
            version = db.get(PackVersion, version_id)
            version.is_active = True
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_release_history_migration_preserves_existing_pack_versions(tmp_path):
    import sqlite3

    from alembic import command
    from alembic.config import Config

    database = tmp_path / "existing-m2.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0002")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("user-1", "test", "author", "Author", "UTC", 1, 0),
        )
        connection.execute(
            "INSERT INTO pack_versions (id, pack_key, version, digest, manifest, author_id, "
            "status, is_active, created_at, published_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("pack-1", "logic", "1.0.0", "digest", "{}", "user-1", "draft", 0, 0, None),
        )
    command.upgrade(config, "head")
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0003",)
        assert connection.execute(
            "SELECT id, pack_key, version, previous_active_id FROM pack_versions"
        ).fetchone() == ("pack-1", "logic", "1.0.0", None)


def test_quarantine_restores_previous_active_release_not_highest_version(content_platform):
    """Emergency rollback follows publication history even if versions arrived out of order."""
    _, client = content_platform
    last_id = ""
    release_ids = {}
    for version in ("1.0.0", "3.0.0", "2.0.0", "1.5.0"):
        imported = client.post(
            "/api/v1/admin/skill-packs",
            json=manifest(version=version),
            headers=as_actor(client, "author"),
        )
        assert imported.status_code == 201, imported.text
        last_id = imported.json()["id"]
        release_ids[version] = last_id
        for actor, role in (
            ("domain", "domain_reviewer"),
            ("learning", "learning_reviewer"),
            ("access", "accessibility_reviewer"),
            ("rights", "rights_reviewer"),
            ("assessment", "assessment_reviewer"),
        ):
            reviewed = client.post(
                f"/api/v1/admin/skill-packs/{last_id}/reviews",
                json={"role": role, "decision": "approve", "note": "Reviewed release contract"},
                headers=as_actor(client, actor),
            )
            assert reviewed.status_code == 201, reviewed.text
        published = client.post(
            f"/api/v1/admin/skill-packs/{last_id}/publish",
            headers=as_actor(client, "release"),
        )
        assert published.status_code == 200, published.text

    rollback = client.post(
        f"/api/v1/admin/skill-packs/{last_id}/quarantine",
        json={"reason": "Incorrect content reached learners"},
        headers=as_actor(client, "release"),
    )
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["active_version"] == "2.0.0"
    assert client.get("/api/v1/skill-packs").json()[0]["version"] == "2.0.0"

    inactive = client.post(
        f"/api/v1/admin/skill-packs/{release_ids['3.0.0']}/quarantine",
        json={"reason": "Earlier release also has a defect"},
        headers=as_actor(client, "release"),
    )
    assert inactive.status_code == 200, inactive.text
    assert inactive.json()["active_version"] is None
    rollback = client.post(
        f"/api/v1/admin/skill-packs/{release_ids['2.0.0']}/quarantine",
        json={"reason": "Current release must be rolled back"},
        headers=as_actor(client, "release"),
    )
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["active_version"] == "1.0.0"
