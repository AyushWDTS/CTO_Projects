from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.digest import DigestSection, DigestStatus


class DigestItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    digest_id: UUID
    event_id: UUID
    event_ai_analysis_id: UUID | None = None
    rank: int
    section: DigestSection
    final_score: Decimal
    relevance_score: Decimal | None = None
    urgency_score: Decimal | None = None
    source_authority_score: Decimal | None = None
    recency_score: Decimal | None = None
    business_impact_score: Decimal | None = None
    importance_tier: str | None = None
    headline: str | None = None
    summary: str | None = None
    why_it_matters: str | None = None
    suggested_action: str | None = None
    source_urls: list | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="item_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime


class DigestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    digest_date: date
    window_start: datetime
    window_end: datetime
    title: str
    status: DigestStatus
    total_candidates: int
    total_selected: int
    critical_count: int
    important_count: int
    monitor_count: int
    metadata: dict | None = Field(
        default=None,
        validation_alias="digest_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class DigestDetailRead(DigestRead):
    items: list[DigestItemRead] = Field(default_factory=list)


class DigestList(BaseModel):
    items: list[DigestRead]
    total: int
    limit: int
    offset: int


class DigestItemList(BaseModel):
    items: list[DigestItemRead]
    total: int
    limit: int
    offset: int


class DigestPreviewItem(BaseModel):
    event_id: UUID
    event_ai_analysis_id: UUID
    rank: int
    section: DigestSection
    final_score: Decimal
    relevance_score: Decimal | None = None
    urgency_score: Decimal | None = None
    source_authority_score: Decimal | None = None
    recency_score: Decimal | None = None
    business_impact_score: Decimal | None = None
    importance_tier: str | None = None
    headline: str | None = None
    summary: str | None = None
    why_it_matters: str | None = None
    suggested_action: str | None = None
    source_urls: list | None = None
    metadata: dict | None = None


class DigestPreview(BaseModel):
    digest_date: date
    window_start: datetime
    window_end: datetime
    title: str
    total_candidates: int
    total_selected: int
    critical_count: int
    important_count: int
    monitor_count: int
    metadata: dict
    items: list[DigestPreviewItem] = Field(default_factory=list)
