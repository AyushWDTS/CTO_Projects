from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.article import ArticleExtractionStatus


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    raw_document_id: UUID
    source_id: UUID
    title: str | None = None
    canonical_url: str | None = None
    source_url: str
    content_type: str | None = None
    clean_text: str | None = None
    excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    content_hash: str | None = None
    extraction_status: ArticleExtractionStatus
    extraction_error: str | None = None
    duplicate_of_article_id: UUID | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="article_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class ArticleList(BaseModel):
    items: list[ArticleRead]
    total: int
    limit: int
    offset: int
