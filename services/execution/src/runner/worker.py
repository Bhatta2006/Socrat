"""Execution-plane pull worker: authenticate, verify, isolate, and sign facts."""

import json
import os
import time

import httpx

from runner.docker_backend import DockerBackend, SandboxUnavailable
from socrat.execution.protocol import ExecutionResult, JobEnvelope, RuntimeProfile, sign


def execute(job: JobEnvelope, backend, secret: str, stamp: int):
    job.authenticate(secret, stamp)
    base = {
        key: job.manifest.model_dump()[key]
        for key in ("job_id", "nonce", "code_hash", "test_digest", "image")
    }
    try:
        cases = backend.execute(job)
        result = ExecutionResult(
            **base, operational_status="healthy", cases=cases, reason_code="execution_finalized"
        )
    except SandboxUnavailable:
        result = ExecutionResult(
            **base, operational_status="failed", cases=[], reason_code="worker_failure"
        )
    payload = result.model_dump()
    return {"result": payload, "signature": sign(payload, secret)}


def main():
    endpoint = os.environ["SOCRAT_EXECUTION_API_URL"].rstrip("/")
    secret = os.environ["SOCRAT_EXECUTION_SIGNING_SECRET"]
    worker_secret = os.environ["SOCRAT_EXECUTION_WORKER_SECRET"]
    worker_id = os.environ["SOCRAT_EXECUTION_WORKER_ID"]
    profiles = [
        RuntimeProfile.model_validate(x)
        for x in json.loads(os.environ["SOCRAT_EXECUTION_PROFILES"])
    ]
    if (
        not endpoint.startswith("https://")
        or len(secret) < 48
        or len(worker_secret) < 48
        or secret == worker_secret
    ):
        raise ValueError("Private HTTPS and distinct strong credentials required")
    backend = DockerBackend(profiles, os.environ["SOCRAT_EXECUTION_COSIGN_PUBLIC_KEY"])
    headers = {
        "Authorization": "Bearer " + worker_secret,
        "Origin": os.environ["SOCRAT_PUBLIC_ORIGIN"],
    }
    with httpx.Client(base_url=endpoint, headers=headers, timeout=15) as client:
        while True:
            backend.preflight()  # A failed verification never advertises a healthy runtime.
            client.post(
                "/api/v1/execution/worker/heartbeat",
                json={"worker_id": worker_id, "images": [x.image for x in profiles]},
            ).raise_for_status()
            response = client.post("/api/v1/execution/worker/claim", json={"worker_id": worker_id})
            response.raise_for_status()
            envelope = response.json()["job"]
            if envelope:
                job = JobEnvelope.model_validate(envelope)
                result = execute(job, backend, secret, int(time.time()))
                for retry in range(3):
                    try:
                        client.post(
                            "/api/v1/execution/worker/result",
                            json={"worker_id": worker_id, "envelope": result},
                        ).raise_for_status()
                        break
                    except httpx.TransportError:
                        if retry == 2:
                            raise
                        time.sleep(1)
            else:
                time.sleep(1)


if __name__ == "__main__":
    main()
