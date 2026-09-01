from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.source import FetchMethod, SourceType


class SourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    rss_url: str | None = Field(default=None, min_length=1)
    source_type: SourceType
    category: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    priority: int = Field(default=3, ge=1, le=5)
    fetch_method: FetchMethod = FetchMethod.MANUAL
    fetch_frequency_minutes: int = Field(default=1440, gt=0)
    reliability_score: float = Field(default=0.5, ge=0, le=1)
    is_active: bool = True
    notes: str | None = None


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1)
    rss_url: str | None = Field(default=None, min_length=1)
    source_type: SourceType | None = None
    category: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    priority: int | None = Field(default=None, ge=1, le=5)
    fetch_method: FetchMethod | None = None
    fetch_frequency_minutes: int | None = Field(default=None, gt=0)
    reliability_score: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None
    last_fetched_at: datetime | None = None
    last_success_at: datetime | None = None
    failure_count: int | None = Field(default=None, ge=0)
    notes: str | None = None


class SourceRead(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    last_fetched_at: datetime | None = None
    last_success_at: datetime | None = None
    failure_count: int
    created_at: datetime
    updated_at: datetime


class SourceList(BaseModel):
    items: list[SourceRead]
    total: int
    limit: int
    offset: int
