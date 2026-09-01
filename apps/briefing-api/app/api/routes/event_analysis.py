from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event_analysis import EventAIAnalysisStatus, ImportanceTier
from app.schemas.event_analysis import (
    EventAIAnalysisBatchResult,
    EventAIAnalysisList,
    EventAIAnalysisRead,
)
from app.services.event_analysis_service import (
    EventAIAnalysisNotFoundError,
    NewsEventNotFoundError,
    analyze_event,
    analyze_pending_events,
    get_event_ai_analysis,
    list_event_ai_analyses,
    reprocess_failed_ai_analyses,
)

router = APIRouter(prefix="/api/v1/event-analysis", tags=["event-analysis"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/events/{event_id}/run", response_model=EventAIAnalysisRead)
def analyze_event_endpoint(
    event_id: UUID,
    db: SessionDependency,
    force: bool = False,
) -> EventAIAnalysisRead:
    try:
        return analyze_event(db, event_id, force=force)
    except NewsEventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/run", response_model=EventAIAnalysisBatchResult)
def analyze_pending_events_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> EventAIAnalysisBatchResult:
    return analyze_pending_events(db, limit=limit)


@router.post("/reprocess-failed", response_model=EventAIAnalysisBatchResult)
def reprocess_failed_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> EventAIAnalysisBatchResult:
    return reprocess_failed_ai_analyses(db, limit=limit)


@router.get("", response_model=EventAIAnalysisList)
def list_event_ai_analyses_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: EventAIAnalysisStatus | None = None,
    importance_tier: ImportanceTier | None = None,
    min_relevance_score: Annotated[float | None, Query(ge=0, le=1)] = None,
    min_urgency_score: Annotated[float | None, Query(ge=0, le=1)] = None,
    source_id: UUID | None = None,
    category: str | None = None,
    region: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> EventAIAnalysisList:
    analyses, total = list_event_ai_analyses(
        db,
        limit=limit,
        offset=offset,
        status=status,
        importance_tier=importance_tier.value if importance_tier else None,
        min_relevance_score=min_relevance_score,
        min_urgency_score=min_urgency_score,
        source_id=source_id,
        category=category,
        region=region,
        created_from=created_from,
        created_to=created_to,
    )
    return EventAIAnalysisList(items=analyses, total=total, limit=limit, offset=offset)


@router.get("/events/{event_id}", response_model=EventAIAnalysisRead)
def get_event_ai_analysis_endpoint(event_id: UUID, db: SessionDependency) -> EventAIAnalysisRead:
    try:
        return get_event_ai_analysis(db, event_id)
    except EventAIAnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
