from uuid import UUID

from pydantic import BaseModel, Field

from app.models.article import ArticleExtractionStatus


class NormalizationRunResult(BaseModel):
    raw_document_id: UUID
    source_id: UUID
    status: ArticleExtractionStatus
    article_id: UUID | None = None
    reason: str | None = None
    duplicate_of_article_id: UUID | None = None


class NormalizationBatchResult(BaseModel):
    total_raw_documents: int
    results: list[NormalizationRunResult] = Field(default_factory=list)
