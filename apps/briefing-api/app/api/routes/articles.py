from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.article import ArticleExtractionStatus
from app.schemas.article import ArticleList, ArticleRead
from app.services.normalization_service import (
    ArticleNotFoundError,
    get_article,
    list_articles,
)

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ArticleList)
def list_articles_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_id: UUID | None = None,
    status: ArticleExtractionStatus | None = None,
    category: str | None = None,
    region: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    content_type: str | None = None,
) -> ArticleList:
    articles, total = list_articles(
        db,
        limit=limit,
        offset=offset,
        source_id=source_id,
        status=status,
        category=category,
        region=region,
        published_from=published_from,
        published_to=published_to,
        content_type=content_type,
    )
    return ArticleList(items=articles, total=total, limit=limit, offset=offset)


@router.get("/{article_id}", response_model=ArticleRead)
def get_article_endpoint(article_id: UUID, db: SessionDependency) -> ArticleRead:
    try:
        return get_article(db, article_id)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
