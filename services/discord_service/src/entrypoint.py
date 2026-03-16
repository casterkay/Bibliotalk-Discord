from __future__ import annotations

import logging

from .config import load_runtime_config, resolve_discord_token
from .runtime import build_live_discord_runtime, configure_logging


async def run_discord_bot(
    *,
    db_path: str | None = None,
    log_level: str | None = None,
    discord_command_guild_id: str | None = None,
) -> int:
    config = load_runtime_config(
        db_path=db_path,
        log_level=log_level,
        discord_command_guild_id=discord_command_guild_id,
    )
    logger = configure_logging(level=config.log_level)
    token = resolve_discord_token()
    if not token:
        logger.error("discord runtime missing token expected_env=DISCORD_TOKEN")
        return 1

    runtime = await build_live_discord_runtime(config, logger_=logger)
    logger.info(
        "starting discord runtime db_path=%s command_guild_id=%s",
        config.db_path,
        config.discord_command_guild_id,
    )
    await runtime.client.start(token)
    return 0


def get_logger() -> logging.Logger:
    return logging.getLogger("discord_service")
