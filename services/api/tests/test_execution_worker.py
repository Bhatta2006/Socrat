"""Trusted worker protocol and isolation controls; no learner source runs on this host."""

import json
import subprocess

import pytest
from m6_support import SIGNING, profiles
from runner.docker_backend import DockerBackend, SandboxUnavailable, container_args, cpu_usage
from runner.worker import execute

from socrat.execution.protocol import (
    COMMANDS,
    CaseResult,
    JobEnvelope,
    JobManifest,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
    verify,
)
from socrat.models import identifier


def job(source="print(4)"):
    profile = RuntimeProfile.model_validate(profiles()[0])
    tests = [TestInput(input="2", expected="4", visibility="public")]
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=identifier(),
        nonce="a" * 64,
        issued_at=100,
        expires_at=700,
        language=profile.language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(source.encode()),
        test_digest=hashed(canonical([x.model_dump() for x in tests])),
        pack_digest="sha256:" + "b" * 64,
        mode="run",
        limits=profile.limits,
        compile_config=COMMANDS[profile.language],
    )
    return JobEnvelope(
        manifest=manifest,
        signature=sign(manifest.model_dump(), SIGNING),
        source=source,
        tests=tests,
    )


def test_signature_expiry_and_artifact_tampering_never_execute():
    class Backend:
        def execute(self, envelope):
            pytest.fail("Invalid job reached a sandbox")

    envelope = job()
    with pytest.raises(ValueError, match="expired"):
        execute(envelope, Backend(), SIGNING, 701)
    envelope.source = "changed source"
    with pytest.raises(ValueError, match="artifact"):
        execute(envelope, Backend(), SIGNING, 100)


def test_signed_success_and_infrastructure_failure_are_distinct():
    class Backend:
        def execute(self, envelope):
            return [CaseResult(index=0, status="passed", wall_ms=1)]

    class Broken:
        def execute(self, envelope):
            raise SandboxUnavailable("no runsc")

    for backend, status in ((Backend(), "healthy"), (Broken(), "failed")):
        result = execute(job(), backend, SIGNING, 100)
        verify(result["result"], result["signature"], SIGNING)
        assert result["result"]["operational_status"] == status
        if status == "failed":
            assert result["result"]["cases"] == []


def test_no_runc_fallback_or_host_mounts_and_required_limits():
    args = container_args(job(), "synthetic")
    for flag in (
        "--runtime=runsc",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--user=10001:10001",
        "--memory=256m",
        "--memory-swap=256m",
        "--cpus=1",
        "--pids-limit=64",
        "--log-driver=none",
    ):
        assert flag in args
    assert not any("mount" in x or "docker.sock" in x or x in ("-v", "--volume") for x in args)
    backend = DockerBackend([RuntimeProfile.model_validate(profiles()[0])], "public-key")
    backend.command = lambda args: subprocess.CompletedProcess(
        args,
        0,
        stdout=json.dumps(
            {"Runtimes": {"runc": {}}, "MemoryLimit": True, "PidsLimit": True, "CPUQuota": True}
        ).encode(),
    )
    with pytest.raises(SandboxUnavailable):
        backend.preflight()


def test_signature_verification_failure_prevents_runtime_advertisement():
    backend = DockerBackend([RuntimeProfile.model_validate(profiles()[0])], "public-key")
    calls = []

    def command(args):
        calls.append(args)
        if args[0] == "cosign":
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "Runtimes": {"runsc": {}},
                    "MemoryLimit": True,
                    "PidsLimit": True,
                    "CPUQuota": True,
                    "CgroupVersion": "2",
                }
            ).encode(),
        )

    backend.command = command
    with pytest.raises(SandboxUnavailable):
        backend.preflight()
    assert len(calls) == 2


def test_cpu_accounting_requires_complete_cgroup_and_rejects_path_escape(tmp_path):
    proc = tmp_path / "proc"
    root = tmp_path / "cgroups"
    (proc / "42").mkdir(parents=True)
    (root / "job").mkdir(parents=True)
    mapping = proc / "42" / "cgroup"
    mapping.write_text("0::/job\n")
    (root / "job" / "cpu.stat").write_text(
        "usage_usec 2500000\nuser_usec 1500000\nsystem_usec 1000000\n"
    )
    assert cpu_usage(42, proc, root) == 2.5
    mapping.write_text("0::/../../outside\n")
    with pytest.raises(SandboxUnavailable, match="path"):
        cpu_usage(42, proc, root)
    mapping.write_text("2:cpu:/job\n")
    with pytest.raises(SandboxUnavailable, match="unified"):
        cpu_usage(42, proc, root)


def test_execution_schemas_match_runtime_contracts():
    from pathlib import Path

    from socrat.execution.protocol import ResultEnvelope

    for name, contract in (
        ("execution-job", JobEnvelope),
        ("execution-result", ResultEnvelope),
        ("execution-runtime", RuntimeProfile),
    ):
        assert (
            json.loads(Path(f"contracts/schemas/{name}.schema.json").read_text())
            == contract.model_json_schema()
        )


@pytest.mark.parametrize(
    "state,error,infrastructure_failure",
    [
        ("created", "", True),
        ("exited", "runsc failed", True),
        ("exited", "", False),
    ],
)
def test_sandbox_start_failure_never_becomes_learner_runtime_error(
    monkeypatch, state, error, infrastructure_failure
):
    monkeypatch.setattr("runner.docker_backend.time.time", lambda: 100)
    backend = DockerBackend([RuntimeProfile.model_validate(profiles()[0])], "public-key")
    backend.command = lambda args: subprocess.CompletedProcess(
        args, 0, stdout=json.dumps({"Status": state, "Error": error, "OOMKilled": False}).encode()
    )
    monkeypatch.setattr(
        "runner.docker_backend.capture", lambda *args: (1, b"", b"failure", False, False)
    )
    if infrastructure_failure:
        with pytest.raises(SandboxUnavailable):
            backend.execute(job())
    else:
        assert backend.execute(job())[0].status == "runtime_error"
