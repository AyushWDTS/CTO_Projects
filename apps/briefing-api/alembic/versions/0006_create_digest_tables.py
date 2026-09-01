"""create digest tables

Revision ID: 0006_create_digest_tables
Revises: 0005_event_ai_analyses
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_create_digest_tables"
down_revision: str | None = "0005_event_ai_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIGEST_STATUSES = ("draft", "finalized", "archived")
DIGEST_SECTIONS = (
    "Critical Alerts",
    "Gaming and Casino Market",
    "Regulatory and Compliance",
    "Technology and Operations",
    "Market/Competitor Intelligence",
    "Monitor List",
)


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
        sa.Column("total_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_selected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("critical_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("important_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("monitor_count", sa.Integer(), server_default="0", nullable=False),
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
            f"status IN ({_check_values(DIGEST_STATUSES)})",
            name="ck_digests_status",
        ),
        sa.CheckConstraint(
            "total_candidates >= 0",
            name="ck_digests_total_candidates_non_negative",
        ),
        sa.CheckConstraint(
            "total_selected >= 0",
            name="ck_digests_total_selected_non_negative",
        ),
        sa.CheckConstraint(
            "critical_count >= 0",
            name="ck_digests_critical_count_non_negative",
        ),
        sa.CheckConstraint(
            "important_count >= 0",
            name="ck_digests_important_count_non_negative",
        ),
        sa.CheckConstraint("monitor_count >= 0", name="ck_digests_monitor_count_non_negative"),
        sa.CheckConstraint("window_start < window_end", name="ck_digests_valid_window"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_digests_window_unique",
        "digests",
        ["digest_date", "window_start", "window_end"],
        unique=True,
    )
    op.create_index("ix_digests_digest_date", "digests", ["digest_date"])
    op.create_index("ix_digests_status", "digests", ["status"])
    op.create_index("ix_digests_window_start", "digests", ["window_start"])
    op.create_index("ix_digests_window_end", "digests", ["window_end"])

    op.create_table(
        "digest_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_ai_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=100), nullable=False),
        sa.Column("final_score", sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("urgency_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("source_authority_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("recency_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("business_impact_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("importance_tier", sa.String(length=50), nullable=True),
        sa.Column("headline", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"section IN ({_check_values(DIGEST_SECTIONS)})",
            name="ck_digest_items_section",
        ),
        sa.CheckConstraint("rank > 0", name="ck_digest_items_rank_positive"),
        sa.CheckConstraint(
            "final_score >= 0 AND final_score <= 1",
            name="ck_digest_items_final_score_range",
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_digest_items_relevance_score_range",
        ),
        sa.CheckConstraint(
            "urgency_score IS NULL OR (urgency_score >= 0 AND urgency_score <= 1)",
            name="ck_digest_items_urgency_score_range",
        ),
        sa.CheckConstraint(
            "source_authority_score IS NULL OR "
            "(source_authority_score >= 0 AND source_authority_score <= 1)",
            name="ck_digest_items_source_authority_score_range",
        ),
        sa.CheckConstraint(
            "recency_score IS NULL OR (recency_score >= 0 AND recency_score <= 1)",
            name="ck_digest_items_recency_score_range",
        ),
        sa.CheckConstraint(
            "business_impact_score IS NULL OR "
            "(business_impact_score >= 0 AND business_impact_score <= 1)",
            name="ck_digest_items_business_impact_score_range",
        ),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["event_ai_analysis_id"],
            ["event_ai_analyses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_digest_items_digest_event_unique",
        "digest_items",
        ["digest_id", "event_id"],
        unique=True,
    )
    op.create_index(
        "ix_digest_items_digest_rank_unique",
        "digest_items",
        ["digest_id", "rank"],
        unique=True,
    )
    op.create_index("ix_digest_items_digest_id", "digest_items", ["digest_id"])
    op.create_index("ix_digest_items_event_id", "digest_items", ["event_id"])
    op.create_index("ix_digest_items_section", "digest_items", ["section"])
    op.create_index("ix_digest_items_rank", "digest_items", ["rank"])
    op.create_index("ix_digest_items_final_score", "digest_items", ["final_score"])
    op.create_index("ix_digest_items_importance_tier", "digest_items", ["importance_tier"])


def downgrade() -> None:
    op.drop_index("ix_digest_items_importance_tier", table_name="digest_items")
    op.drop_index("ix_digest_items_final_score", table_name="digest_items")
    op.drop_index("ix_digest_items_rank", table_name="digest_items")
    op.drop_index("ix_digest_items_section", table_name="digest_items")
    op.drop_index("ix_digest_items_event_id", table_name="digest_items")
    op.drop_index("ix_digest_items_digest_id", table_name="digest_items")
    op.drop_index("ix_digest_items_digest_rank_unique", table_name="digest_items")
    op.drop_index("ix_digest_items_digest_event_unique", table_name="digest_items")
    op.drop_table("digest_items")

    op.drop_index("ix_digests_window_end", table_name="digests")
    op.drop_index("ix_digests_window_start", table_name="digests")
    op.drop_index("ix_digests_status", table_name="digests")
    op.drop_index("ix_digests_digest_date", table_name="digests")
    op.drop_index("ix_digests_window_unique", table_name="digests")
    op.drop_table("digests")
