from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import Figure, IngestState, Subscription, TranscriptBatch
from bt_common.evidence_store.models import Segment as StoredSegment
from bt_common.evidence_store.models import Source as StoredSource
from ingestion_service.domain.models import Source, SourceContent, TranscriptContent, TranscriptLine
from ingestion_service.pipeline.discovery import DiscoveredVideo
from ingestion_service.pipeline.index import IngestionIndex
from ingestion_service.pipeline.ingest import ingest_source, manual_reingest_source
from ingestion_service.runtime.config import load_runtime_config
from ingestion_service.runtime.poller import CollectorPoller
from ingestion_service.runtime.reporting import configure_logging
from sqlalchemy import func, select


class StubEverMemOS:
    def __init__(self) -> None:
        self.memorize_calls: list[dict] = []
        self.meta_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.memorize_results: list[object] = []

    async def memorize(self, payload: dict) -> dict:
        self.memorize_calls.append(payload)
        if self.memorize_results:
            value = self.memorize_results.pop(0)
            if isinstance(value, Exception):
                raise value
        return {"ok": True}

    async def save_conversation_meta(self, *, group_id: str, source_meta: dict) -> dict:
        self.meta_calls.append({"group_id": group_id, "source_meta": source_meta})
        return {"ok": True}

    async def delete_by_group_id(self, group_id: str, *, user_id: str | None = None) -> dict:
        self.delete_calls.append({"group_id": group_id, "user_id": user_id})
        return {"ok": True}


def _build_source_content(*, text_a: str = "One.", text_b: str = "Two.") -> SourceContent:
    source = Source(
        user_id="alan-watts",
        external_id="abc123",
        title="Alan Watts Lecture",
        source_url="https://www.youtube.com/watch?v=abc123",
        channel_name="Alan Watts Org",
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        raw_meta={"timestamp": 1704067200},
    )
    return SourceContent(
        source=source,
        content=TranscriptContent(
            lines=[
                TranscriptLine(text=text_a, start_ms=0, end_ms=900),
                TranscriptLine(text=text_b, start_ms=1200, end_ms=2200),
            ]
        ),
    )


@pytest.mark.anyio
async def test_ingest_persists_sources_segments_and_batches_without_duplicates(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    index = IngestionIndex(session_factory, path=db)
    client = StubEverMemOS()

    async with session_factory() as session:
        session.add(
            Figure(
                figure_id=uuid.uuid4(),
                display_name="Alan Watts",
                emos_user_id="alan-watts",
            )
        )
        await session.commit()

    first = await ingest_source(
        source_content=_build_source_content(),
        index=index,
        client=client,
    )
    second = await ingest_source(
        source_content=_build_source_content(),
        index=index,
        client=client,
    )

    assert first.status == "done"
    assert second.segments_skipped_unchanged == 2
    assert len(client.meta_calls) == 1
    assert len(client.memorize_calls) == 2

    async with session_factory() as session:
        stored_source = (await session.execute(select(StoredSource))).scalar_one()
        segment_count = await session.scalar(select(func.count()).select_from(StoredSegment))
        batch_count = await session.scalar(select(func.count()).select_from(TranscriptBatch))

    assert stored_source.group_id == "alan-watts:youtube:abc123"
    assert stored_source.transcript_status == "ingested"
    assert stored_source.source_meta_synced_at is not None
    assert segment_count == 2
    assert batch_count >= 1


@pytest.mark.anyio
async def test_manual_reingest_deletes_remote_memories_and_supersedes_old_segments(
    tmp_path,
) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    index = IngestionIndex(session_factory, path=db)
    client = StubEverMemOS()

    async with session_factory() as session:
        session.add(
            Figure(
                figure_id=uuid.uuid4(),
                display_name="Alan Watts",
                emos_user_id="alan-watts",
            )
        )
        await session.commit()

    await ingest_source(source_content=_build_source_content(), index=index, client=client)
    client.memorize_calls.clear()

    result = await manual_reingest_source(
        source_content=_build_source_content(text_a="One revised.", text_b="Two revised."),
        index=index,
        client=client,
    )

    assert result.status == "done"
    assert client.delete_calls == [
        {"group_id": "alan-watts:youtube:abc123", "user_id": "alan-watts"}
    ]
    assert len(client.memorize_calls) == 2

    async with session_factory() as session:
        stored_source = (await session.execute(select(StoredSource))).scalar_one()
        segments = (
            (await session.execute(select(StoredSegment).order_by(StoredSegment.seq)))
            .scalars()
            .all()
        )
        batch_count = await session.scalar(select(func.count()).select_from(TranscriptBatch))

    assert stored_source.transcript_status == "ingested"
    assert len(segments) == 2
    assert all("revised" in segment.text for segment in segments)
    assert batch_count >= 1


@pytest.mark.anyio
async def test_manual_reingest_same_content_succeeds_without_unique_constraint_conflict(
    tmp_path,
) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    index = IngestionIndex(session_factory, path=db)
    client = StubEverMemOS()

    async with session_factory() as session:
        session.add(
            Figure(
                figure_id=uuid.uuid4(),
                display_name="Alan Watts",
                emos_user_id="alan-watts",
            )
        )
        await session.commit()

    await ingest_source(source_content=_build_source_content(), index=index, client=client)
    client.memorize_calls.clear()

    result = await manual_reingest_source(
        source_content=_build_source_content(),
        index=index,
        client=client,
    )

    assert result.status == "done"
    assert len(client.memorize_calls) == 2

    async with session_factory() as session:
        segment_count = await session.scalar(select(func.count()).select_from(StoredSegment))

    assert segment_count == 2


@pytest.mark.anyio
async def test_segment_failure_marks_whole_transcript_failed_and_cleans_up(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    index = IngestionIndex(session_factory, path=db)
    client = StubEverMemOS()
    client.memorize_results = [{"ok": True}, RuntimeError("emos down")]

    async with session_factory() as session:
        session.add(
            Figure(
                figure_id=uuid.uuid4(),
                display_name="Alan Watts",
                emos_user_id="alan-watts",
            )
        )
        await session.commit()

    result = await ingest_source(
        source_content=_build_source_content(),
        index=index,
        client=client,
    )

    assert result.status == "failed"
    assert result.segments_ingested == 1
    assert result.segments_failed == 1
    assert client.delete_calls == [
        {"group_id": "alan-watts:youtube:abc123", "user_id": "alan-watts"}
    ]

    async with session_factory() as session:
        stored_source = (await session.execute(select(StoredSource))).scalar_one()
        segment_count = await session.scalar(select(func.count()).select_from(StoredSegment))
        batch_count = await session.scalar(select(func.count()).select_from(TranscriptBatch))

    assert stored_source.transcript_status == "failed"
    assert segment_count == 0
    assert batch_count == 0


@pytest.mark.anyio
async def test_collector_poll_once_ingests_new_video_and_skips_it_on_next_cycle(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    client = StubEverMemOS()

    async with session_factory() as session:
        figure = Figure(
            figure_id=uuid.uuid4(),
            display_name="Alan Watts",
            emos_user_id="alan-watts",
        )
        session.add(figure)
        await session.flush()
        session.add(
            Subscription(
                figure_id=figure.figure_id,
                subscription_type="channel",
                subscription_url="https://www.youtube.com/@AlanWattsOrg",
            )
        )
        await session.commit()

    async def fake_discovery(
        _: str,
        *,
        last_seen_video_id: str | None = None,
        last_published_at: datetime | None = None,
        bootstrap: bool = False,
    ) -> list[DiscoveredVideo]:
        del last_published_at, bootstrap
        if last_seen_video_id:
            return []
        return [
            DiscoveredVideo(
                video_id="abc123",
                title="Alan Watts Lecture",
                source_url="https://www.youtube.com/watch?v=abc123",
                published_at=datetime(2024, 1, 1, tzinfo=UTC),
                channel_name="Alan Watts Org",
                raw_meta={"timestamp": 1704067200},
            )
        ]

    async def fake_loader(**kwargs) -> SourceContent:
        del kwargs
        return _build_source_content()

    config = load_runtime_config(
        db_path=str(db),
        figure_slug="alan-watts",
        emos_base_url="https://emos.local",
        index_path=str(tmp_path / "index.sqlite3"),
    )
    poller = CollectorPoller(
        config=config,
        session_factory=session_factory,
        logger=configure_logging(),
        client=client,
        discovery_fn=fake_discovery,
        transcript_loader=fake_loader,
    )

    first = await poller.run_once()
    second = await poller.run_once()

    assert first.discovered_videos == 1
    assert first.ingested_videos == 1
    assert second.discovered_videos == 0
    assert second.ingested_videos == 0
    assert len(client.memorize_calls) == 2

    async with session_factory() as session:
        source_count = await session.scalar(select(func.count()).select_from(StoredSource))
        segment_count = await session.scalar(select(func.count()).select_from(StoredSegment))
        batch_count = await session.scalar(select(func.count()).select_from(TranscriptBatch))

    assert source_count == 1
    assert segment_count == 2
    assert batch_count >= 1


@pytest.mark.anyio
async def test_collector_does_not_advance_cursor_when_ingest_fails(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    client = StubEverMemOS()
    client.memorize_results = [RuntimeError("emos down")]

    async with session_factory() as session:
        figure = Figure(
            figure_id=uuid.uuid4(),
            display_name="Alan Watts",
            emos_user_id="alan-watts",
        )
        session.add(figure)
        await session.flush()
        subscription = Subscription(
            figure_id=figure.figure_id,
            subscription_type="channel",
            subscription_url="https://www.youtube.com/@AlanWattsOrg",
        )
        session.add(subscription)
        await session.commit()
        subscription_id = subscription.subscription_id

    async def fake_discovery(
        _: str,
        *,
        last_seen_video_id: str | None = None,
        last_published_at: datetime | None = None,
        bootstrap: bool = False,
    ) -> list[DiscoveredVideo]:
        del last_seen_video_id, last_published_at, bootstrap
        return [
            DiscoveredVideo(
                video_id="vid1",
                title="Broken Lecture",
                source_url="https://www.youtube.com/watch?v=vid1",
                published_at=datetime(2024, 1, 1, tzinfo=UTC),
                channel_name="Alan Watts Org",
                raw_meta={"timestamp": 1704067200},
            )
        ]

    async def fake_loader(**kwargs) -> SourceContent:
        del kwargs
        return SourceContent(
            source=Source(
                user_id="alan-watts",
                external_id="vid1",
                title="Broken Lecture",
                source_url="https://www.youtube.com/watch?v=vid1",
                published_at=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            content=TranscriptContent(lines=[TranscriptLine(text="One.", start_ms=0, end_ms=900)]),
        )

    config = load_runtime_config(
        db_path=str(db),
        figure_slug="alan-watts",
        emos_base_url="https://emos.local",
        index_path=str(tmp_path / "index.sqlite3"),
    )
    poller = CollectorPoller(
        config=config,
        session_factory=session_factory,
        logger=configure_logging(),
        client=client,
        discovery_fn=fake_discovery,
        transcript_loader=fake_loader,
    )

    snapshot = await poller.run_once()

    assert snapshot.failed_subscriptions == 1
    assert snapshot.ingested_videos == 0

    async with session_factory() as session:
        ingest_state = await session.get(IngestState, subscription_id)

    assert ingest_state is not None
    assert ingest_state.last_seen_video_id is None
    assert ingest_state.failure_count == 1
    assert ingest_state.next_retry_at is not None
