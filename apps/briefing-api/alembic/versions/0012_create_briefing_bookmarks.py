"""create briefing bookmarks table

Revision ID: 0012_briefing_bookmarks
Revises: 0011_remove_email_delivery
Create Date: 2026-08-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_briefing_bookmarks"
down_revision: str | None = "0011_remove_email_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "briefing_bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_key", sa.String(length=100), server_default="default", nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("digest_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("digest_date", sa.String(length=32), nullable=True),
        sa.Column("section", sa.String(length=120), nullable=True),
        sa.Column("headline", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("importance_tier", sa.String(length=50), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["digest_item_id"], ["digest_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_key", "event_id", name="uq_briefing_bookmarks_user_event"),
    )
    op.create_index("ix_briefing_bookmarks_user_key", "briefing_bookmarks", ["user_key"])
    op.create_index("ix_briefing_bookmarks_created_at", "briefing_bookmarks", ["created_at"])
    op.create_index("ix_briefing_bookmarks_digest_date", "briefing_bookmarks", ["digest_date"])


def downgrade() -> None:
    op.drop_index("ix_briefing_bookmarks_digest_date", table_name="briefing_bookmarks")
    op.drop_index("ix_briefing_bookmarks_created_at", table_name="briefing_bookmarks")
    op.drop_index("ix_briefing_bookmarks_user_key", table_name="briefing_bookmarks")
    op.drop_table("briefing_bookmarks")
