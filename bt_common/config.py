"""Shared application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings used by all service modules."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    GOOGLE_API_KEY: str | None = None
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    EMOS_BASE_URL: str
    EMOS_API_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    MATRIX_HOMESERVER_URL: str
    MATRIX_AS_TOKEN: str
    MATRIX_HS_TOKEN: str
    LOG_LEVEL: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


class EMOSFallbackSettings(BaseSettings):
    """Optional EMOS values loaded from .env for local/dev fallback."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    EMOS_BASE_URL: str | None = None
    EMOS_API_KEY: str | None = None


@lru_cache(maxsize=1)
def get_emos_fallback_settings() -> EMOSFallbackSettings:
    return EMOSFallbackSettings()
