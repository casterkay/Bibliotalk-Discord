"""Add source_meta_synced_at to sources.

Revision ID: 0002_add_source_meta_synced_at
Revises: 0001_initial_schema
Create Date: 2026-03-07 00:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_add_source_meta_synced_at"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources", sa.Column("source_meta_synced_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sources", "source_meta_synced_at")
