from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from bt_common.evermemos_client import EverMemOSClient
from bt_common.evidence_store.models import Figure, IngestState, Source, Subscription
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..adapters.youtube_transcript import load_youtube_transcript_source
from ..domain.errors import IngestError
from ..pipeline.discovery import DiscoveredVideo, discover_subscription
from ..pipeline.index import IngestionIndex
from ..pipeline.ingest import ingest_source, manual_reingest_source
from .config import RuntimeConfig


class SubscriptionConcurrencyGate:
    def __init__(self, *, global_limit: int) -> None:
        self._global = asyncio.Semaphore(max(1, global_limit))
        self._locks: dict[UUID, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def run(self, subscription_id: UUID, operation: Callable[[], Awaitable[object]]):
        async with self._global:
            lock = await self._get_lock(subscription_id)
            async with lock:
                return await operation()

    async def _get_lock(self, subscription_id: UUID) -> asyncio.Lock:
        async with self._locks_guard:
            lock = self._locks.get(subscription_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[subscription_id] = lock
            return lock


@dataclass(slots=True)
class PollerSnapshot:
    active_subscriptions: int
    figure_slug: str | None
    discovered_videos: int = 0
    ingested_videos: int = 0
    failed_subscriptions: int = 0


class CollectorPoller:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        session_factory: async_sessionmaker[AsyncSession],
        logger,
        client: EverMemOSClient | None = None,
        discovery_fn: Callable[..., Awaitable[list[DiscoveredVideo]]] | None = None,
        transcript_loader: Callable[..., Awaitable[object]] | None = None,
    ):
        self.config = config
        self.session_factory = session_factory
        self.logger = logger
        self.client = client
        self.discovery_fn = discovery_fn or discover_subscription
        self.transcript_loader = transcript_loader or load_youtube_transcript_source
        self._stopped = asyncio.Event()
        self._subscription_gate = SubscriptionConcurrencyGate(
            global_limit=self.config.global_concurrency
        )

    async def run_once(self) -> PollerSnapshot:
        discovered_videos = 0
        ingested_videos = 0
        failed_subscriptions = 0

        async with self.session_factory() as session:
            stmt = (
                select(Subscription, Figure)
                .join(Figure, Figure.figure_id == Subscription.figure_id)
                .where(Subscription.is_active.is_(True))
            )
            if self.config.figure_slug:
                stmt = stmt.where(Figure.emos_user_id == self.config.figure_slug)
            subscription_rows = (await session.execute(stmt)).all()

        results = await asyncio.gather(
            *[
                self._subscription_gate.run(
                    subscription.subscription_id,
                    lambda subscription=subscription, figure=figure: self._process_subscription(
                        subscription=subscription,
                        figure=figure,
                    ),
                )
                for subscription, figure in subscription_rows
            ],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                failed_subscriptions += 1
                self.logger.exception("collector subscription task failed: %s", result)
                continue
            discovered_videos += result[0]
            ingested_videos += result[1]
            failed_subscriptions += result[2]

        self.logger.info(
            "collector poll tick figure_slug=%s subscriptions=%s discovered=%s ingested=%s failed=%s",
            self.config.figure_slug or "*",
            len(subscription_rows),
            discovered_videos,
            ingested_videos,
            failed_subscriptions,
        )
        return PollerSnapshot(
            active_subscriptions=len(subscription_rows),
            figure_slug=self.config.figure_slug,
            discovered_videos=discovered_videos,
            ingested_videos=ingested_videos,
            failed_subscriptions=failed_subscriptions,
        )

    async def _process_subscription(
        self,
        *,
        subscription: Subscription,
        figure: Figure,
    ) -> tuple[int, int, int]:
        if self.client is None:
            return (0, 0, 0)

        now = datetime.now(tz=UTC)
        discovered_count = 0
        ingested_count = 0

        try:
            async with self.session_factory() as session:
                ingest_state = await session.get(IngestState, subscription.subscription_id)
                if ingest_state is None:
                    ingest_state = IngestState(subscription_id=subscription.subscription_id)
                    session.add(ingest_state)
                    await session.commit()
                    await session.refresh(ingest_state)

                if ingest_state.next_retry_at and ingest_state.next_retry_at > now:
                    return (0, 0, 0)

                discovered = await self.discovery_fn(
                    subscription.subscription_url,
                    last_seen_video_id=ingest_state.last_seen_video_id,
                    last_published_at=ingest_state.last_published_at,
                    bootstrap=(
                        ingest_state.last_polled_at is None
                        and ingest_state.last_seen_video_id is None
                        and ingest_state.last_published_at is None
                    ),
                )
                discovered_count = len(discovered)

                for source_row in await self._load_manual_reingest_sources(figure.figure_id):
                    source_content = await self.transcript_loader(
                        user_id=figure.emos_user_id,
                        external_id=source_row.external_id,
                        title=source_row.title,
                        video_id=source_row.external_id,
                        source_url=source_row.source_url,
                    )
                    result = await manual_reingest_source(
                        source_content=source_content,
                        index=IngestionIndex(self.session_factory, path=self.config.index_path),
                        client=self.client,
                    )
                    if result.status != "done":
                        raise IngestError(
                            f"manual reingest failed for source {source_row.external_id}",
                            code="INGEST_FAILED",
                        )
                    ingested_count += 1

                for item in discovered:
                    source_content = await self.transcript_loader(
                        user_id=figure.emos_user_id,
                        external_id=item.video_id,
                        title=item.title,
                        video_id=item.video_id,
                        source_url=item.source_url,
                    )
                    result = await ingest_source(
                        source_content=source_content,
                        index=IngestionIndex(self.session_factory, path=self.config.index_path),
                        client=self.client,
                    )
                    if result.status != "done":
                        raise IngestError(
                            f"ingest failed for video {item.video_id}",
                            code="INGEST_FAILED",
                        )
                    ingested_count += 1

                latest = discovered[-1] if discovered else None
                ingest_state.last_polled_at = now
                if latest is not None:
                    ingest_state.last_seen_video_id = latest.video_id
                    ingest_state.last_published_at = latest.published_at
                ingest_state.failure_count = 0
                ingest_state.next_retry_at = None
                await session.commit()
            return (discovered_count, ingested_count, 0)
        except Exception:
            async with self.session_factory() as session:
                ingest_state = await session.get(IngestState, subscription.subscription_id)
                if ingest_state is None:
                    ingest_state = IngestState(subscription_id=subscription.subscription_id)
                    session.add(ingest_state)
                ingest_state.last_polled_at = now
                ingest_state.failure_count += 1
                backoff_minutes = min(
                    subscription.poll_interval_minutes
                    * (2 ** max(0, ingest_state.failure_count - 1)),
                    24 * 60,
                )
                ingest_state.next_retry_at = now + timedelta(minutes=backoff_minutes)
                await session.commit()
            raise

    async def _load_manual_reingest_sources(self, figure_id) -> list[Source]:
        async with self.session_factory() as session:
            stmt = (
                select(Source)
                .where(
                    Source.figure_id == figure_id,
                    Source.manual_ingestion_requested_at.is_not(None),
                )
                .order_by(Source.manual_ingestion_requested_at.asc())
            )
            return list((await session.execute(stmt)).scalars().all())

    async def run_forever(self) -> None:
        while not self._stopped.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(
                    self._stopped.wait(),
                    timeout=self.config.poll_interval_minutes * 60,
                )
            except TimeoutError:
                continue

    def stop(self) -> None:
        self._stopped.set()
