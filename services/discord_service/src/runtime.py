from __future__ import annotations

import logging
from dataclasses import dataclass

import discord
from agents_service.agent.agent_factory import create_spirit_agent
from agents_service.agent.orchestrator import DMOrchestrator
from agents_service.store import SQLiteFigureStore
from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import DiscordMap, Figure
from bt_common.logging import JsonFormatter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .bot.client import BibliotalkDiscordClient
from .bot.concierge import DMConcierge
from .config import DiscordRuntimeConfig
from .feed.discord_transport import DiscordPyFeedTransport
from .feed.publisher import DiscordFeedTransport, FeedPublisher
from .talks.directory import FigureDirectory
from .talks.router import FacilitatorRouter
from .talks.service import TalkService
from .talks.transport import DiscordPyTalkTransport, TalkTransport


def configure_logging(*, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("discord_service")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level.upper())
    return logger


@dataclass(frozen=True, slots=True)
class LiveDiscordRuntime:
    client: BibliotalkDiscordClient


@dataclass(frozen=True, slots=True)
class FeedPublicationSummary:
    attempted_figures: int = 0
    attempted_sources: int = 0
    published_sources: int = 0
    failed_sources: int = 0


async def publish_pending_feeds(
    config: DiscordRuntimeConfig,
    *,
    transport: DiscordFeedTransport,
    figure_slug: str | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    logger_: logging.Logger | None = None,
) -> FeedPublicationSummary:
    logger_ = logger_ or logging.getLogger("discord_service")
    await init_database(config.db_path)
    session_factory = session_factory or get_session_factory(config.db_path)

    async with session_factory() as session:
        query = (
            select(Figure.figure_id, Figure.emos_user_id, DiscordMap.channel_id)
            .join(DiscordMap, DiscordMap.figure_id == Figure.figure_id)
            .where(Figure.status == "active")
        )
        if figure_slug:
            query = query.where(Figure.emos_user_id == figure_slug)
        rows = (await session.execute(query.order_by(Figure.emos_user_id))).all()

    publisher = FeedPublisher(session_factory, transport=transport)
    attempted_sources = 0
    published_sources = 0
    failed_sources = 0
    for figure_id, figure_slug, channel_id in rows:
        publication = await publisher.publish_pending_sources(
            figure_id=figure_id,
            channel_id=str(channel_id),
        )
        logger_.info(
            "feed publication complete figure_slug=%s attempted=%s published=%s failed=%s",
            figure_slug,
            publication.attempted_sources,
            publication.published_sources,
            publication.failed_sources,
        )
        attempted_sources += publication.attempted_sources
        published_sources += publication.published_sources
        failed_sources += publication.failed_sources

    return FeedPublicationSummary(
        attempted_figures=len(rows),
        attempted_sources=attempted_sources,
        published_sources=published_sources,
        failed_sources=failed_sources,
    )


async def build_live_discord_runtime(
    config: DiscordRuntimeConfig,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    logger_: logging.Logger | None = None,
) -> LiveDiscordRuntime:
    logger_ = logger_ or logging.getLogger("discord_service")
    await init_database(config.db_path)
    session_factory = session_factory or get_session_factory(config.db_path)

    store = SQLiteFigureStore(session_factory)
    orchestrator = DMOrchestrator(
        agent_factory=lambda figure_id: create_spirit_agent(figure_id, store=store)
    )

    directory = FigureDirectory(session_factory=session_factory)
    await directory.refresh()

    router = FacilitatorRouter()

    # Circular dependency: TalkService needs a transport backed by the live Discord client.
    # We construct the client first, then inject it into the transport instance.
    talk_transport: TalkTransport = DiscordPyTalkTransport(client=None)
    talk_service = TalkService(
        session_factory=session_factory,
        figure_directory=directory,
        router=router,
        orchestrator=orchestrator,
        transport=talk_transport,
        hub_channel_name="bibliotalk",
        logger_=logger_,
    )

    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True
    intents.guilds = True
    intents.messages = True

    client = BibliotalkDiscordClient(
        config=config,
        talk_service=talk_service,
        figure_directory=directory,
        dm_concierge=DMConcierge(figure_directory=directory, logger_=logger_),
        on_ready_callback=None,
        logger=logger_,
        intents=intents,
    )
    client.on_ready_callback = lambda: _on_ready(
        client=client,
        config=config,
        session_factory=session_factory,
        logger_=logger_,
    )

    # Inject live client into talk transport.
    assert isinstance(talk_transport, DiscordPyTalkTransport)
    talk_transport.client = client

    return LiveDiscordRuntime(client=client)


async def _on_ready(
    *,
    client: BibliotalkDiscordClient,
    config: DiscordRuntimeConfig,
    session_factory: async_sessionmaker[AsyncSession],
    logger_: logging.Logger,
) -> None:
    # Best-effort feed publication; talk UX does not depend on it.
    try:
        transport = DiscordPyFeedTransport(client)
        await publish_pending_feeds(
            config,
            transport=transport,
            session_factory=session_factory,
            logger_=logger_,
        )
    except Exception:
        logger_.exception("feed publication on ready failed")
