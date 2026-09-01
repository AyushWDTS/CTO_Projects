from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceType(StrEnum):
    RSS = "rss"
    NEWS_SITE = "news_site"
    REGULATOR = "regulator"
    GOVERNMENT = "government"
    COMPANY_IR = "company_ir"
    PRESS_RELEASE = "press_release"
    BLOG = "blog"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    YOUTUBE = "youtube"
    FILING = "filing"
    OTHER = "other"


class FetchMethod(StrEnum):
    MANUAL = "manual"
    RSS = "rss"
    API = "api"
    STATIC_HTML = "static_html"
    BROWSER = "browser"
    NEWSLETTER = "newsletter"
    FILING = "filing"
    SOCIAL = "social"
    YOUTUBE = "youtube"


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


def enum_check_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{value}'" for value in enum_values(enum_type))


source_type_enum = SQLAlchemyEnum(
    SourceType,
    native_enum=False,
    length=50,
    validate_strings=True,
    values_callable=enum_values,
)
fetch_method_enum = SQLAlchemyEnum(
    FetchMethod,
    native_enum=False,
    length=50,
    validate_strings=True,
    values_callable=enum_values,
)


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 5", name="ck_sources_priority_range"),
        CheckConstraint(
            "fetch_frequency_minutes > 0",
            name="ck_sources_fetch_frequency_positive",
        ),
        CheckConstraint(
            "reliability_score >= 0 AND reliability_score <= 1",
            name="ck_sources_reliability_score_range",
        ),
        CheckConstraint("failure_count >= 0", name="ck_sources_failure_count_non_negative"),
        CheckConstraint(
            f"source_type IN ({enum_check_values(SourceType)})",
            name="ck_sources_source_type",
        ),
        CheckConstraint(
            f"fetch_method IN ({enum_check_values(FetchMethod)})",
            name="ck_sources_fetch_method",
        ),
        Index("ix_sources_url_unique", "url", unique=True),
        Index(
            "ix_sources_rss_url_unique",
            "rss_url",
            unique=True,
            postgresql_where=text("rss_url IS NOT NULL"),
        ),
        Index("ix_sources_source_type", "source_type"),
        Index("ix_sources_category", "category"),
        Index("ix_sources_region", "region"),
        Index("ix_sources_is_active", "is_active"),
        Index("ix_sources_priority", "priority"),
        Index("ix_sources_fetch_method", "fetch_method"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    rss_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(source_type_enum, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    fetch_method: Mapped[FetchMethod] = mapped_column(
        fetch_method_enum,
        nullable=False,
        default=FetchMethod.MANUAL,
        server_default=FetchMethod.MANUAL.value,
    )
    fetch_frequency_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1440,
        server_default="1440",
    )
    reliability_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("0.50"),
        server_default="0.50",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
