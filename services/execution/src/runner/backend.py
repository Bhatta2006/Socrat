"""Backend seam; signed jobs and result acceptance stay in the existing worker."""

from typing import Protocol

from socrat.execution.protocol import CaseResult, JobEnvelope


class ExecutionBackend(Protocol):
    def preflight(self) -> None: ...
    def execute(self, job: JobEnvelope) -> list[CaseResult]: ...


def make_backend(settings):
    from socrat.execution.protocol import RuntimeProfile

    profiles = [RuntimeProfile.model_validate(x) for x in settings.execution_profiles]
    if settings.execution_backend == "local_process":
        from runner.local_backend import LocalProcessBackend

        return LocalProcessBackend(
            profiles, environment=settings.environment, demo_mode=settings.demo_mode
        )
    if settings.execution_backend == "demo_docker":
        from runner.demo_backend import DemoDockerBackend

        return DemoDockerBackend(
            profiles, environment=settings.environment, demo_mode=settings.demo_mode
        )
    import os

    from runner.docker_backend import DockerBackend

    return DockerBackend(profiles, os.environ["SOCRAT_EXECUTION_COSIGN_PUBLIC_KEY"])
