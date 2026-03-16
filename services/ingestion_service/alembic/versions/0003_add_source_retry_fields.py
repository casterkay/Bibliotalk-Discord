"""Add per-source retry metadata and subscription linkage.

Revision ID: 0003_add_source_retry_fields
Revises: 0002_add_source_meta_synced_at
Create Date: 2026-03-16 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_add_source_retry_fields"
down_revision = "0002_add_source_meta_synced_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column(
            "subscription_id",
            sa.Uuid(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_sources_subscription_id",
        "sources",
        "subscriptions",
        ["subscription_id"],
        ["subscription_id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "sources",
        sa.Column(
            "transcript_failure_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sources",
        sa.Column("transcript_last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("transcript_next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("transcript_skip_reason", sa.String(length=80), nullable=True),
    )
    op.create_index("ix_sources_subscription_id", "sources", ["subscription_id"])
    op.create_index(
        "ix_sources_transcript_retry",
        "sources",
        ["subscription_id", "transcript_next_retry_at"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_sources_subscription_id", "sources", type_="foreignkey")
    op.drop_index("ix_sources_transcript_retry", table_name="sources")
    op.drop_index("ix_sources_subscription_id", table_name="sources")
    op.drop_column("sources", "transcript_skip_reason")
    op.drop_column("sources", "transcript_next_retry_at")
    op.drop_column("sources", "transcript_last_attempt_at")
    op.drop_column("sources", "transcript_failure_count")
    op.drop_column("sources", "subscription_id")
