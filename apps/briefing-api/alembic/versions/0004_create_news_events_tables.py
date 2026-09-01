"""create news events tables

Revision ID: 0004_create_news_events_tables
Revises: 0003_create_articles_table
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_create_news_events_tables"
down_revision: str | None = "0003_create_articles_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENT_STATUSES = ("active", "needs_review", "archived")
MATCH_TYPES = (
    "exact_url",
    "exact_source_url",
    "exact_hash",
    "title_similarity",
    "text_similarity",
    "manual",
)


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "news_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_title", sa.String(length=500), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("normalized_canonical_url", sa.Text(), nullable=True),
        sa.Column("primary_article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("article_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column(
            "confidence_score",
            sa.Numeric(precision=4, scale=3),
            server_default="0.000",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            f"status IN ({_check_values(EVENT_STATUSES)})",
            name="ck_news_events_status",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_news_events_confidence_score_range",
        ),
        sa.CheckConstraint("article_count >= 0", name="ck_news_events_article_count_non_negative"),
        sa.CheckConstraint("source_count >= 0", name="ck_news_events_source_count_non_negative"),
        sa.ForeignKeyConstraint(["primary_article_id"], ["articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["primary_source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_news_events_event_key_unique", "news_events", ["event_key"], unique=True)
    op.create_index("ix_news_events_status", "news_events", ["status"])
    op.create_index("ix_news_events_category", "news_events", ["category"])
    op.create_index("ix_news_events_region", "news_events", ["region"])
    op.create_index("ix_news_events_published_at", "news_events", ["published_at"])
    op.create_index("ix_news_events_first_seen_at", "news_events", ["first_seen_at"])
    op.create_index("ix_news_events_last_seen_at", "news_events", ["last_seen_at"])
    op.create_index("ix_news_events_primary_source_id", "news_events", ["primary_source_id"])
    op.create_index(
        "ix_news_events_normalized_canonical_url",
        "news_events",
        ["normalized_canonical_url"],
    )

    op.create_table(
        "event_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_type", sa.String(length=50), nullable=False),
        sa.Column(
            "similarity_score",
            sa.Numeric(precision=4, scale=3),
            server_default="0.000",
            nullable=False,
        ),
        sa.Column(
            "confidence_score",
            sa.Numeric(precision=4, scale=3),
            server_default="0.000",
            nullable=False,
        ),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("match_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"match_type IN ({_check_values(MATCH_TYPES)})",
            name="ck_event_articles_match_type",
        ),
        sa.CheckConstraint(
            "similarity_score >= 0 AND similarity_score <= 1",
            name="ck_event_articles_similarity_score_range",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_event_articles_confidence_score_range",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_articles_article_id_unique",
        "event_articles",
        ["article_id"],
        unique=True,
    )
    op.create_index(
        "ix_event_articles_one_primary_per_event",
        "event_articles",
        ["event_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )
    op.create_index("ix_event_articles_event_id", "event_articles", ["event_id"])
    op.create_index("ix_event_articles_article_id", "event_articles", ["article_id"])
    op.create_index("ix_event_articles_source_id", "event_articles", ["source_id"])
    op.create_index("ix_event_articles_match_type", "event_articles", ["match_type"])
    op.create_index("ix_event_articles_is_primary", "event_articles", ["is_primary"])


def downgrade() -> None:
    op.drop_index("ix_event_articles_is_primary", table_name="event_articles")
    op.drop_index("ix_event_articles_match_type", table_name="event_articles")
    op.drop_index("ix_event_articles_source_id", table_name="event_articles")
    op.drop_index("ix_event_articles_article_id", table_name="event_articles")
    op.drop_index("ix_event_articles_event_id", table_name="event_articles")
    op.drop_index("ix_event_articles_one_primary_per_event", table_name="event_articles")
    op.drop_index("ix_event_articles_article_id_unique", table_name="event_articles")
    op.drop_table("event_articles")

    op.drop_index("ix_news_events_normalized_canonical_url", table_name="news_events")
    op.drop_index("ix_news_events_primary_source_id", table_name="news_events")
    op.drop_index("ix_news_events_last_seen_at", table_name="news_events")
    op.drop_index("ix_news_events_first_seen_at", table_name="news_events")
    op.drop_index("ix_news_events_published_at", table_name="news_events")
    op.drop_index("ix_news_events_region", table_name="news_events")
    op.drop_index("ix_news_events_category", table_name="news_events")
    op.drop_index("ix_news_events_status", table_name="news_events")
    op.drop_index("ix_news_events_event_key_unique", table_name="news_events")
    op.drop_table("news_events")
