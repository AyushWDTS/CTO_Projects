from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FetchLogStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"


def fetch_log_status_values() -> str:
    return ", ".join(f"'{status.value}'" for status in FetchLogStatus)


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (
        CheckConstraint(
            "raw_size_bytes IS NULL OR raw_size_bytes >= 0",
            name="ck_raw_documents_size",
        ),
        Index("ix_raw_documents_source_id", "source_id"),
        Index("ix_raw_documents_url", "url"),
        Index("ix_raw_documents_raw_hash", "raw_hash"),
        Index("ix_raw_documents_fetched_at", "fetched_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    source = relationship("Source")


class SourceFetchLog(Base):
    __tablename__ = "source_fetch_logs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({fetch_log_status_values()})",
            name="ck_source_fetch_logs_status",
        ),
        CheckConstraint(
            "items_found IS NULL OR items_found >= 0",
            name="ck_fetch_logs_items_found",
        ),
        CheckConstraint(
            "items_stored IS NULL OR items_stored >= 0",
            name="ck_fetch_logs_items_stored",
        ),
        Index("ix_source_fetch_logs_source_id", "source_id"),
        Index("ix_source_fetch_logs_status", "status"),
        Index("ix_source_fetch_logs_started_at", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[FetchLogStatus] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_stored: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    source = relationship("Source")
