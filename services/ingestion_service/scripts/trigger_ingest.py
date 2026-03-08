from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import Figure, Source
from sqlalchemy import select


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Request a manual one-shot ingest for a YouTube video"
    )
    parser.add_argument("--figure", dest="figure_slug", required=True)
    parser.add_argument("--video-id", dest="video_id", required=True)
    parser.add_argument("--title", dest="title", default="(manual ingest requested)")
    parser.add_argument("--source-url", dest="source_url")
    parser.add_argument("--db", dest="db_path")
    return parser


async def trigger_manual_ingest(
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
                f"Figure '{figure_slug}' not found. Seed it first with services/discord_service/scripts/seed_figure.py."
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


def main() -> int:
    args = build_parser().parse_args()
    try:
        asyncio.run(
            trigger_manual_ingest(
                db_path=args.db_path,
                figure_slug=args.figure_slug,
                video_id=args.video_id,
                title=args.title,
                source_url=args.source_url,
            )
        )
    except LookupError as exc:
        print(str(exc))
        return 1

    print(
        f"Manual ingest requested for '{args.figure_slug}' video '{args.video_id}'. Run ingestion_service with --once to process it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
