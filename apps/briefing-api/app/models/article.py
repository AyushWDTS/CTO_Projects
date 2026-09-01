from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ArticleExtractionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    EXACT_DUPLICATE = "exact_duplicate"


def article_extraction_status_values() -> str:
    return ", ".join(f"'{status.value}'" for status in ArticleExtractionStatus)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint(
            f"extraction_status IN ({article_extraction_status_values()})",
            name="ck_articles_extraction_status",
        ),
        Index("ix_articles_raw_document_id_unique", "raw_document_id", unique=True),
        Index("ix_articles_source_id", "source_id"),
        Index("ix_articles_canonical_url", "canonical_url"),
        Index("ix_articles_content_hash", "content_hash"),
        Index("ix_articles_extraction_status", "extraction_status"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_source_id_published_at", "source_id", "published_at"),
        Index("ix_articles_canonical_url_content_hash", "canonical_url", "content_hash"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    raw_document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("raw_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    clean_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_status: Mapped[ArticleExtractionStatus] = mapped_column(String(50), nullable=False)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of_article_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id"),
        nullable=True,
    )
    article_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    raw_document = relationship("RawDocument")
    source = relationship("Source")
    duplicate_of_article = relationship("Article", remote_side=[id])
