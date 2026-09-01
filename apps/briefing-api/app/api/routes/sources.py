from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.source import FetchMethod, SourceType
from app.schemas.source import SourceCreate, SourceList, SourceRead, SourceUpdate
from app.services.source_service import (
    DuplicateSourceError,
    SourceNotFoundError,
    activate_source,
    create_source,
    deactivate_source,
    get_source,
    list_sources,
    update_source,
)

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source_endpoint(source_create: SourceCreate, db: SessionDependency) -> SourceRead:
    try:
        return create_source(db, source_create)
    except DuplicateSourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=SourceList)
def list_sources_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_type: SourceType | None = None,
    category: str | None = None,
    region: str | None = None,
    is_active: bool | None = None,
    priority: Annotated[int | None, Query(ge=1, le=5)] = None,
    fetch_method: FetchMethod | None = None,
) -> SourceList:
    sources, total = list_sources(
        db,
        limit=limit,
        offset=offset,
        source_type=source_type,
        category=category,
        region=region,
        is_active=is_active,
        priority=priority,
        fetch_method=fetch_method,
    )
    return SourceList(items=sources, total=total, limit=limit, offset=offset)


@router.get("/{source_id}", response_model=SourceRead)
def get_source_endpoint(source_id: UUID, db: SessionDependency) -> SourceRead:
    try:
        return get_source(db, source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{source_id}", response_model=SourceRead)
def update_source_endpoint(
    source_id: UUID,
    source_update: SourceUpdate,
    db: SessionDependency,
) -> SourceRead:
    try:
        return update_source(db, source_id, source_update)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateSourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{source_id}", response_model=SourceRead)
def delete_source_endpoint(source_id: UUID, db: SessionDependency) -> SourceRead:
    try:
        return deactivate_source(db, source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{source_id}/activate", response_model=SourceRead)
def activate_source_endpoint(source_id: UUID, db: SessionDependency) -> SourceRead:
    try:
        return activate_source(db, source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{source_id}/deactivate", response_model=SourceRead)
def deactivate_source_endpoint(source_id: UUID, db: SessionDependency) -> SourceRead:
    try:
        return deactivate_source(db, source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
