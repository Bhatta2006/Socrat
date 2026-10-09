"""Development-only Docker Desktop sandbox. Never selected by production defaults."""

import json
import subprocess
import time
from typing import Literal, cast

from runner.docker_backend import SandboxUnavailable, capture, container_args
from socrat.execution.protocol import CaseResult, JobEnvelope, RuntimeProfile, same_output


def demo_container_args(job: JobEnvelope, name: str) -> list[str]:
    args = container_args(job, name)
    args.remove("--runtime=runsc")
    # Locally built runtimes have immutable image IDs, but no registry RepoDigest.
    args[args.index(job.manifest.image)] = job.manifest.image.split("@", 1)[1]
    return args


class DemoDockerBackend:
    def __init__(self, profiles: list[RuntimeProfile], *, environment: str, demo_mode: bool):
        if environment not in {"development", "test"} or not demo_mode:
            raise ValueError("Demo Docker requires explicit development/test demo mode")
        self.profiles = {x.image: x for x in profiles}

    def command(self, args: list[str]):
        return subprocess.run(args, capture_output=True, timeout=30, check=True)

    def preflight(self):
        try:
            info = json.loads(self.command(["docker", "info", "--format", "{{json .}}"]).stdout)
            if info.get("OSType") != "linux" or not all(
                info.get(x) for x in ("MemoryLimit", "PidsLimit", "CpuCfsQuota")
            ):
                raise SandboxUnavailable("Linux Docker resource controllers required")
            for image in self.profiles:
                immutable = image.split("@", 1)[1]
                actual = self.command(
                    ["docker", "image", "inspect", "--format", "{{.Id}}", immutable]
                )
                if actual.stdout.decode().strip() != immutable:
                    raise SandboxUnavailable("Demo image identity mismatch")
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
            raise SandboxUnavailable("demo_docker_unavailable") from exc

    def execute(self, job: JobEnvelope) -> list[CaseResult]:
        profile = self.profiles.get(job.manifest.image)
        if (
            profile is None
            or profile.limits != job.manifest.limits
            or profile.language != job.manifest.language
        ):
            raise SandboxUnavailable("Unapproved execution profile")
        results = []
        for index, test in enumerate(job.tests):
            name = f"socrat-demo-{job.manifest.job_id}-{index}"
            try:
                self.command(demo_container_args(job, name))
                started = time.monotonic()

                def abort(container=name):
                    self.command(["docker", "kill", container])

                code, stdout, stderr, timed_out, flooded = capture(
                    ["docker", "start", "--attach", "--interactive", name],
                    json.dumps({"source": job.source, "stdin": test.input}).encode(),
                    profile.limits.compile_seconds + profile.limits.wall_seconds,
                    profile.limits.output_bytes,
                    abort,
                    lambda: False,
                )
                state = json.loads(
                    self.command(["docker", "inspect", "--format", "{{json .State}}", name]).stdout
                )
                if state.get("Status") != "exited" or state.get("Error"):
                    raise SandboxUnavailable("sandbox_start_or_control_failure")
                status = (
                    "memory_limit"
                    if state.get("OOMKilled")
                    else "output_limit"
                    if flooded
                    else "timeout"
                    if timed_out or code in {124, 137, 152}
                    else "compile_error"
                    if code == 65
                    else "runtime_error"
                    if code != 0
                    else "executed"
                    if test.expected is None
                    else "passed"
                    if same_output(stdout.decode(errors="replace"), test.expected)
                    else "wrong_answer"
                )
                public = test.visibility == "public"
                results.append(
                    CaseResult(
                        index=index,
                        status=cast(
                            Literal[
                                "passed",
                                "wrong_answer",
                                "executed",
                                "compile_error",
                                "runtime_error",
                                "timeout",
                                "memory_limit",
                                "output_limit",
                            ],
                            status,
                        ),
                        wall_ms=min(60000, int((time.monotonic() - started) * 1000)),
                        stdout=stdout.decode(errors="replace")[:16000] if public else "",
                        stderr=stderr.decode(errors="replace")[:16000] if public else "",
                    )
                )
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                raise SandboxUnavailable("demo_worker_failure") from exc
            finally:
                try:
                    self.command(["docker", "rm", "--force", name])
                except (OSError, subprocess.SubprocessError) as exc:
                    raise SandboxUnavailable("sandbox_cleanup_failed") from exc
        return results
