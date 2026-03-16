from __future__ import annotations

from datetime import UTC, datetime

from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import Figure, Source
from sqlalchemy import select


async def request_manual_ingest(
    *,
    db_path: str | None,
    figure_slug: str,
    video_id: str,
    title: str,
    source_url: str | None,
) -> None:
    await init_database(db_path)
    session_factory = get_session_factory(db_path)
    now = datetime.now(tz=UTC)

    async with session_factory() as session:
        figure = (
            (await session.execute(select(Figure).where(Figure.emos_user_id == figure_slug)))
            .scalars()
            .first()
        )
        if figure is None:
            raise LookupError(
                f"Figure '{figure_slug}' not found. Seed it first with `bibliotalk figure seed ...`."
            )

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
            effective_source_url = source_url or f"https://www.youtube.com/watch?v={video_id}"
            source = Source(
                figure_id=figure.figure_id,
                platform="youtube",
                external_id=video_id,
                group_id=f"{figure.emos_user_id}:youtube:{video_id}",
                title=title,
                source_url=effective_source_url,
                transcript_status="pending",
                manual_ingestion_requested_at=now,
            )
            session.add(source)
        else:
            source.manual_ingestion_requested_at = now
            if source_url:
                source.source_url = source_url
            if title and source.title.startswith("("):
                source.title = title

        await session.commit()
