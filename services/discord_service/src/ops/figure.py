from __future__ import annotations

import uuid

from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import DiscordMap, Figure, Subscription
from sqlalchemy import select


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
