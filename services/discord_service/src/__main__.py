from __future__ import annotations

import argparse
import asyncio

from .entrypoint import run_discord_bot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bibliotalk Discord runtime")
    parser.add_argument("--db", dest="db_path")
    parser.add_argument("--log-level", dest="log_level")
    parser.add_argument("--command-guild-id", dest="discord_command_guild_id")
    return parser


async def _main_async() -> int:
    args = build_parser().parse_args()
    return await run_discord_bot(
        db_path=args.db_path,
        log_level=args.log_level,
        discord_command_guild_id=args.discord_command_guild_id,
    )


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
