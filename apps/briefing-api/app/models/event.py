from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EventStatus(StrEnum):
    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"
    ARCHIVED = "archived"


class EventArticleMatchType(StrEnum):
    EXACT_URL = "exact_url"
    EXACT_SOURCE_URL = "exact_source_url"
    EXACT_HASH = "exact_hash"
    TITLE_SIMILARITY = "title_similarity"
    TEXT_SIMILARITY = "text_similarity"
    MANUAL = "manual"


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


def enum_check_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{value}'" for value in enum_values(enum_type))


event_status_enum = SQLAlchemyEnum(
    EventStatus,
    native_enum=False,
    length=50,
    validate_strings=True,
    values_callable=enum_values,
)
event_article_match_type_enum = SQLAlchemyEnum(
    EventArticleMatchType,
    native_enum=False,
    length=50,
    validate_strings=True,
    values_callable=enum_values,
)


class NewsEvent(Base):
    __tablename__ = "news_events"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(EventStatus)})",
            name="ck_news_events_status",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_news_events_confidence_score_range",
        ),
        CheckConstraint("article_count >= 0", name="ck_news_events_article_count_non_negative"),
        CheckConstraint("source_count >= 0", name="ck_news_events_source_count_non_negative"),
        Index("ix_news_events_event_key_unique", "event_key", unique=True),
        Index("ix_news_events_status", "status"),
        Index("ix_news_events_category", "category"),
        Index("ix_news_events_region", "region"),
        Index("ix_news_events_published_at", "published_at"),
        Index("ix_news_events_first_seen_at", "first_seen_at"),
        Index("ix_news_events_last_seen_at", "last_seen_at"),
        Index("ix_news_events_primary_source_id", "primary_source_id"),
        Index("ix_news_events_normalized_canonical_url", "normalized_canonical_url"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_article_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    primary_source_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    article_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    source_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    status: Mapped[EventStatus] = mapped_column(
        event_status_enum,
        nullable=False,
        default=EventStatus.ACTIVE,
        server_default=EventStatus.ACTIVE.value,
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default="0.000",
    )
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
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

    primary_article = relationship("Article", foreign_keys=[primary_article_id])
    primary_source = relationship("Source", foreign_keys=[primary_source_id])
    event_articles = relationship(
        "EventArticle",
        back_populates="event",
        cascade="all, delete-orphan",
        foreign_keys="EventArticle.event_id",
    )


class EventArticle(Base):
    __tablename__ = "event_articles"
    __table_args__ = (
        CheckConstraint(
            f"match_type IN ({enum_check_values(EventArticleMatchType)})",
            name="ck_event_articles_match_type",
        ),
        CheckConstraint(
            "similarity_score >= 0 AND similarity_score <= 1",
            name="ck_event_articles_similarity_score_range",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_event_articles_confidence_score_range",
        ),
        Index("ix_event_articles_article_id_unique", "article_id", unique=True),
        Index(
            "ix_event_articles_one_primary_per_event",
            "event_id",
            unique=True,
            postgresql_where=text("is_primary IS TRUE"),
        ),
        Index("ix_event_articles_event_id", "event_id"),
        Index("ix_event_articles_article_id", "article_id"),
        Index("ix_event_articles_source_id", "source_id"),
        Index("ix_event_articles_match_type", "match_type"),
        Index("ix_event_articles_is_primary", "is_primary"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    article_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id"),
        nullable=False,
    )
    match_type: Mapped[EventArticleMatchType] = mapped_column(
        event_article_match_type_enum,
        nullable=False,
    )
    similarity_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default="0.000",
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default="0.000",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    match_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    event = relationship("NewsEvent", back_populates="event_articles", foreign_keys=[event_id])
    article = relationship("Article")
    source = relationship("Source")
