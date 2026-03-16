from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

import discord
from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import (
    DiscordMap,
    DiscordPost,
    Figure,
    Source,
    TranscriptBatch,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..config import DiscordRuntimeConfig
from ..config import resolve_discord_token
from ..feed.discord_transport import DiscordPyFeedTransport
from ..feed.publisher import FeedPublisher, PublishResult
from ..runtime import FeedPublicationSummary, publish_pending_feeds

logger = logging.getLogger("discord_service.ops.feed")


@dataclass(frozen=True, slots=True)
class SourceFeedStatus:
    source_id: str
    parent_posted: bool
    batches_total: int
    batches_posted: int
    failed_posts: int


async def _with_discord_client(
    token: str,
    *,
    logger_: logging.Logger,
    fn,
):
    intents = discord.Intents.none()
    client = discord.Client(intents=intents)
    done = asyncio.Event()
    result_holder: dict[str, object] = {}
    exc_holder: dict[str, BaseException] = {}

    async def _run() -> None:
        try:
            result_holder["value"] = await fn(client)
        except BaseException as exc:  # noqa: BLE001
            exc_holder["exc"] = exc
        finally:
            done.set()
            try:
                await client.close()
            except Exception:
                pass

    @client.event
    async def on_ready() -> None:  # type: ignore[override]
        logger_.info("discord ops client ready user=%s", client.user)
        asyncio.create_task(_run())

    await client.start(token)
    await done.wait()
    if "exc" in exc_holder:
        raise exc_holder["exc"]
    return result_holder.get("value")


async def publish_pending_feeds_once(
    config: DiscordRuntimeConfig,
    *,
    figure_slug: str | None = None,
    logger_: logging.Logger | None = None,
) -> FeedPublicationSummary:
    logger_ = logger_ or logging.getLogger("discord_service")
    token = resolve_discord_token()
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN")

    async def _publish(client: discord.Client) -> FeedPublicationSummary:
        transport = DiscordPyFeedTransport(client)
        return await publish_pending_feeds(
            config,
            transport=transport,
            session_factory=get_session_factory(config.db_path),
            logger_=logger_,
            figure_slug=figure_slug,
        )

    value = await _with_discord_client(token, logger_=logger_, fn=_publish)
    assert isinstance(value, FeedPublicationSummary)
    return value


async def _lookup_source_by_video(
    session: AsyncSession,
    *,
    figure_slug: str,
    video_id: str,
) -> tuple[Figure, Source]:
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
        raise LookupError(f"Unknown figure: {figure_slug}")
    source = (
        (
            await session.execute(
                select(Source).where(
                    Source.figure_id == figure.figure_id,
                    Source.platform == "youtube",
                    Source.external_id == video_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if source is None:
        raise LookupError(f"Unknown video_id for {figure_slug}: {video_id}")
    return figure, source


async def source_feed_status_by_video(
    *,
    db_path: str | None,
    figure_slug: str,
    video_id: str,
) -> SourceFeedStatus:
    await init_database(db_path)
    session_factory = get_session_factory(db_path)
    async with session_factory() as session:
        _figure, source = await _lookup_source_by_video(
            session, figure_slug=figure_slug, video_id=video_id
        )

        parent_posted = (
            await session.execute(
                select(DiscordPost.parent_message_id, DiscordPost.thread_id).where(
                    DiscordPost.source_id == source.source_id,
                    DiscordPost.batch_id.is_(None),
                    DiscordPost.post_status == "posted",
                )
            )
        ).first() is not None
        batches_total = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(TranscriptBatch)
                    .where(TranscriptBatch.source_id == source.source_id)
                )
            ).scalar_one()
            or 0
        )
        batches_posted = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(TranscriptBatch)
                    .where(
                        TranscriptBatch.source_id == source.source_id,
                        TranscriptBatch.posted_to_discord.is_(True),
                    )
                )
            ).scalar_one()
            or 0
        )
        failed_posts = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(DiscordPost)
                    .where(
                        DiscordPost.source_id == source.source_id,
                        DiscordPost.post_status == "failed",
                    )
                )
            ).scalar_one()
            or 0
        )
        return SourceFeedStatus(
            source_id=str(source.source_id),
            parent_posted=parent_posted,
            batches_total=batches_total,
            batches_posted=batches_posted,
            failed_posts=failed_posts,
        )


async def _reset_failed_posts_for_source(
    session: AsyncSession,
    *,
    source_id: uuid.UUID,
) -> int:
    failed = (
        (
            await session.execute(
                select(DiscordPost).where(
                    DiscordPost.source_id == source_id,
                    DiscordPost.post_status == "failed",
                )
            )
        )
        .scalars()
        .all()
    )
    if not failed:
        return 0
    await session.execute(
        update(DiscordPost)
        .where(DiscordPost.source_id == source_id, DiscordPost.post_status == "failed")
        .values(post_status="pending", posted_at=None)
    )
    # Conservative: also flip batch flags back to false so the publisher rechecks them.
    batch_ids = [row.batch_id for row in failed if row.batch_id is not None]
    if batch_ids:
        await session.execute(
            update(TranscriptBatch)
            .where(TranscriptBatch.batch_id.in_(batch_ids))
            .values(posted_to_discord=False)
        )
    await session.commit()
    return len(failed)


async def _publish_source_once(
    *,
    discord_config: DiscordRuntimeConfig,
    session_factory: async_sessionmaker[AsyncSession],
    source_id: uuid.UUID,
    channel_id: str,
    logger_: logging.Logger,
) -> PublishResult:
    token = resolve_discord_token()
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN")

    async def _publish(client: discord.Client) -> PublishResult:
        transport = DiscordPyFeedTransport(client)
        publisher = FeedPublisher(session_factory, transport=transport)
        return await publisher.publish_source(
            source_id=source_id, channel_id=channel_id
        )

    value = await _with_discord_client(token, logger_=logger_, fn=_publish)
    assert isinstance(value, PublishResult)
    return value


async def retry_failed_posts_by_video(
    *,
    db_path: str | None,
    figure_slug: str,
    video_id: str,
    discord_config: DiscordRuntimeConfig,
    logger_: logging.Logger | None = None,
) -> FeedPublicationSummary:
    logger_ = logger_ or logging.getLogger("discord_service")
    await init_database(db_path)
    session_factory = get_session_factory(db_path)

    source_id: uuid.UUID
    channel_id: str
    async with session_factory() as session:
        figure, source = await _lookup_source_by_video(
            session, figure_slug=figure_slug, video_id=video_id
        )
        discord_map = await session.get(DiscordMap, figure.figure_id)
        if discord_map is None:
            raise LookupError(f"Missing discord_map for figure: {figure_slug}")
        await _reset_failed_posts_for_source(session, source_id=source.source_id)
        source_id = source.source_id
        channel_id = str(discord_map.channel_id)

    result = await _publish_source_once(
        discord_config=discord_config,
        session_factory=session_factory,
        source_id=source_id,
        channel_id=channel_id,
        logger_=logger_,
    )

    # Report summary for just this source.
    return FeedPublicationSummary(
        attempted_figures=1,
        attempted_sources=1,
        published_sources=1 if result.status == "done" else 0,
        failed_sources=1 if result.status != "done" else 0,
    )


async def republish_source_by_video(
    *,
    db_path: str | None,
    figure_slug: str,
    video_id: str,
    discord_config: DiscordRuntimeConfig,
    logger_: logging.Logger | None = None,
) -> PublishResult:
    """Publish/resume feed posting for one video (idempotent; does not reset state)."""
    logger_ = logger_ or logging.getLogger("discord_service")
    await init_database(db_path)
    session_factory = get_session_factory(db_path)

    async with session_factory() as session:
        figure, source = await _lookup_source_by_video(
            session, figure_slug=figure_slug, video_id=video_id
        )
        discord_map = await session.get(DiscordMap, figure.figure_id)
        if discord_map is None:
            raise LookupError(f"Missing discord_map for figure: {figure_slug}")
        source_id = source.source_id
        channel_id = str(discord_map.channel_id)

    return await _publish_source_once(
        discord_config=discord_config,
        session_factory=session_factory,
        source_id=source_id,
        channel_id=channel_id,
        logger_=logger_,
    )
