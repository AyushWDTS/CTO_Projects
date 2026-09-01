"""create sources table

Revision ID: 0001_create_sources_table
Revises:
Create Date: 2026-05-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_create_sources_table"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPE_VALUES = (
    "rss",
    "news_site",
    "regulator",
    "government",
    "company_ir",
    "press_release",
    "blog",
    "newsletter",
    "social",
    "youtube",
    "filing",
    "other",
)
FETCH_METHOD_VALUES = (
    "manual",
    "rss",
    "api",
    "static_html",
    "browser",
    "newsletter",
    "filing",
    "social",
    "youtube",
)


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("rss_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="3", nullable=False),
        sa.Column("fetch_method", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column(
            "fetch_frequency_minutes",
            sa.Integer(),
            server_default="1440",
            nullable=False,
        ),
        sa.Column(
            "reliability_score",
            sa.Numeric(precision=3, scale=2),
            server_default="0.50",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="ck_sources_priority_range"),
        sa.CheckConstraint(
            "fetch_frequency_minutes > 0",
            name="ck_sources_fetch_frequency_positive",
        ),
        sa.CheckConstraint(
            "reliability_score >= 0 AND reliability_score <= 1",
            name="ck_sources_reliability_score_range",
        ),
        sa.CheckConstraint("failure_count >= 0", name="ck_sources_failure_count_non_negative"),
        sa.CheckConstraint(
            f"source_type IN ({_check_values(SOURCE_TYPE_VALUES)})",
            name="ck_sources_source_type",
        ),
        sa.CheckConstraint(
            f"fetch_method IN ({_check_values(FETCH_METHOD_VALUES)})",
            name="ck_sources_fetch_method",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_url_unique", "sources", ["url"], unique=True)
    op.create_index(
        "ix_sources_rss_url_unique",
        "sources",
        ["rss_url"],
        unique=True,
        postgresql_where=sa.text("rss_url IS NOT NULL"),
    )
    op.create_index("ix_sources_source_type", "sources", ["source_type"])
    op.create_index("ix_sources_category", "sources", ["category"])
    op.create_index("ix_sources_region", "sources", ["region"])
    op.create_index("ix_sources_is_active", "sources", ["is_active"])
    op.create_index("ix_sources_priority", "sources", ["priority"])
    op.create_index("ix_sources_fetch_method", "sources", ["fetch_method"])


def downgrade() -> None:
    op.drop_index("ix_sources_fetch_method", table_name="sources")
    op.drop_index("ix_sources_priority", table_name="sources")
    op.drop_index("ix_sources_is_active", table_name="sources")
    op.drop_index("ix_sources_region", table_name="sources")
    op.drop_index("ix_sources_category", table_name="sources")
    op.drop_index("ix_sources_source_type", table_name="sources")
    op.drop_index(
        "ix_sources_rss_url_unique",
        table_name="sources",
        postgresql_where=sa.text("rss_url IS NOT NULL"),
    )
    op.drop_index("ix_sources_url_unique", table_name="sources")
    op.drop_table("sources")
