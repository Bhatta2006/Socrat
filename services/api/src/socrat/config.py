from typing import Literal
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOCRAT_", env_file=".env", extra="ignore")
    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///socrat.local.db"
    public_origin: str = "http://localhost:3000"
    session_secret: str = "local-development-only-change-before-deploy"
    session_ttl_seconds: int = 28800
    dev_login_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    metrics_token: str = ""

    @property
    def secure(self) -> bool:
        return self.environment in {"staging", "production"}

    @model_validator(mode="after")
    def enforce_boundaries(self):
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
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Deployed environments require PostgreSQL")
            if (
                origin.scheme != "https"
                or len(self.session_secret) < 48
                or "local-development" in self.session_secret
            ):
                raise ValueError("Deployed environments require HTTPS and a unique session secret")
            if not (
                self.oidc_issuer.startswith("https://")
                and self.oidc_client_id
                and self.oidc_client_secret
            ):
                raise ValueError("Deployed environments require an OIDC provider")
            if len(self.metrics_token) < 32:
                raise ValueError("Deployed metrics require a private bearer token")
        return self
