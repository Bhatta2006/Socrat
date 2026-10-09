"""Synthetic runtime profiles and secrets for execution tests."""

from socrat.execution.protocol import Limits, RuntimeProfile

SIGNING = "synthetic-signing-" + "a" * 64
WORKER = "synthetic-worker-" + "b" * 64


def profiles():
    return [
        RuntimeProfile(
            id=f"{language}_1",
            language=language,
            image=f"ghcr.io/socrat/{language}@sha256:{digit * 64}",
            limits=Limits(memory_mb=512 if language == "java" else 256),
            attestation_reference="synthetic-tests-only",
        ).model_dump()
        for language, digit in (("python", "1"), ("cpp", "2"), ("java", "3"))
    ]
