"""create articles table

Revision ID: 0003_create_articles_table
Revises: 0002_create_ingestion_tables
Create Date: 2026-05-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_create_articles_table"
down_revision: str | None = "0002_create_ingestion_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ARTICLE_STATUSES = ("success", "failed", "skipped", "exact_duplicate")


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("clean_text", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("extraction_status", sa.String(length=50), nullable=False),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("duplicate_of_article_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            f"extraction_status IN ({_check_values(ARTICLE_STATUSES)})",
            name="ck_articles_extraction_status",
        ),
        sa.ForeignKeyConstraint(["duplicate_of_article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["raw_document_id"], ["raw_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_articles_raw_document_id_unique",
        "articles",
        ["raw_document_id"],
        unique=True,
    )
    op.create_index("ix_articles_source_id", "articles", ["source_id"])
    op.create_index("ix_articles_canonical_url", "articles", ["canonical_url"])
    op.create_index("ix_articles_content_hash", "articles", ["content_hash"])
    op.create_index("ix_articles_extraction_status", "articles", ["extraction_status"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_source_id_published_at", "articles", ["source_id", "published_at"])
    op.create_index(
        "ix_articles_canonical_url_content_hash",
        "articles",
        ["canonical_url", "content_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_articles_canonical_url_content_hash", table_name="articles")
    op.drop_index("ix_articles_source_id_published_at", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_index("ix_articles_extraction_status", table_name="articles")
    op.drop_index("ix_articles_content_hash", table_name="articles")
    op.drop_index("ix_articles_canonical_url", table_name="articles")
    op.drop_index("ix_articles_source_id", table_name="articles")
    op.drop_index("ix_articles_raw_document_id_unique", table_name="articles")
    op.drop_table("articles")
