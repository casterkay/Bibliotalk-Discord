from __future__ import annotations

import argparse
import asyncio

from .entrypoint import run_discord_bot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bibliotalk Discord runtime")
    parser.add_argument("--db", dest="db_path")
    parser.add_argument("--log-level", dest="log_level")
    parser.add_argument("--command-guild-id", dest="discord_command_guild_id")
    parser.add_argument("--voip-service-url", dest="voip_service_url")
    parser.add_argument(
        "--voice-default-text-channel-id", dest="discord_voice_default_text_channel_id"
    )
    return parser


async def _main_async() -> int:
    args = build_parser().parse_args()
    return await run_discord_bot(
        db_path=args.db_path,
        log_level=args.log_level,
        discord_command_guild_id=args.discord_command_guild_id,
        voip_service_url=args.voip_service_url,
        discord_voice_default_text_channel_id=args.discord_voice_default_text_channel_id,
    )


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
