from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_SESSION_SECRET = "local-development-only-change-before-deploy"
LOCAL_DATABASE_URL = "sqlite:///socrat.local.db"


class ContentAdminIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issuer: str = Field(min_length=1, max_length=512)
    subject: str = Field(min_length=1, max_length=255)


def _read_secret_file(name: str, file_name: str) -> str:
    path = Path(file_name)
    try:
        if not path.is_file() or path.stat().st_size > 16_384:
            raise ValueError(f"{name}_file must reference a small regular file")
        value = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{name}_file could not be read") from exc

    if value.endswith("\n"):
        value = value[:-1]
        if value.endswith("\r"):
            value = value[:-1]
    if not value or "\n" in value or "\r" in value:
        raise ValueError(f"{name}_file must contain one non-empty single line")
    return value


def _secret_from_file(name: str, direct: SecretStr, file_name: str, default: str = ""):
    direct_value = direct.get_secret_value()
    if not file_name:
        return direct
    if direct_value not in {"", default}:
        raise ValueError(f"{name} cannot be provided both directly and by file")
    value = _read_secret_file(name, file_name)
    return SecretStr(value)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOCRAT_", env_file=".env", extra="ignore")
    database_url: SecretStr = SecretStr(LOCAL_DATABASE_URL)
    database_host: str = ""
    database_port: int = 5432
    database_name: str = ""
    database_user: str = ""
    database_password_file: str = ""

    @model_validator(mode="after")
    def load_database_password(self):
        if not self.database_password_file:
            return self
        if self.database_url.get_secret_value() != LOCAL_DATABASE_URL:
            raise ValueError("database_url and database_password_file cannot both be provided")
        if not self.database_host or not self.database_name or not self.database_user:
            raise ValueError(
                "database_host, database_name and database_user are required with a password file"
            )
        if not 1 <= self.database_port <= 65535:
            raise ValueError("database_port must be between 1 and 65535")
        password = _read_secret_file("database_password", self.database_password_file)
        user = quote(self.database_user, safe="")
        encoded_password = quote(password, safe="")
        database = quote(self.database_name, safe="")
        self.database_url = SecretStr(
            f"postgresql+psycopg://{user}:{encoded_password}"
            f"@{self.database_host}:{self.database_port}/{database}"
        )
        return self

    @property
    def database_url_value(self) -> str:
        return self.database_url.get_secret_value()


class Settings(DatabaseSettings):
    tutor_enabled: bool = False
    tutor_model_enabled: bool = False
    tutor_model_rollout_percent: int = Field(default=100, ge=0, le=100)
    tutor_advisor_shadow_enabled: bool = False
    tutor_prompt_version: Literal["tutor_1.0.0", "tutor_1.0.1", "tutor_1.0.2"] = "tutor_1.0.1"
    tutor_model: str = ""
    tutor_provider: Literal["structured_gateway", "openai_responses", "openai_chat"] = (
        "structured_gateway"
    )
    tutor_model_allowlist: list[str] = Field(default_factory=list, max_length=10)
    tutor_gateway_url: str = ""
    tutor_reasoning_effort: Literal["", "none", "low", "medium", "high"] = ""
    tutor_temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    tutor_top_p: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    tutor_gateway_secret: SecretStr = SecretStr("")
    tutor_gateway_secret_file: str = ""
    tutor_timeout_seconds: float = Field(default=4, ge=0.1, le=4)
    tutor_output_tokens: int = Field(default=600, ge=100, le=2000)
    tutor_session_calls: int = Field(default=12, ge=1, le=50)
    tutor_daily_calls: int = Field(default=40, ge=1, le=200)
    tutor_call_reserve_microusd: int = Field(default=10000, ge=1, le=1000000)
    tutor_daily_budget_microusd: int = Field(default=400000, ge=1, le=10000000)
    learning_sessions_enabled: bool = False
    execution_enabled: bool = False
    execution_signing_secret: SecretStr = SecretStr("")
    execution_worker_secret: SecretStr = SecretStr("")
    execution_signing_secret_file: str = ""
    execution_worker_secret_file: str = ""
    execution_profiles: list[dict] = Field(default_factory=list, max_length=3)
    execution_daily_quota: int = Field(default=100, ge=1, le=1000)
    execution_queue_limit: int = Field(default=4, ge=1, le=20)
    execution_ip_daily_quota: int = Field(default=500, ge=1, le=10000)
    execution_global_queue_limit: int = Field(default=100, ge=1, le=1000)
    planning_enabled: bool = False
    diagnostics_enabled: bool = False
    onboarding_enabled: bool = False
    content_admin_identities: list[ContentAdminIdentity] = Field(
        default_factory=list, max_length=100
    )
    environment: Literal["development", "test", "staging", "production"] = "development"
    public_origin: str = "http://localhost:3000"
    session_secret: SecretStr = SecretStr(LOCAL_SESSION_SECRET)
    session_secret_file: str = ""
    session_ttl_seconds: int = 28800
    dev_login_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_client_secret_file: str = ""
    metrics_token: SecretStr = SecretStr("")
    metrics_token_file: str = ""

    @property
    def secure(self) -> bool:
        return self.environment in {"staging", "production"}

    @model_validator(mode="after")
    def enforce_boundaries(self):
        self.tutor_gateway_secret = _secret_from_file(
            "tutor_gateway_secret", self.tutor_gateway_secret, self.tutor_gateway_secret_file
        )
        if self.tutor_model_enabled:
            gateway = urlparse(self.tutor_gateway_url)
            if (
                gateway.scheme != "https"
                or not gateway.hostname
                or gateway.username
                or gateway.password
                or gateway.query
                or gateway.fragment
                or self.tutor_model not in self.tutor_model_allowlist
                or not self.tutor_gateway_secret.get_secret_value()
            ):
                raise ValueError(
                    "Tutor models require an HTTPS adapter, secret and allow-listed model"
                )
        self.execution_signing_secret = _secret_from_file(
            "execution_signing_secret",
            self.execution_signing_secret,
            self.execution_signing_secret_file,
            "",
        )
        self.execution_worker_secret = _secret_from_file(
            "execution_worker_secret",
            self.execution_worker_secret,
            self.execution_worker_secret_file,
            "",
        )
        if self.execution_enabled:
            if (
                len(self.execution_signing_secret.get_secret_value()) < 48
                or len(self.execution_worker_secret.get_secret_value()) < 48
                or self.execution_signing_secret == self.execution_worker_secret
            ):
                raise ValueError("Execution requires distinct strong signing and worker secrets")
            from socrat.execution.protocol import RuntimeProfile

            profiles = [RuntimeProfile.model_validate(x) for x in self.execution_profiles]
            if (
                not profiles
                or len({x.language for x in profiles}) != len(profiles)
                or len({x.id for x in profiles}) != len(profiles)
            ):
                raise ValueError("Execution requires unique immutable runtime profiles")
        self.session_secret = _secret_from_file(
            "session_secret",
            self.session_secret,
            self.session_secret_file,
            LOCAL_SESSION_SECRET,
        )
        self.oidc_client_secret = _secret_from_file(
            "oidc_client_secret", self.oidc_client_secret, self.oidc_client_secret_file
        )
        self.metrics_token = _secret_from_file(
            "metrics_token", self.metrics_token, self.metrics_token_file
        )

        origin = urlparse(self.public_origin)
        if origin.scheme not in {"http", "https"} or not origin.netloc or origin.path:
            raise ValueError("public_origin must be an origin without a trailing slash")
        if not 300 <= self.session_ttl_seconds <= 86400:
            raise ValueError("Session lifetime must be between 5 minutes and 24 hours")
        if self.dev_login_enabled and (
            self.secure or origin.hostname not in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("Developer login is only allowed on local development/test origins")
        if self.secure:
            if not self.database_url_value.startswith("postgresql+psycopg://"):
                raise ValueError("Deployed environments require PostgreSQL")
            if (
                origin.scheme != "https"
                or len(self.session_secret.get_secret_value()) < 48
                or "local-development" in self.session_secret.get_secret_value()
            ):
                raise ValueError("Deployed environments require HTTPS and a unique session secret")
            if not (
                self.oidc_issuer.startswith("https://")
                and self.oidc_client_id
                and self.oidc_client_secret.get_secret_value()
            ):
                raise ValueError("Deployed environments require an OIDC provider")
            if len(self.metrics_token.get_secret_value()) < 32:
                raise ValueError("Deployed metrics require a private bearer token")
        return self
