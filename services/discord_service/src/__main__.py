from __future__ import annotations

import argparse
import asyncio

from .config import load_runtime_config
from .runtime import build_live_discord_runtime, configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bibliotalk Discord runtime")
    parser.add_argument("--db", dest="db_path")
    parser.add_argument("--log-level", dest="log_level")
    parser.add_argument("--discord-token", dest="discord_token")
    parser.add_argument("--command-guild-id", dest="discord_command_guild_id")
    return parser


async def _main_async() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(
        db_path=args.db_path,
        log_level=args.log_level,
        discord_token=args.discord_token,
        discord_command_guild_id=args.discord_command_guild_id,
    )
    logger = configure_logging(level=config.log_level)
    if not config.discord_token:
        logger.error(
            "discord runtime missing token expected_env=DISCORD_TOKEN",
        )
        return 1
    runtime = await build_live_discord_runtime(config, logger_=logger)
    logger.info(
        "starting discord runtime db_path=%s command_guild_id=%s",
        config.db_path,
        config.discord_command_guild_id,
    )
    await runtime.client.start(config.discord_token)
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
