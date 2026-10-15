from datetime import date
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FoundrySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOCRAT_FOUNDRY_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    enabled: bool = False
    kill_switch: bool = False
    live_enabled: bool = False
    bot_info_url: str = Field(default="", max_length=2048)
    bot_contact: str = Field(default="", max_length=160)
    request_timeout_seconds: float = Field(default=20, ge=1, le=30, allow_inf_nan=False)
    snapshot_directory: str = ".cache/foundry-snapshots"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    github_token: SecretStr = SecretStr("")
    github_token_file: str = ""
    pipeline_version: str = Field(default="foundry-m2", min_length=1, max_length=64)
    max_docs_per_job: int = Field(default=60, ge=1, le=10000)
    max_tokens_per_job: int = Field(default=2_500_000, ge=1, le=100_000_000)
    max_wall_seconds: int = Field(default=5400, ge=1, le=86400)
    max_jobs_per_day: int = Field(default=20, ge=1, le=10000)
    max_tokens_per_day: int = Field(default=50_000_000, ge=1, le=1_000_000_000)
    lease_seconds: int = Field(default=60, ge=1, le=3600)
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_seconds: int = Field(default=5, ge=1, le=300)
    poll_seconds: float = Field(default=2, ge=0.1, le=60, allow_inf_nan=False)
    min_delay_ms: int = Field(default=2000, ge=2000, le=60000)
    max_concurrency_per_domain: int = Field(default=2, ge=1, le=2)
    max_depth: int = Field(default=2, ge=0, le=2)
    max_bytes: int = Field(default=10_000_000, ge=1, le=10_000_000)
    max_redirects: int = Field(default=5, ge=0, le=5)
    robots_cache_seconds: int = Field(default=86400, ge=1, le=86400)
    github_min_stars: int = Field(default=300, ge=0)
    github_pushed_after: date = date(2025, 1, 1)
    discovery_licenses: list[str] = Field(
        default_factory=lambda: ["mit", "apache-2.0", "bsd-3-clause", "cc-by-4.0", "cc0-1.0"]
    )
    allowed_domain_types: tuple[Literal["code", "math"], ...] = Field(
        default=("code", "math"), min_length=1
    )
    language: Literal["en"] = "en"
    tier: Literal["explorer"] = "explorer"
    min_concept_resource_coverage: float = Field(default=0.8, ge=0.8, le=1, allow_inf_nan=False)
    min_link_health: float = Field(default=0.95, ge=0.95, le=1, allow_inf_nan=False)

    @property
    def user_agent(self) -> str:
        return f"SocratBot/1.0 (+{self.bot_info_url}; {self.bot_contact})"

    @model_validator(mode="after")
    def acquisition_settings(self):
        from urllib.parse import urlsplit

        from socrat.config import _secret_from_file

        self.github_token = _secret_from_file(
            "foundry_github_token", self.github_token, self.github_token_file
        )
        if len(self.user_agent) > 512 or any(c in self.user_agent for c in "\r\n"):
            raise ValueError("Bot identity must fit a safe User-Agent header")
        if self.live_enabled:
            info = urlsplit(self.bot_info_url)
            if (
                not self.enabled
                or info.scheme != "https"
                or not info.hostname
                or info.username
                or info.password
                or not self.bot_contact
                or any(c in self.user_agent for c in "\r\n")
            ):
                raise ValueError(
                    "Live acquisition requires enabled Foundry and a real bot URL/contact"
                )
        if self.s3_endpoint_url and urlsplit(self.s3_endpoint_url).scheme != "https":
            raise ValueError("Snapshot object storage requires HTTPS")
        return self
