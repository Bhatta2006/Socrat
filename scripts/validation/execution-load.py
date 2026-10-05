"""Dedicated-host service-time baseline; API queue/end-to-end soak remains a separate gate."""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src"),
               str(ROOT / "services/api/tests")]

from runner.corpus import source  # noqa: E402
from runner.docker_backend import DockerBackend  # noqa: E402
from socrat.execution.protocol import RuntimeProfile  # noqa: E402
from test_execution_sandbox import envelope  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--profiles", type=Path, required=True)
parser.add_argument("--cosign-key", required=True)
parser.add_argument("--beta-concurrency", type=int, required=True)
parser.add_argument("--jobs-per-language", type=int, default=100)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if not 1 <= args.beta_concurrency <= 32 or args.jobs_per_language < 100:
    parser.error("Declare beta concurrency 1..32 and at least 100 jobs per language")
profiles = [RuntimeProfile.model_validate(x) for x in json.loads(args.profiles.read_text())]
if {x.language for x in profiles} != {"python", "cpp", "java"}:
    parser.error("All three reviewed runtime profiles are required")
backend = DockerBackend(profiles, args.cosign_key)
backend.preflight()  # Mandatory runsc, cgroups, signatures, and immutable image checks.


def run(profile):
    started = time.monotonic()
    result = backend.execute(envelope(profile, source(profile.language, "semantic"), "3", "6"))
    return profile.language, time.monotonic() - started, result[0].status


jobs = [profile for _ in range(args.jobs_per_language) for profile in profiles]
with ThreadPoolExecutor(max_workers=2 * args.beta_concurrency) as pool:
    results = list(pool.map(run, jobs))
report = {"scope": "dedicated_host_service_time_excludes_api_queue", "concurrency": 2 * args.beta_concurrency,
          "images": [x.image for x in profiles], "languages": {}}
for profile in profiles:
    values = sorted(seconds for language, seconds, _ in results if language == profile.language)
    passed = sum(status == "passed" for language, _, status in results if language == profile.language)
    report["languages"][profile.language] = {"jobs": len(values), "p95_seconds": values[int(.95 * len(values)) - 1],
        "successful_jobs": passed, "passes": values[int(.95 * len(values)) - 1] < 4 and passed / len(values) >= .995}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
raise SystemExit(0 if all(x["passes"] for x in report["languages"].values()) else 1)
