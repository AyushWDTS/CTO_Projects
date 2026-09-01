from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.ingestion import FetchLogStatus


class RawDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    url: str
    canonical_url: str | None = None
    content_type: str | None = None
    raw_content: str | None = None
    raw_hash: str
    raw_size_bytes: int | None = None
    http_status: int | None = None
    fetched_at: datetime
    metadata: dict | None = Field(
        default=None,
        validation_alias="document_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime


class RawDocumentList(BaseModel):
    items: list[RawDocumentRead]
    total: int
    limit: int
    offset: int


class SourceFetchLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    status: FetchLogStatus
    started_at: datetime
    finished_at: datetime | None = None
    http_status: int | None = None
    error_message: str | None = None
    items_found: int | None = None
    items_stored: int | None = None
    created_at: datetime


class SourceFetchLogList(BaseModel):
    items: list[SourceFetchLogRead]
    total: int
    limit: int
    offset: int


class IngestionRunResult(BaseModel):
    source_id: UUID
    status: FetchLogStatus
    reason: str | None = None
    items_found: int = 0
    items_stored: int = 0
    raw_document_ids: list[UUID] = Field(default_factory=list)
    fetch_log_id: UUID | None = None
    http_status: int | None = None
    error_message: str | None = None


class IngestionBatchResult(BaseModel):
    total_sources: int
    results: list[IngestionRunResult]
