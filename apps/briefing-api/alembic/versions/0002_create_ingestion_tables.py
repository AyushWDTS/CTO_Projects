"""create ingestion tables

Revision ID: 0002_create_ingestion_tables
Revises: 0001_create_sources_table
Create Date: 2026-05-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_create_ingestion_tables"
down_revision: str | None = "0001_create_sources_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FETCH_LOG_STATUSES = ("running", "success", "partial_success", "failed", "skipped")


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "raw_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_size_bytes", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "raw_size_bytes IS NULL OR raw_size_bytes >= 0",
            name="ck_raw_documents_size",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_documents_source_id", "raw_documents", ["source_id"])
    op.create_index("ix_raw_documents_url", "raw_documents", ["url"])
    op.create_index("ix_raw_documents_raw_hash", "raw_documents", ["raw_hash"])
    op.create_index("ix_raw_documents_fetched_at", "raw_documents", ["fetched_at"])

    op.create_table(
        "source_fetch_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("items_found", sa.Integer(), nullable=True),
        sa.Column("items_stored", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_check_values(FETCH_LOG_STATUSES)})",
            name="ck_source_fetch_logs_status",
        ),
        sa.CheckConstraint(
            "items_found IS NULL OR items_found >= 0",
            name="ck_fetch_logs_items_found",
        ),
        sa.CheckConstraint(
            "items_stored IS NULL OR items_stored >= 0",
            name="ck_fetch_logs_items_stored",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_fetch_logs_source_id", "source_fetch_logs", ["source_id"])
    op.create_index("ix_source_fetch_logs_status", "source_fetch_logs", ["status"])
    op.create_index("ix_source_fetch_logs_started_at", "source_fetch_logs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_source_fetch_logs_started_at", table_name="source_fetch_logs")
    op.drop_index("ix_source_fetch_logs_status", table_name="source_fetch_logs")
    op.drop_index("ix_source_fetch_logs_source_id", table_name="source_fetch_logs")
    op.drop_table("source_fetch_logs")

    op.drop_index("ix_raw_documents_fetched_at", table_name="raw_documents")
    op.drop_index("ix_raw_documents_raw_hash", table_name="raw_documents")
    op.drop_index("ix_raw_documents_url", table_name="raw_documents")
    op.drop_index("ix_raw_documents_source_id", table_name="raw_documents")
    op.drop_table("raw_documents")
