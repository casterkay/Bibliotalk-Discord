from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models_base import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id: Mapped[UUID] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    room_id: Mapped[str] = mapped_column(String(255), index=True)
    sender_agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agents.agent_id"), default=None
    )
    sender_platform_user_id: Mapped[str] = mapped_column(String(255))
    platform_event_id: Mapped[str | None] = mapped_column(String(255), default=None)
    modality: Mapped[str] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PlatformPost(Base):
    __tablename__ = "platform_posts"
    __table_args__ = (UniqueConstraint("idempotency_key"),)

    post_id: Mapped[UUID] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.agent_id"), index=True)
    room_id: Mapped[str] = mapped_column(String(255), index=True)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.source_id"), index=True)
    segment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("segments.segment_id"), index=True, default=None
    )
    idempotency_key: Mapped[str] = mapped_column(String(512))
    platform_event_id: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    error: Mapped[str | None] = mapped_column(String(1024), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
