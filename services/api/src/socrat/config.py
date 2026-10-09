from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_SESSION_SECRET = "local-development-only-change-before-deploy"
LOCAL_DATABASE_URL = "sqlite:///socrat.local.db"


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
    environment: Literal["development", "test", "staging", "production"] = "development"
    public_origin: str = "http://localhost:3000"
    session_secret: SecretStr = SecretStr(LOCAL_SESSION_SECRET)
    session_secret_file: str = ""
    session_ttl_seconds: int = 30 * 86400
    dev_login_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_client_secret_file: str = ""
    metrics_token: SecretStr = SecretStr("")
    metrics_token_file: str = ""

    # Code judge. "local_process" is an insecure native runner for development only;
    # deployed environments use gVisor workers with attested images.
    execution_backend: Literal["gvisor_docker", "local_process", "demo_docker"] = "gvisor_docker"
    execution_signing_secret: SecretStr = SecretStr("")
    execution_worker_secret: SecretStr = SecretStr("")
    execution_signing_secret_file: str = ""
    execution_worker_secret_file: str = ""
    execution_profiles: list[dict] = Field(default_factory=list, max_length=3)
    execution_daily_quota: int = Field(default=400, ge=1, le=5000)
    execution_queue_limit: int = Field(default=3, ge=1, le=20)

    # Socrat assistant. Keys may also come from ANTHROPIC_API_KEY / OPENAI_API_KEY,
    # which the official SDKs resolve themselves when these are empty.
    ai_provider: Literal["anthropic", "openai", "offline"] = "offline"
    ai_model: str = "claude-opus-5"
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    ai_server_fallbacks: bool = True
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    openai_base_url: str = ""
    ai_timeout_seconds: float = Field(default=45, ge=5, le=120)
    ai_daily_messages: int = Field(default=150, ge=1, le=5000)
    ai_reply_tokens: int = Field(default=1500, ge=200, le=8000)

    # Local demo conveniences (seeded sample learners). Rejected outside development/test.
    demo_mode: bool = False

    @property
    def secure(self) -> bool:
        return self.environment in {"staging", "production"}

    @property
    def execution_enabled(self) -> bool:
        return bool(self.execution_profiles)

    @model_validator(mode="after")
    def enforce_boundaries(self):
        if self.demo_mode and self.environment not in {"development", "test"}:
            raise ValueError("Demo mode is only accepted in development/test")
        if self.execution_backend in {"local_process", "demo_docker"} and self.secure:
            raise ValueError("The insecure local runner is only allowed in development/test")
        for name in ("execution_signing_secret", "execution_worker_secret"):
            setattr(
                self,
                name,
                _secret_from_file(name, getattr(self, name), getattr(self, f"{name}_file")),
            )
        if self.execution_profiles:
            if (
                len(self.execution_signing_secret.get_secret_value()) < 48
                or len(self.execution_worker_secret.get_secret_value()) < 48
                or self.execution_signing_secret == self.execution_worker_secret
            ):
                raise ValueError("Execution requires distinct strong signing and worker secrets")
            from socrat.execution.protocol import RuntimeProfile

            profiles = [RuntimeProfile.model_validate(x) for x in self.execution_profiles]
            if len({x.language for x in profiles}) != len(profiles) or len(
                {x.id for x in profiles}
            ) != len(profiles):
                raise ValueError("Execution requires unique runtime profiles")
        self.session_secret = _secret_from_file(
            "session_secret", self.session_secret, self.session_secret_file, LOCAL_SESSION_SECRET
        )
        self.oidc_client_secret = _secret_from_file(
            "oidc_client_secret", self.oidc_client_secret, self.oidc_client_secret_file
        )
        self.metrics_token = _secret_from_file(
            "metrics_token", self.metrics_token, self.metrics_token_file
        )
        if self.ai_provider == "openai" and not self.openai_model:
            raise ValueError("The OpenAI provider requires SOCRAT_OPENAI_MODEL")
        if self.ai_provider == "anthropic" and not self.ai_model.startswith("claude-"):
            raise ValueError("The Anthropic provider requires a Claude model id")

        origin = urlparse(self.public_origin)
        if origin.scheme not in {"http", "https"} or not origin.netloc or origin.path:
            raise ValueError("public_origin must be an origin without a trailing slash")
        if not 300 <= self.session_ttl_seconds <= 90 * 86400:
            raise ValueError("Session lifetime must be between 5 minutes and 90 days")
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
