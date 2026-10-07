"""Execution-plane pull worker: authenticate, verify, isolate, and sign facts."""

import json
import os
import threading
import time

import httpx

from runner.backend import ExecutionBackend, make_backend
from runner.docker_backend import SandboxUnavailable
from socrat.execution.protocol import ExecutionResult, JobEnvelope, RuntimeProfile, sign


def execute(job: JobEnvelope, backend: ExecutionBackend, secret: str, stamp: int):
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
    demo = os.environ.get("SOCRAT_EXECUTION_BACKEND", "gvisor_docker") in {
        "demo_docker",
        "local_process",
    }
    if demo:
        from socrat.config import Settings

        settings = Settings()
        if not settings.demo_mode or settings.environment not in {"development", "test"}:
            raise ValueError("Demo worker requires explicit development/test demo mode")
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"api", "127.0.0.1", "localhost"}
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Demo worker requires a local API endpoint")
    if (
        (not demo and not endpoint.startswith("https://"))
        or len(secret) < 48
        or len(worker_secret) < 48
        or secret == worker_secret
    ):
        raise ValueError("Private HTTPS and distinct strong credentials required")
    if not demo:
        from socrat.config import Settings

        settings = Settings()
    backend = make_backend(settings)
    headers = {
        "Authorization": "Bearer " + worker_secret,
        "Origin": os.environ["SOCRAT_PUBLIC_ORIGIN"],
    }
    with httpx.Client(base_url=endpoint, headers=headers, timeout=15) as client:

        def beat():
            backend.preflight()
            images = (
                backend.available_images()
                if hasattr(backend, "available_images")
                else [x.image for x in profiles]
            )
            result = client.post(
                "/api/v1/execution/worker/heartbeat",
                json={"worker_id": worker_id, "images": images},
            )
            result.raise_for_status()
            return result

        # Dev jobs can contain many cases. Keep runtime availability honest while
        # executing them; leases and signed-result validation remain server-side.
        def background_heartbeat():
            while True:
                time.sleep(5)
                try:
                    beat()
                except (httpx.HTTPError, SandboxUnavailable):
                    pass  # Server expires health naturally; never claim success.

        if demo:
            threading.Thread(target=background_heartbeat, daemon=True).start()
        while True:
            heartbeat = beat()  # Failed verification never advertises a healthy runtime.
            clock_offset = (
                heartbeat.json().get("server_now", int(time.time())) - int(time.time())
                if demo
                else 0
            )
            response = client.post("/api/v1/execution/worker/claim", json={"worker_id": worker_id})
            if demo and response.status_code == 403:
                # Moving the shared demo clock can age out the heartbeat in the
                # milliseconds between heartbeat and claim. Re-authenticate and
                # advertise current health; do not loosen the broker's check.
                beat()
                continue
            response.raise_for_status()
            envelope = response.json()["job"]
            if envelope:
                job = JobEnvelope.model_validate(envelope)
                result = execute(job, backend, secret, int(time.time()) + clock_offset)
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
