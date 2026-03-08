from __future__ import annotations

import argparse
import asyncio
import uuid

from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import DiscordMap, Figure, Subscription
from sqlalchemy import select


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a figure and Discord mapping for local quickstart"
    )
    parser.add_argument("--figure", dest="figure_slug", required=True)
    parser.add_argument("--display-name", dest="display_name")
    parser.add_argument("--persona-summary", dest="persona_summary")
    parser.add_argument("--subscription-url", dest="subscription_url", required=True)
    parser.add_argument(
        "--subscription-type", dest="subscription_type", default="channel"
    )
    parser.add_argument("--guild-id", dest="guild_id", required=True)
    parser.add_argument("--channel-id", dest="channel_id", required=True)
    parser.add_argument(
        "--poll-interval-minutes", dest="poll_interval_minutes", type=int, default=60
    )
    parser.add_argument("--db", dest="db_path")
    return parser


def _display_name_for_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-"))


async def seed_figure(
    *,
    db_path: str | None,
    figure_slug: str,
    display_name: str | None,
    persona_summary: str | None,
    subscription_url: str,
    subscription_type: str,
    guild_id: str,
    channel_id: str,
    poll_interval_minutes: int,
) -> None:
    await init_database(db_path)
    session_factory = get_session_factory(db_path)

    async with session_factory() as session:
        figure = (
            (
                await session.execute(
                    select(Figure).where(Figure.emos_user_id == figure_slug)
                )
            )
            .scalars()
            .first()
        )
        if figure is None:
            figure = Figure(
                figure_id=uuid.uuid4(),
                display_name=display_name or _display_name_for_slug(figure_slug),
                emos_user_id=figure_slug,
                persona_summary=persona_summary,
                status="active",
            )
            session.add(figure)
            await session.flush()
        else:
            if display_name:
                figure.display_name = display_name
            if persona_summary:
                figure.persona_summary = persona_summary
            figure.status = "active"

        subscription = (
            (
                await session.execute(
                    select(Subscription).where(
                        Subscription.figure_id == figure.figure_id,
                        Subscription.platform == "youtube",
                        Subscription.subscription_url == subscription_url,
                    )
                )
            )
            .scalars()
            .first()
        )
        if subscription is None:
            subscription = Subscription(
                figure_id=figure.figure_id,
                platform="youtube",
                subscription_type=subscription_type,
                subscription_url=subscription_url,
                poll_interval_minutes=max(1, poll_interval_minutes),
                is_active=True,
            )
            session.add(subscription)
        else:
            subscription.subscription_type = subscription_type
            subscription.poll_interval_minutes = max(1, poll_interval_minutes)
            subscription.is_active = True

        discord_map = await session.get(DiscordMap, figure.figure_id)
        if discord_map is None:
            session.add(
                DiscordMap(
                    figure_id=figure.figure_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                )
            )
        else:
            discord_map.guild_id = guild_id
            discord_map.channel_id = channel_id

        await session.commit()


def main() -> int:
    args = build_parser().parse_args()
    asyncio.run(
        seed_figure(
            db_path=args.db_path,
            figure_slug=args.figure_slug,
            display_name=args.display_name,
            persona_summary=args.persona_summary,
            subscription_url=args.subscription_url,
            subscription_type=args.subscription_type,
            guild_id=args.guild_id,
            channel_id=args.channel_id,
            poll_interval_minutes=args.poll_interval_minutes,
        )
    )
    print(
        f"Seeded figure '{args.figure_slug}' with subscription '{args.subscription_url}' and Discord channel '{args.channel_id}'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
