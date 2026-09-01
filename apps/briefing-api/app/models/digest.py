from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DigestStatus(StrEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class DigestSection(StrEnum):
    CRITICAL_ALERTS = "Critical Alerts"
    GAMING_AND_CASINO_MARKET = "Gaming and Casino Market"
    REGULATORY_AND_COMPLIANCE = "Regulatory and Compliance"
    TECHNOLOGY_AND_OPERATIONS = "Technology and Operations"
    MARKET_COMPETITOR_INTELLIGENCE = "Market/Competitor Intelligence"
    MONITOR_LIST = "Monitor List"


def enum_check_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{value.value}'" for value in enum_type)


class Digest(Base):
    __tablename__ = "digests"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(DigestStatus)})",
            name="ck_digests_status",
        ),
        CheckConstraint("total_candidates >= 0", name="ck_digests_total_candidates_non_negative"),
        CheckConstraint("total_selected >= 0", name="ck_digests_total_selected_non_negative"),
        CheckConstraint("critical_count >= 0", name="ck_digests_critical_count_non_negative"),
        CheckConstraint("important_count >= 0", name="ck_digests_important_count_non_negative"),
        CheckConstraint("monitor_count >= 0", name="ck_digests_monitor_count_non_negative"),
        CheckConstraint("window_start < window_end", name="ck_digests_valid_window"),
        Index(
            "ix_digests_window_unique",
            "digest_date",
            "window_start",
            "window_end",
            unique=True,
        ),
        Index("ix_digests_digest_date", "digest_date"),
        Index("ix_digests_status", "status"),
        Index("ix_digests_window_start", "window_start"),
        Index("ix_digests_window_end", "window_end"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DigestStatus.DRAFT.value,
        server_default=DigestStatus.DRAFT.value,
    )
    total_candidates: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total_selected: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    critical_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    important_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    monitor_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    digest_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
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

    items = relationship(
        "DigestItem",
        back_populates="digest",
        cascade="all, delete-orphan",
        order_by="DigestItem.rank",
    )


class DigestItem(Base):
    __tablename__ = "digest_items"
    __table_args__ = (
        CheckConstraint(
            f"section IN ({enum_check_values(DigestSection)})",
            name="ck_digest_items_section",
        ),
        CheckConstraint("rank > 0", name="ck_digest_items_rank_positive"),
        CheckConstraint(
            "final_score >= 0 AND final_score <= 1",
            name="ck_digest_items_final_score_range",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_digest_items_relevance_score_range",
        ),
        CheckConstraint(
            "urgency_score IS NULL OR (urgency_score >= 0 AND urgency_score <= 1)",
            name="ck_digest_items_urgency_score_range",
        ),
        CheckConstraint(
            "source_authority_score IS NULL OR "
            "(source_authority_score >= 0 AND source_authority_score <= 1)",
            name="ck_digest_items_source_authority_score_range",
        ),
        CheckConstraint(
            "recency_score IS NULL OR (recency_score >= 0 AND recency_score <= 1)",
            name="ck_digest_items_recency_score_range",
        ),
        CheckConstraint(
            "business_impact_score IS NULL OR "
            "(business_impact_score >= 0 AND business_impact_score <= 1)",
            name="ck_digest_items_business_impact_score_range",
        ),
        Index("ix_digest_items_digest_event_unique", "digest_id", "event_id", unique=True),
        Index("ix_digest_items_digest_rank_unique", "digest_id", "rank", unique=True),
        Index("ix_digest_items_digest_id", "digest_id"),
        Index("ix_digest_items_event_id", "event_id"),
        Index("ix_digest_items_section", "section"),
        Index("ix_digest_items_rank", "rank"),
        Index("ix_digest_items_final_score", "final_score"),
        Index("ix_digest_items_importance_tier", "importance_tier"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    digest_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("digests.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_ai_analysis_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("event_ai_analyses.id", ondelete="SET NULL"),
        nullable=True,
    )
    rank: Mapped[int] = mapped_column(nullable=False)
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    final_score: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False)
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    urgency_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    source_authority_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    recency_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    business_impact_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    importance_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_urls: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    item_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    digest = relationship("Digest", back_populates="items")
    event = relationship("NewsEvent")
    event_ai_analysis = relationship("EventAIAnalysis")
