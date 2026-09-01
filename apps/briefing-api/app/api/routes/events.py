from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import EventStatus
from app.schemas.event import EventArticleList, NewsEventList, NewsEventRead
from app.services.clustering_service import (
    NewsEventNotFoundError,
    get_event,
    list_event_articles,
    list_events,
)

router = APIRouter(prefix="/api/v1/events", tags=["events"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.get("", response_model=NewsEventList)
def list_events_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    category: str | None = None,
    region: str | None = None,
    status: EventStatus | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    source_id: UUID | None = None,
    min_confidence: Annotated[float | None, Query(ge=0, le=1)] = None,
) -> NewsEventList:
    events, total = list_events(
        db,
        limit=limit,
        offset=offset,
        category=category,
        region=region,
        status=status,
        published_from=published_from,
        published_to=published_to,
        source_id=source_id,
        min_confidence=min_confidence,
    )
    return NewsEventList(items=events, total=total, limit=limit, offset=offset)


@router.get("/{event_id}", response_model=NewsEventRead)
def get_event_endpoint(event_id: UUID, db: SessionDependency) -> NewsEventRead:
    try:
        return get_event(db, event_id)
    except NewsEventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{event_id}/articles", response_model=EventArticleList)
def list_event_articles_endpoint(
    event_id: UUID,
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventArticleList:
    try:
        rows, total = list_event_articles(db, event_id, limit=limit, offset=offset)
    except NewsEventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EventArticleList(items=rows, total=total, limit=limit, offset=offset)
