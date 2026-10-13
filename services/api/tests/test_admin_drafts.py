"""Content review queue: validate, request changes, approve into the course."""

import shutil
from pathlib import Path

import yaml
from test_learner_api import client, login  # noqa: F401  (client is a fixture)
from test_validate import problem

from socrat.catalog.registry import CONTENT_ROOT, load


def setup(client, tmp_path: Path) -> tuple[dict, Path, Path]:  # noqa: F811
    courses = tmp_path / "courses"
    shutil.copytree(CONTENT_ROOT, courses)
    drafts = tmp_path / "drafts" / "zero"
    drafts.mkdir(parents=True)
    draft = problem(id="triangle-total", concepts=["for-loops"])
    (drafts / "triangle-total.yaml").write_text(
        yaml.safe_dump(draft, sort_keys=False), encoding="utf-8"
    )
    settings = client.app.state.settings
    settings.content_courses_dir = str(courses)
    settings.content_drafts_dir = str(tmp_path / "drafts")
    settings.admin_subjects = ["editor"]
    return login(client, subject="editor", name="Grace Editor"), courses, drafts


def test_only_admins_see_the_queue(client, tmp_path):  # noqa: F811
    setup(client, tmp_path)
    login(client, subject="someone", name="Someone")
    assert client.get("/api/v1/admin/drafts").status_code == 403


def test_a_draft_is_validated_reviewed_and_approved_into_its_course(client, tmp_path):  # noqa: F811
    headers, courses, drafts = setup(client, tmp_path)
    queue = client.get("/api/v1/admin/drafts").json()
    assert queue["enabled"] and queue["items"][0]["status"] == "needs_validation"

    early = client.post("/api/v1/admin/drafts/triangle-total/approve", json={}, headers=headers)
    assert early.status_code == 409 and early.json()["error"]["code"] == "validate_first"

    checked = client.post("/api/v1/admin/drafts/triangle-total/validate", headers=headers).json()
    assert checked["status"] == "ready"
    assert {g["name"]: g["status"] for g in checked["validation"]["gates"]}["brute"] == "pass"

    asked = client.post(
        "/api/v1/admin/drafts/triangle-total/request-changes",
        json={"notes": "Make hint 2 less direct."},
        headers=headers,
    ).json()
    assert asked["status"] == "changes_requested" and asked["review"]["by"] == "Grace Editor"

    # Editing the draft clears both the old review and the old validation.
    path = drafts / "triangle-total.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("There is a formula.", "Think in pairs."),
        encoding="utf-8",
    )
    assert client.get("/api/v1/admin/drafts/triangle-total").json()["status"] == "needs_validation"
    client.post("/api/v1/admin/drafts/triangle-total/validate", headers=headers)

    approved = client.post(
        "/api/v1/admin/drafts/triangle-total/approve",
        json={"notes": "Clear and fair."},
        headers=headers,
    ).json()
    assert approved["review"]["by"] == "Grace Editor"
    assert not path.exists()
    shipped = yaml.safe_load(
        (courses / "zero" / "problems" / "triangle-total.yaml").read_text(encoding="utf-8")
    )
    assert shipped["review"]["notes"] == "Clear and fair."
    concept = (courses / "zero" / "concepts" / "for-loops.yaml").read_text(encoding="utf-8")
    assert "triangle-total" in concept
    catalog = load(courses, tests_root=None)  # the course still loads with the new problem
    assert catalog.problem("triangle-total").review.by == "Grace Editor"
    assert client.get("/api/v1/admin/drafts").json()["items"] == []


def test_failing_gates_block_approval(client, tmp_path):  # noqa: F811
    headers, _, drafts = setup(client, tmp_path)
    path = drafts / "triangle-total.yaml"
    broken = problem(id="triangle-total", concepts=["for-loops"], brute="print(0)")
    path.write_text(yaml.safe_dump(broken, sort_keys=False), encoding="utf-8")
    checked = client.post("/api/v1/admin/drafts/triangle-total/validate", headers=headers).json()
    assert checked["status"] == "failing"
    blocked = client.post("/api/v1/admin/drafts/triangle-total/approve", json={}, headers=headers)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "gates_failing"
    assert client.get("/api/v1/admin/drafts/../secrets").status_code == 404
