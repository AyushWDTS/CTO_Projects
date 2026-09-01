from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.digest import DigestSection, DigestStatus
from app.models.event_analysis import ImportanceTier
from app.schemas.digest import (
    DigestDetailRead,
    DigestItemList,
    DigestList,
    DigestPreview,
)
from app.services.digest_service import (
    DigestNotFoundError,
    InvalidDigestWindowError,
    build_digest,
    get_digest,
    list_digest_items,
    list_digests,
    preview_digest,
    refresh_digest,
)

router = APIRouter(prefix="/api/v1/digests", tags=["digests"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/build", response_model=DigestDetailRead)
def build_digest_endpoint(
    db: SessionDependency,
    digest_date: date | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 15,
    category: str | None = None,
    region: str | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=1)] = None,
    include_low: bool = False,
    refresh: bool = False,
) -> DigestDetailRead:
    try:
        return build_digest(
            db,
            digest_date=digest_date,
            window_start=window_start,
            window_end=window_end,
            limit=limit,
            category=category,
            region=region,
            min_score=min_score,
            include_low=include_low,
            refresh=refresh,
        )
    except InvalidDigestWindowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/preview", response_model=DigestPreview)
def preview_digest_endpoint(
    db: SessionDependency,
    digest_date: date | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 15,
    category: str | None = None,
    region: str | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=1)] = None,
    include_low: bool = False,
) -> DigestPreview:
    try:
        return preview_digest(
            db,
            digest_date=digest_date,
            window_start=window_start,
            window_end=window_end,
            limit=limit,
            category=category,
            region=region,
            min_score=min_score,
            include_low=include_low,
        )
    except InvalidDigestWindowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=DigestList)
def list_digests_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: DigestStatus | None = None,
    digest_date: date | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> DigestList:
    rows, total = list_digests(
        db,
        limit=limit,
        offset=offset,
        status=status,
        digest_date=digest_date,
        created_from=created_from,
        created_to=created_to,
    )
    return DigestList(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{digest_id}", response_model=DigestDetailRead)
def get_digest_endpoint(digest_id: UUID, db: SessionDependency) -> DigestDetailRead:
    try:
        return get_digest(db, digest_id)
    except DigestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{digest_id}/items", response_model=DigestItemList)
def list_digest_items_endpoint(
    digest_id: UUID,
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    section: DigestSection | None = None,
    importance_tier: ImportanceTier | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=1)] = None,
) -> DigestItemList:
    try:
        rows, total = list_digest_items(
            db,
            digest_id,
            limit=limit,
            offset=offset,
            section=section.value if section else None,
            importance_tier=importance_tier,
            min_score=min_score,
        )
        return DigestItemList(items=rows, total=total, limit=limit, offset=offset)
    except DigestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{digest_id}/refresh", response_model=DigestDetailRead)
def refresh_digest_endpoint(digest_id: UUID, db: SessionDependency) -> DigestDetailRead:
    try:
        return refresh_digest(db, digest_id)
    except DigestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
