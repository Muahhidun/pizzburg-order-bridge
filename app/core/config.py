from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BRIDGE_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PizzBurg Order Bridge"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://bridge:bridge@localhost:5432/pizzburg_bridge"
    auto_create_schema: bool = False

    oauth_client_id: str = "local-yandex-client"
    oauth_client_secret: SecretStr = SecretStr("change-me-local-client-secret")
    jwt_secret: SecretStr = SecretStr("change-me-local-jwt-signing-secret-at-least-32-chars")
    token_ttl_seconds: int = 900
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "pizzburg-order-bridge"
    jwt_issuer: str = "pizzburg-order-bridge"

    @model_validator(mode="after")
    def reject_placeholder_production_secrets(self) -> "Settings":
        if self.environment != "production":
            return self

        placeholders = {
            "change-me-local-client-secret",
            "change-me-local-jwt-signing-secret-at-least-32-chars",
        }
        secrets = {
            self.oauth_client_secret.get_secret_value(),
            self.jwt_secret.get_secret_value(),
        }
        if placeholders & secrets:
            raise ValueError("Production requires non-placeholder OAuth and JWT secrets")
        if not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Production requires PostgreSQL with the asyncpg driver")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
