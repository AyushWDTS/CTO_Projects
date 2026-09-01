from uuid import UUID

from pydantic import BaseModel, Field

from app.models.event import EventArticleMatchType, EventStatus


class ArticleClusteringResult(BaseModel):
    article_id: UUID
    source_id: UUID | None = None
    status: str
    event_id: UUID | None = None
    event_status: EventStatus | None = None
    match_type: EventArticleMatchType | None = None
    similarity_score: float | None = None
    confidence_score: float | None = None
    reason: str | None = None
    created_event: bool = False
    updated_event: bool = False


class ClusteringBatchResult(BaseModel):
    total_articles: int
    created_events: int = 0
    updated_events: int = 0
    linked_articles: int = 0
    skipped_articles: int = 0
    results: list[ArticleClusteringResult] = Field(default_factory=list)
