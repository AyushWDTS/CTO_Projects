from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventArticleMatchType, EventStatus


class NewsEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    canonical_title: str | None = None
    canonical_url: str | None = None
    normalized_canonical_url: str | None = None
    primary_article_id: UUID | None = None
    primary_source_id: UUID | None = None
    event_key: str
    category: str | None = None
    region: str | None = None
    published_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    article_count: int
    source_count: int
    status: EventStatus
    confidence_score: Decimal
    metadata: dict | None = Field(
        default=None,
        validation_alias="event_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class NewsEventList(BaseModel):
    items: list[NewsEventRead]
    total: int
    limit: int
    offset: int


class EventArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    article_id: UUID
    source_id: UUID
    match_type: EventArticleMatchType
    similarity_score: Decimal
    confidence_score: Decimal
    is_primary: bool
    match_details: dict | None = None
    created_at: datetime


class EventArticleList(BaseModel):
    items: list[EventArticleRead]
    total: int
    limit: int
    offset: int
