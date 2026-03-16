from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bt_common.config import load_repo_dotenv
from bt_common.evidence_store.engine import default_database_path, resolve_database_path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_repo_dotenv()


class DiscordSettings(BaseSettings):
    bibliotalk_db_path: str | None = Field(
        default=None, validation_alias="BIBLIOTALK_DB_PATH"
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    discord_token: str | None = Field(default=None, validation_alias="DISCORD_TOKEN")
    discord_command_guild_id: str | None = Field(
        default=None, validation_alias="DISCORD_COMMAND_GUILD_ID"
    )

    model_config = SettingsConfigDict(extra="ignore")


@dataclass(frozen=True, slots=True)
class DiscordRuntimeConfig:
    db_path: Path
    log_level: str
    discord_command_guild_id: str | None = None


def load_runtime_config(
    *,
    db_path: str | None = None,
    log_level: str | None = None,
    discord_command_guild_id: str | None = None,
) -> DiscordRuntimeConfig:
    settings = DiscordSettings()
    return DiscordRuntimeConfig(
        db_path=resolve_database_path(
            db_path or settings.bibliotalk_db_path or default_database_path()
        ),
        log_level=(log_level or settings.log_level).upper(),
        discord_command_guild_id=(
            discord_command_guild_id or settings.discord_command_guild_id or ""
        ).strip()
        or None,
    )


def resolve_discord_token() -> str | None:
    settings = DiscordSettings()
    return (settings.discord_token or "").strip() or None
