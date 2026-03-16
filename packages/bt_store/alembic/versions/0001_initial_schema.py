"""Initial bt_store schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("agent_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("persona_prompt", sa.String(), nullable=False),
        sa.Column("llm_model", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_agents_is_active"), "agents", ["is_active"], unique=False)
    op.create_index(op.f("ix_agents_kind"), "agents", ["kind"], unique=False)

    op.create_table(
        "agent_platform_identities",
        sa.Column("identity_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("platform_user_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("platform", "platform_user_id"),
        sa.UniqueConstraint("agent_id", "platform"),
    )
    op.create_index(
        op.f("ix_agent_platform_identities_agent_id"),
        "agent_platform_identities",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_platform_identities_platform"),
        "agent_platform_identities",
        ["platform"],
        unique=False,
    )

    op.create_table(
        "rooms",
        sa.Column("room_pk", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("room_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("owner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("platform", "room_id"),
    )
    op.create_index(op.f("ix_rooms_kind"), "rooms", ["kind"], unique=False)
    op.create_index(op.f("ix_rooms_owner_agent_id"), "rooms", ["owner_agent_id"], unique=False)
    op.create_index(op.f("ix_rooms_platform"), "rooms", ["platform"], unique=False)

    op.create_table(
        "sources",
        sa.Column("source_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("content_platform", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("external_url", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("author", sa.String(length=512), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_meta_json", sa.JSON(), nullable=True),
        sa.Column("emos_group_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_id", "content_platform", "external_id"),
    )
    op.create_index(op.f("ix_sources_agent_id"), "sources", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_sources_content_platform"), "sources", ["content_platform"], unique=False
    )
    op.create_index(op.f("ix_sources_emos_group_id"), "sources", ["emos_group_id"], unique=False)

    op.create_table(
        "segments",
        sa.Column("segment_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("speaker", sa.String(length=255), nullable=True),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.Column("emos_message_id", sa.String(length=255), nullable=False),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
            name=op.f("fk_segments_source_id_sources"),
        ),
        sa.UniqueConstraint("source_id", "seq"),
    )
    op.create_index(op.f("ix_segments_agent_id"), "segments", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_segments_emos_message_id"), "segments", ["emos_message_id"], unique=False
    )
    op.create_index(op.f("ix_segments_source_id"), "segments", ["source_id"], unique=False)
    op.create_index(
        "ix_segments_agent_source_seq",
        "segments",
        ["agent_id", "source_id", "seq"],
        unique=False,
    )

    op.create_table(
        "chat_history",
        sa.Column("chat_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("room_id", sa.String(length=255), nullable=False),
        sa.Column("sender_agent_id", sa.Uuid(), nullable=True),
        sa.Column("sender_platform_user_id", sa.String(length=255), nullable=False),
        sa.Column("platform_event_id", sa.String(length=255), nullable=True),
        sa.Column("modality", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sender_agent_id"],
            ["agents.agent_id"],
            name=op.f("fk_chat_history_sender_agent_id_agents"),
        ),
    )
    op.create_index(op.f("ix_chat_history_modality"), "chat_history", ["modality"], unique=False)
    op.create_index(op.f("ix_chat_history_platform"), "chat_history", ["platform"], unique=False)
    op.create_index(op.f("ix_chat_history_room_id"), "chat_history", ["room_id"], unique=False)

    op.create_table(
        "platform_posts",
        sa.Column("post_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("platform_event_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.agent_id"],
            name=op.f("fk_platform_posts_agent_id_agents"),
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"],
            ["segments.segment_id"],
            name=op.f("fk_platform_posts_segment_id_segments"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
            name=op.f("fk_platform_posts_source_id_sources"),
        ),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_platform_posts_agent_id"), "platform_posts", ["agent_id"], unique=False
    )
    op.create_index(op.f("ix_platform_posts_kind"), "platform_posts", ["kind"], unique=False)
    op.create_index(
        op.f("ix_platform_posts_platform"), "platform_posts", ["platform"], unique=False
    )
    op.create_index(op.f("ix_platform_posts_room_id"), "platform_posts", ["room_id"], unique=False)
    op.create_index(
        op.f("ix_platform_posts_segment_id"), "platform_posts", ["segment_id"], unique=False
    )
    op.create_index(
        op.f("ix_platform_posts_source_id"), "platform_posts", ["source_id"], unique=False
    )
    op.create_index(op.f("ix_platform_posts_status"), "platform_posts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("platform_posts")
    op.drop_table("chat_history")
    op.drop_index("ix_segments_agent_source_seq", table_name="segments")
    op.drop_table("segments")
    op.drop_table("sources")
    op.drop_table("rooms")
    op.drop_table("agent_platform_identities")
    op.drop_table("agents")
