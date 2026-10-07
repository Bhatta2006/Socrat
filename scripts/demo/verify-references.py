"""Run every original reference against its actual test bundle in the demo Docker sandbox."""

import argparse
import json
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src")]

from runner.demo_backend import DemoDockerBackend  # noqa: E402
from runner.local_backend import LocalProcessBackend  # noqa: E402
from runner.worker import execute  # noqa: E402

from socrat.demo.content import build_pack  # noqa: E402
from socrat.execution.protocol import (  # noqa: E402
    COMMANDS,
    JobEnvelope,
    JobManifest,
    RuntimeProfile,
    canonical,
    hashed,
    sign,
)
from socrat.models import identifier  # noqa: E402


def verify(exercise, variant, profile, backend, digest):
    tests = [x.model_dump() for x in exercise.tests]
    stamp = int(time.time())
    secret = secrets.token_hex(48)
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=identifier(),
        nonce=secrets.token_hex(32),
        issued_at=stamp,
        expires_at=stamp + 600,
        language=variant.language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(variant.reference_solution.encode()),
        test_digest=hashed(canonical(tests)),
        pack_digest="sha256:" + digest,
        mode="submit",
        limits=profile.limits,
        compile_config=COMMANDS[variant.language],
    )
    job = JobEnvelope(
        manifest=manifest,
        signature=sign(manifest.model_dump(), secret),
        source=variant.reference_solution,
        tests=tests,
    )
    result = execute(job, backend, secret, stamp)["result"]
    if result["operational_status"] != "healthy" or not all(
        x["status"] == "passed" for x in result["cases"]
    ):
        raise AssertionError(
            f"{exercise.id}/{variant.language}: "
            + result["reason_code"] + " "
            + str([(x["index"], x["status"]) for x in result["cases"] if x["status"] != "passed"])
        )
    return {
        "exercise": exercise.id,
        "language": variant.language,
        "passed_cases": len(result["cases"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise", default="")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--backend", choices=["local_process", "demo_docker"], default="local_process")
    args = parser.parse_args()
    environment = (dict((line.split("=",1)[0], json.loads(line.split("=",1)[1])) for line in (ROOT / ".env.local").read_text().splitlines()) if args.backend == "local_process" else json.loads((ROOT / ".cache/demo-environment.json").read_text()))
    profiles = [
        RuntimeProfile.model_validate(x)
        for x in json.loads(environment["SOCRAT_EXECUTION_PROFILES"])
    ]
    pack = build_pack({x.language: x.image for x in profiles})
    backend = (LocalProcessBackend if args.backend == "local_process" else DemoDockerBackend)(profiles, environment="development", demo_mode=True)
    backend.preflight()
    results, failures = [], []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [
            pool.submit(
                verify,
                exercise,
                variant,
                next(p for p in profiles if p.language == variant.language),
                backend,
                pack.digest(),
            )
            for exercise in pack.exercises
            if exercise.modality == "code" and (not args.exercise or args.exercise in exercise.id)
            for variant in exercise.variants
        ]
        if not jobs:
            raise ValueError("No reference variants selected")
        for future in as_completed(jobs):
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append(str(exc))
                print(str(exc), flush=True)
            if (len(results) + len(failures)) % 5 == 0:
                print(
                    f"Verified {len(results)}/{len(jobs)} variants; failures: {len(failures)}",
                    flush=True,
                )
    report = {
        "backend": args.backend,
        "filter": args.exercise,
        "pack_digest": pack.digest(),
        "variants": len(jobs),
        "passed": results,
        "failures": failures,
        "seconds": round(time.monotonic() - started, 2),
    }
    (ROOT / (".cache/demo-reference-" + args.backend + ("-filtered" if args.exercise else "") + ".json")).write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "passed"}))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
