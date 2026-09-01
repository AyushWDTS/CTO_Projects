from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BriefingBookmarkCreate(BaseModel):
    user_key: str = Field(default="default", max_length=100)
    event_id: UUID
    digest_id: UUID | None = None
    digest_item_id: UUID | None = None
    digest_date: str | None = None
    section: str | None = None
    headline: str = Field(min_length=1, max_length=500)
    summary: str | None = None
    why_it_matters: str | None = None
    suggested_action: str | None = None
    source_url: str | None = None
    importance_tier: str | None = None
    note: str | None = None
    metadata: dict | None = None


class BriefingBookmarkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    user_key: str
    event_id: UUID
    digest_id: UUID | None = None
    digest_item_id: UUID | None = None
    digest_date: str | None = None
    section: str | None = None
    headline: str
    summary: str | None = None
    why_it_matters: str | None = None
    suggested_action: str | None = None
    source_url: str | None = None
    importance_tier: str | None = None
    note: str | None = None
    metadata: dict | None = Field(default=None, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class BriefingBookmarkList(BaseModel):
    items: list[BriefingBookmarkRead]
    total: int
    limit: int
    offset: int
