"""Demo isolation, original inventory, real sandbox arguments, and clock boundaries."""

import time

import pytest
from pydantic import ValidationError
from runner.demo_backend import DemoDockerBackend, demo_container_args
from runner.docker_backend import container_args

from socrat.clock import demo_offset, now
from socrat.config import Settings
from socrat.demo.content import validated_pack
from socrat.demo.seed import seed
from socrat.execution.protocol import COMMANDS, JobEnvelope, JobManifest, Limits


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_demo_refused_outside_development(environment):
    with pytest.raises(ValidationError, match="only accepted in development"):
        Settings(_env_file=None, environment=environment, demo_mode=True)


@pytest.mark.parametrize(
    "environment,demo", [("development", False), ("test", False), ("production", True)]
)
def test_demo_backend_refused_without_both_guards(environment, demo):
    with pytest.raises(ValueError):
        DemoDockerBackend([], environment=environment, demo_mode=demo)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, environment=environment, demo_mode=demo, execution_backend="demo_docker"
        )


def test_production_backend_default_is_gvisor():
    settings = Settings(_env_file=None)
    assert settings.execution_backend == "gvisor_docker"
    assert not settings.demo_mode and not settings.execution_enabled
    with pytest.raises(ValueError, match="explicit development"):
        seed(settings)


def test_clock_unscoped_is_real_and_scoped_resets():
    wall = int(time.time())
    assert abs(now() - wall) <= 1
    token = demo_offset.set(7 * 86400)
    try:
        assert abs(now() - wall - 7 * 86400) <= 1
    finally:
        demo_offset.reset(token)
    assert abs(now() - wall) <= 1


def test_non_demo_app_never_reads_demo_clock(platform, monkeypatch):
    _, client = platform
    monkeypatch.setattr(
        "socrat.clock.offset_for", lambda engine: pytest.fail("Production read a demo clock")
    )
    assert client.get("/api/v1/features").json()["demo_mode"] is False
    assert client.get("/api/v1/demo/clock").status_code == 404
    assert client.get("/api/v1/auth/status").json() == {"profile": None}


def test_demo_sandbox_uses_same_hardening_without_runsc():
    stamp = int(time.time())
    manifest = JobManifest(
        job_id="00000000-0000-0000-0000-000000000001",
        attempt_id="00000000-0000-0000-0000-000000000002",
        nonce="1" * 64,
        issued_at=stamp,
        expires_at=stamp + 600,
        language="python",
        image="socrat/demo-python@sha256:" + "2" * 64,
        runtime_id="demo_python",
        code_hash="sha256:" + "3" * 64,
        test_digest="sha256:" + "4" * 64,
        pack_digest="sha256:" + "5" * 64,
        mode="submit",
        limits=Limits(),
        compile_config=COMMANDS["python"],
    )
    job = JobEnvelope(
        manifest=manifest,
        signature="1" * 64,
        source="print(1)",
        tests=[dict(input="", expected="1", visibility="public")],
    )
    production = container_args(job, "production")
    demo = demo_container_args(job, "demo")
    assert "--runtime=runsc" in production and "--runtime=runsc" not in demo
    for required in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--user=10001:10001",
        "--pids-limit=64",
        "--cpus=1",
    ):
        assert required in production and required in demo
    assert not any(x.startswith(("--mount", "--volume", "-v=")) for x in demo)
    assert "sha256:" + "2" * 64 in demo


def test_original_demo_inventory_passes_unchanged_audits():
    pack, audit = validated_pack(
        {x: "socrat/demo-" + x + "@sha256:" + "1" * 64 for x in ("python", "cpp", "java")}
    )
    assert audit["ready"] and len(audit["cells"]) == 9 and len(pack.concepts) >= 12
    assert len(pack.learning_lessons) == len(pack.concepts) * 9
    practice = {x.family_id for x in pack.exercises if x.inventory == "practice"}
    protected = {x.family_id for x in pack.exercises if x.inventory == "assessment"}
    assert not practice & protected
    for exercise in pack.exercises:
        if exercise.modality == "code":
            assert {x.language for x in exercise.variants} == {"python", "cpp", "java"}
            assert len(exercise.tests) >= 20


# Keep the existing migrated-fixture coverage rather than creating an unmigrated DB.
from test_foundation import platform as platform  # noqa: E402
