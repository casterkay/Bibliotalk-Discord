# Data Model: YouTube → EverMemOS → Discord Figure Bots

**Phase 1 output for:** `003-discord-bot`
**Date:** 2026-03-07
**Status:** Deprecated (schema moved to `packages/bt_store/`)

All services now share a single relational schema owned by `bt_store` (SQLite for local dev; Postgres for prod). The old
`bt_common.evidence_store` module has been quarantined; if you need to migrate an existing legacy SQLite DB, use
`scripts/backfill_bt_store_v2.py`.

---

## ORM Models

```python
"""SQLAlchemy 2.x async ORM models for the Bibliotalk figure-bot system."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

class Figure(Base):
    """A public figure whose YouTube content is tracked and memorized."""

    __tablename__ = "figures"

    figure_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    emos_user_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )  # readable slug e.g. "alan-watts" — immutable once deployed
    persona_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # "active" | "paused" | "archived"

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )
    sources: Mapped[list[Source]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class Subscription(Base):
    """A YouTube channel or playlist URL polled for new videos."""

    __tablename__ = "subscriptions"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    figure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("figures.figure_id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, default="youtube"
    )
    subscription_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "channel" | "playlist"
    subscription_url: Mapped[str] = mapped_column(Text, nullable=False)
    poll_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    figure: Mapped[Figure] = relationship(back_populates="subscriptions")
    ingest_state: Mapped[IngestState | None] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_subscriptions_figure_id", "figure_id"),
    )


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------

class Source(Base):
    """A single YouTube video associated with a figure."""

    __tablename__ = "sources"

    source_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    figure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("figures.figure_id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, default="youtube"
    )
    external_id: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # YouTube video_id — immutable idempotency key
    group_id: Mapped[str] = mapped_column(
        String(300), nullable=False
    )  # "{emos_user_id}:youtube:{video_id}"
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    channel_name: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_meta_json: Mapped[str | None] = mapped_column(Text)  # JSON blob from yt-dlp
    transcript_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending" | "ingested" | "failed" | "no_transcript"
    manual_ingestion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    figure: Mapped[Figure] = relationship(back_populates="sources")
    segments: Mapped[list[Segment]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    transcript_batches: Mapped[list[TranscriptBatch]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("figure_id", "platform", "external_id", name="uq_source_identity"),
        Index("ix_sources_figure_id", "figure_id"),
        Index("ix_sources_group_id", "group_id"),
    )


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

class Segment(Base):
    """One atomic chunk of verbatim transcript text — the evidence atom."""

    __tablename__ = "segments"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    start_ms: Mapped[int | None] = mapped_column(Integer)
    end_ms: Mapped[int | None] = mapped_column(Integer)
    # create_time = video_published_at + start_ms offset; used as EMOS timestamp
    create_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_superseded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # set True on manual re-ingest before replacement

    source: Mapped[Source] = relationship(back_populates="segments")

    __table_args__ = (
        # Deduplication key: same source + same position + same content = no new row
        UniqueConstraint("source_id", "seq", "sha256", name="uq_segment_dedup"),
        Index("ix_segments_source_id", "source_id"),
    )


# ---------------------------------------------------------------------------
# TranscriptBatch
# ---------------------------------------------------------------------------

class TranscriptBatch(Base):
    """
    A locally grouped run of adjacent segments for Discord feed posting.
    NOT derived from EMOS MemCells — contains only verbatim segment text.
    """

    __tablename__ = "transcript_batches"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False
    )
    speaker_label: Mapped[str | None] = mapped_column(String(200))
    start_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    end_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int | None] = mapped_column(Integer)
    end_ms: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    batch_rule: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "silence_gap" | "char_limit" | "speaker_change"
    posted_to_discord: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    source: Mapped[Source] = relationship(back_populates="transcript_batches")

    __table_args__ = (
        Index("ix_transcript_batches_source_id", "source_id"),
        Index("ix_transcript_batches_unposted", "source_id", "posted_to_discord"),
    )


# ---------------------------------------------------------------------------
# IngestState
# ---------------------------------------------------------------------------

class IngestState(Base):
    """Discovery cursor and failure tracking per subscription."""

    __tablename__ = "ingest_state"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.subscription_id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_seen_video_id: Mapped[str | None] = mapped_column(String(200))
    last_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subscription: Mapped[Subscription] = relationship(back_populates="ingest_state")


# ---------------------------------------------------------------------------
# DiscordMap
# ---------------------------------------------------------------------------

class DiscordMap(Base):
    """Associates a figure with its Discord guild, feed channel, and bot identifiers."""

    __tablename__ = "discord_map"

    figure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("figures.figure_id", ondelete="CASCADE"),
        primary_key=True,
    )
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(30), nullable=False)
    bot_application_id: Mapped[str | None] = mapped_column(String(30))
    bot_user_id: Mapped[str | None] = mapped_column(String(30))


# ---------------------------------------------------------------------------
# DiscordPost
# ---------------------------------------------------------------------------

class DiscordPost(Base):
    """
    Records whether each (source, batch) pair has been posted to Discord.
    Enables idempotent retry: skip already-posted batches on failure/resume.
    """

    __tablename__ = "discord_posts"

    post_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    figure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("figures.figure_id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False
    )
    parent_message_id: Mapped[str | None] = mapped_column(String(30))
    thread_id: Mapped[str | None] = mapped_column(String(30))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transcript_batches.batch_id", ondelete="SET NULL")
    )  # NULL = the parent-message post itself
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    post_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending" | "posted" | "failed"

    __table_args__ = (
        # Deduplication key: one post per (source, batch); NULL batch_id = parent post
        UniqueConstraint("source_id", "batch_id", name="uq_discord_post_dedup"),
        Index("ix_discord_posts_source_id", "source_id"),
        Index("ix_discord_posts_pending", "figure_id", "post_status"),
    )
```

---

## Required Query Patterns

| Query                                                     | How Satisfied                                                                                                                                               |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Given EMOS `group_id` values, fetch all local segments    | `SELECT segments.* FROM segments JOIN sources ON sources.source_id = segments.source_id WHERE sources.group_id IN (...)` — covered by `ix_sources_group_id` |
| Given `segment_id`, fetch verbatim text                   | Primary key lookup on `segments.segment_id`                                                                                                                 |
| Given EMOS `(user_id, timestamp)`, reconstruct timepoint  | Join `figures` on `emos_user_id = user_id` → `sources.published_at` + `segment.start_ms` derived from `segment.create_time - source.published_at`           |
| Given `source_id`, fetch unposted transcript batches      | `WHERE source_id = ? AND posted_to_discord = FALSE ORDER BY start_seq` — covered by `ix_transcript_batches_unposted`                                        |
| Given `figure_id`, fetch all segments for reranking       | Join `sources → segments` filtered by `figure_id`                                                                                                           |
| Given `source_id` or `video_id`, check Discord post state | `SELECT * FROM discord_posts WHERE source_id = ?`                                                                                                           |

---

## Entity Identifier Summary

| Entity                | ID             | Format                                                                                         |
| --------------------- | -------------- | ---------------------------------------------------------------------------------------------- |
| Figure                | `figure_id`    | UUID v4, internal PK                                                                           |
| Figure (EMOS)         | `emos_user_id` | Readable slug `"alan-watts"` — immutable                                                       |
| YouTube video         | `external_id`  | YouTube `video_id` string                                                                      |
| EMOS group            | `group_id`     | `"{emos_user_id}:youtube:{video_id}"`                                                          |
| EMOS message          | `message_id`   | `"{emos_user_id}:youtube:{video_id}:seg:{seq}"` (constructed at ingest time, not stored in DB) |
| Segment `create_time` | EMOS timestamp | `video_published_at + start_ms_offset` as UTC datetime                                         |
| Memory URL            | —              | `https://www.bibliotalk.space/memory/{emos_user_id}_{create_time_iso}`                         |
