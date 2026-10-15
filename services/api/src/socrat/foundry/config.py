from datetime import date
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FoundrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOCRAT_FOUNDRY_", env_file=".env", extra="ignore")

    enabled: bool = False
    kill_switch: bool = False
    # M1 has no acquisition or model adapters; configuration cannot enable live work.
    live_enabled: Literal[False] = False
    pipeline_version: str = Field(default="foundry-m1", min_length=1, max_length=64)
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
