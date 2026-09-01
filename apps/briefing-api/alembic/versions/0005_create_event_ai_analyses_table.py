"""create event ai analyses table

Revision ID: 0005_event_ai_analyses
Revises: 0004_create_news_events_tables
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_event_ai_analyses"
down_revision: str | None = "0004_create_news_events_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("pending", "success", "failed", "skipped")
IMPORTANCE_TIERS = ("critical", "important", "monitor", "low")
SENTIMENTS = ("positive", "neutral", "negative", "mixed", "unknown")


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "event_ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("short_summary", sa.String(length=500), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("key_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sentiment", sa.String(length=50), nullable=True),
        sa.Column("relevance_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("urgency_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("importance_tier", sa.String(length=50), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("affected_business_area", sa.String(length=255), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "prompt_version",
            sa.String(length=50),
            server_default="phase5_v1",
            nullable=False,
        ),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("content_signature", sa.String(length=64), nullable=True),
        sa.Column("source_article_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("primary_article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_article_count", sa.Integer(), server_default="0", nullable=False),
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
            f"status IN ({_check_values(STATUSES)})",
            name="ck_event_ai_analyses_status",
        ),
        sa.CheckConstraint(
            f"importance_tier IS NULL OR importance_tier IN ({_check_values(IMPORTANCE_TIERS)})",
            name="ck_event_ai_analyses_importance_tier",
        ),
        sa.CheckConstraint(
            f"sentiment IS NULL OR sentiment IN ({_check_values(SENTIMENTS)})",
            name="ck_event_ai_analyses_sentiment",
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_event_ai_analyses_relevance_score_range",
        ),
        sa.CheckConstraint(
            "urgency_score IS NULL OR (urgency_score >= 0 AND urgency_score <= 1)",
            name="ck_event_ai_analyses_urgency_score_range",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_event_ai_analyses_confidence_score_range",
        ),
        sa.CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
            name="ck_event_ai_analyses_prompt_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_event_ai_analyses_completion_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_event_ai_analyses_total_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "context_article_count >= 0",
            name="ck_event_ai_analyses_context_article_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_article_id"], ["articles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_ai_analyses_event_id_unique",
        "event_ai_analyses",
        ["event_id"],
        unique=True,
    )
    op.create_index("ix_event_ai_analyses_status", "event_ai_analyses", ["status"])
    op.create_index(
        "ix_event_ai_analyses_importance_tier",
        "event_ai_analyses",
        ["importance_tier"],
    )
    op.create_index(
        "ix_event_ai_analyses_relevance_score",
        "event_ai_analyses",
        ["relevance_score"],
    )
    op.create_index("ix_event_ai_analyses_urgency_score", "event_ai_analyses", ["urgency_score"])
    op.create_index("ix_event_ai_analyses_created_at", "event_ai_analyses", ["created_at"])
    op.create_index("ix_event_ai_analyses_updated_at", "event_ai_analyses", ["updated_at"])
    op.create_index(
        "ix_event_ai_analyses_primary_article_id",
        "event_ai_analyses",
        ["primary_article_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_ai_analyses_primary_article_id", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_updated_at", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_created_at", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_urgency_score", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_relevance_score", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_importance_tier", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_status", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_event_id_unique", table_name="event_ai_analyses")
    op.drop_table("event_ai_analyses")
