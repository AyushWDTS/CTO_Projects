from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EventAIAnalysisStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ImportanceTier(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    MONITOR = "monitor"
    LOW = "low"


class AnalysisSentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNKNOWN = "unknown"


def enum_check_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{value.value}'" for value in enum_type)


class EventAIAnalysis(Base):
    __tablename__ = "event_ai_analyses"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(EventAIAnalysisStatus)})",
            name="ck_event_ai_analyses_status",
        ),
        CheckConstraint(
            f"importance_tier IS NULL OR importance_tier IN ({enum_check_values(ImportanceTier)})",
            name="ck_event_ai_analyses_importance_tier",
        ),
        CheckConstraint(
            f"sentiment IS NULL OR sentiment IN ({enum_check_values(AnalysisSentiment)})",
            name="ck_event_ai_analyses_sentiment",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_event_ai_analyses_relevance_score_range",
        ),
        CheckConstraint(
            "urgency_score IS NULL OR (urgency_score >= 0 AND urgency_score <= 1)",
            name="ck_event_ai_analyses_urgency_score_range",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_event_ai_analyses_confidence_score_range",
        ),
        CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
            name="ck_event_ai_analyses_prompt_tokens_non_negative",
        ),
        CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_event_ai_analyses_completion_tokens_non_negative",
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_event_ai_analyses_total_tokens_non_negative",
        ),
        CheckConstraint(
            "context_article_count >= 0",
            name="ck_event_ai_analyses_context_article_count_non_negative",
        ),
        Index("ix_event_ai_analyses_event_id_unique", "event_id", unique=True),
        Index("ix_event_ai_analyses_status", "status"),
        Index("ix_event_ai_analyses_importance_tier", "importance_tier"),
        Index("ix_event_ai_analyses_relevance_score", "relevance_score"),
        Index("ix_event_ai_analyses_urgency_score", "urgency_score"),
        Index("ix_event_ai_analyses_created_at", "created_at"),
        Index("ix_event_ai_analyses_updated_at", "updated_at"),
        Index("ix_event_ai_analyses_primary_article_id", "primary_article_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    entities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    urgency_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    importance_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_business_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="phase5_v1",
        server_default="phase5_v1",
    )
    prompt_tokens: Mapped[int | None] = mapped_column(nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=EventAIAnalysisStatus.PENDING.value,
        server_default=EventAIAnalysisStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_article_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_urls: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    primary_article_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_article_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    analysis_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
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

    event = relationship("NewsEvent")
    primary_article = relationship("Article")
