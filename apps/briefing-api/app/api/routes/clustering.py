from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.clustering import ArticleClusteringResult, ClusteringBatchResult
from app.services.clustering_service import (
    ArticleNotFoundError,
    cluster_article,
    cluster_by_source,
    cluster_pending_articles,
)

router = APIRouter(prefix="/api/v1/clustering", tags=["clustering"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/run", response_model=ClusteringBatchResult)
def cluster_pending_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    reprocess: bool = False,
) -> ClusteringBatchResult:
    return cluster_pending_articles(db, limit=limit, reprocess=reprocess)


@router.post("/articles/{article_id}/run", response_model=ArticleClusteringResult)
def cluster_article_endpoint(
    article_id: UUID,
    db: SessionDependency,
    reprocess: bool = False,
) -> ArticleClusteringResult:
    try:
        return cluster_article(db, article_id, reprocess=reprocess)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/sources/{source_id}/run", response_model=ClusteringBatchResult)
def cluster_source_endpoint(
    source_id: UUID,
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    reprocess: bool = False,
) -> ClusteringBatchResult:
    return cluster_by_source(db, source_id, limit=limit, reprocess=reprocess)
