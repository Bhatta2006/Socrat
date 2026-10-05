"""Opt-in dedicated-host gates. Never substitute Docker Desktop/runc for runsc."""

import json
import os
import time
from pathlib import Path

import pytest
from runner.corpus import source
from runner.docker_backend import DockerBackend

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

pytestmark = pytest.mark.skipif(
    os.environ.get("SOCRAT_EXECUTION_GATE") != "true",
    reason="Requires an attested dedicated gVisor execution host",
)


@pytest.fixture(scope="module")
def sandbox():
    profiles = [
        RuntimeProfile.model_validate(x)
        for x in json.loads(Path(os.environ["SOCRAT_EXECUTION_GATE_PROFILE_FILE"]).read_text())
    ]
    assert {x.language for x in profiles} == {"python", "cpp", "java"}
    backend = DockerBackend(profiles, os.environ["SOCRAT_EXECUTION_COSIGN_PUBLIC_KEY"])
    backend.preflight()
    return backend, {x.language: x for x in profiles}


def envelope(profile, program, stdin="", expected=None):
    tests = [TestInput(input=stdin, expected=expected, visibility="public")]
    stamp = int(time.time())
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=identifier(),
        nonce="a" * 64,
        issued_at=stamp,
        expires_at=stamp + 600,
        language=profile.language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(program.encode()),
        test_digest=hashed(canonical([x.model_dump() for x in tests])),
        pack_digest="sha256:" + "b" * 64,
        mode="run",
        limits=profile.limits,
        compile_config=COMMANDS[profile.language],
    )
    return JobEnvelope(
        manifest=manifest,
        signature=sign(manifest.model_dump(), "gate-only"),
        source=program,
        tests=tests,
    )


@pytest.mark.parametrize("language", ["python", "cpp", "java"])
@pytest.mark.parametrize("case", ["cpu", "memory", "output", "disk", "fork", "timing", "probes"])
def test_malicious_corpus(sandbox, language, case):
    backend, profiles = sandbox
    result = backend.execute(
        envelope(
            profiles[language],
            source(language, case),
            expected="isolated" if case == "probes" else None,
        )
    )[0]
    if case == "probes":
        assert result.status == "passed", result
    elif case == "output":
        assert result.status == "output_limit", result
    else:
        assert result.status in {"memory_limit", "runtime_error", "timeout"}, result
    # A subsequent job proves cleanup and that an attack cannot poison the next sandbox.
    assert (
        backend.execute(envelope(profiles[language], source(language, "semantic"), "3", "6"))[
            0
        ].status
        == "passed"
    )


@pytest.mark.parametrize(
    "stdin,expected", [("0", "0"), ("-17", "-34"), ("2147483647", "4294967294")]
)
def test_cross_language_semantics(sandbox, stdin, expected):
    backend, profiles = sandbox
    for language, profile in profiles.items():
        assert (
            backend.execute(envelope(profile, source(language, "semantic"), stdin, expected))[
                0
            ].status
            == "passed"
        )
