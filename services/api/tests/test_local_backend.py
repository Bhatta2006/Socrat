"""Real native Windows/POSIX execution, never simulated result callbacks."""

import time

import psutil
import pytest
from runner.local_backend import LocalProcessBackend
from runner.worker import execute

from socrat.execution.protocol import (
    COMMANDS,
    JobEnvelope,
    JobManifest,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
)
from socrat.models import identifier

SECRET = "native-test-signing-secret-" * 3


def envelope(source, language="python", **limits):
    profile = RuntimeProfile.model_validate(
        dict(
            id="local_" + language,
            language=language,
            image="socrat/local-" + language + "@sha256:" + "a" * 64,
            attestation_reference="Insecure local development toolchain",
            limits=dict(
                wall_seconds=2,
                compile_seconds=20,
                memory_mb=256,
                pids=8,
                output_bytes=4096,
                **limits,
            ),
        )
    )
    tests = [
        TestInput(input="2\n", expected="4", visibility="public"),
        TestInput(input="3\n", expected="6", visibility="hidden"),
    ]
    stamp = int(time.time())
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=identifier(),
        nonce="b" * 64,
        issued_at=stamp,
        expires_at=stamp + 600,
        language=language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(source.encode()),
        test_digest=hashed(canonical([x.model_dump() for x in tests])),
        pack_digest="sha256:" + "c" * 64,
        mode="submit",
        limits=profile.limits,
        compile_config=COMMANDS[language],
    )
    job = JobEnvelope(
        manifest=manifest, signature=sign(manifest.model_dump(), SECRET), source=source, tests=tests
    )
    return LocalProcessBackend([profile], environment="test", demo_mode=True), job


@pytest.mark.parametrize(
    "source,status",
    [
        ("print(int(input())*2)", "passed"),
        ("print(0)", "wrong_answer"),
        ("a=1\ndef broken(:\n  pass", "compile_error"),
        ("a=1\nraise ValueError('real traceback')", "runtime_error"),
        ("while True: pass", "timeout"),
        ("while True: print('X'*4096)", "output_limit"),
        ("x=bytearray(2_000_000_000)", "memory_limit"),
    ],
)
def test_native_python_results_and_cleanup(source, status, tmp_path):
    backend, job = envelope(source)
    backend.temp_root = tmp_path
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "healthy"
    assert [x["status"] for x in result["cases"]] == [status, status]
    assert result["cases"][1]["stdout"] == result["cases"][1]["stderr"] == ""
    assert not list(tmp_path.iterdir())
    if status == "compile_error":
        assert "line 2" in result["cases"][0]["stderr"]
    if status == "runtime_error":
        assert "line 2" in result["cases"][0]["stderr"]
    assert len(result["cases"][0]["stdout"]) <= 4096


def test_no_secrets_and_no_oracle_files(monkeypatch):
    monkeypatch.setenv("SOCRAT_EXECUTION_SIGNING_SECRET", "private-never-leak")
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "private-never-leak")
    source = "import os,pathlib\nassert not any('SOCRAT' in k or 'PRIVATE' in k for k in os.environ)\nassert sorted(x.name for x in pathlib.Path('.').iterdir()) == ['solution.py']\nprint(int(input())*2)"
    backend, job = envelope(source)
    assert all(x.status == "passed" for x in backend.execute(job))


def test_timeout_kills_descendants_and_spawn_is_contained(tmp_path):
    marker = "socrat-orphan-" + identifier()
    source = f"import subprocess,sys\nfor n in range(1000):\n subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(60)',{marker!r}])\nwhile True: pass"
    backend, job = envelope(source)
    backend.temp_root = tmp_path
    assert all(
        x.status in {"timeout", "runtime_error", "memory_limit"} for x in backend.execute(job)
    )
    time.sleep(0.1)
    for process in psutil.process_iter(["cmdline"]):
        assert marker not in " ".join(process.info["cmdline"] or [])
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "environment,demo",
    [("production", True), ("staging", True), ("development", False), ("test", False)],
)
def test_local_process_guard(environment, demo):
    with pytest.raises(ValueError, match="demo mode"):
        LocalProcessBackend([], environment=environment, demo_mode=demo)
