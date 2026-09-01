from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.normalization import NormalizationBatchResult, NormalizationRunResult
from app.services.normalization_service import (
    RawDocumentNotFoundError,
    normalize_by_source,
    normalize_pending_raw_documents,
    normalize_raw_document,
    reprocess_failed_normalizations,
)

router = APIRouter(prefix="/api/v1/normalization", tags=["normalization"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/raw-documents/{raw_document_id}/run", response_model=NormalizationRunResult)
def normalize_raw_document_endpoint(
    raw_document_id: UUID,
    db: SessionDependency,
) -> NormalizationRunResult:
    try:
        return normalize_raw_document(db, raw_document_id)
    except RawDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/run", response_model=NormalizationBatchResult)
def normalize_pending_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> NormalizationBatchResult:
    return normalize_pending_raw_documents(db, limit=limit)


@router.post("/sources/{source_id}/run", response_model=NormalizationBatchResult)
def normalize_source_endpoint(
    source_id: UUID,
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> NormalizationBatchResult:
    return normalize_by_source(db, source_id, limit=limit)


@router.post("/reprocess-failed", response_model=NormalizationBatchResult)
def reprocess_failed_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> NormalizationBatchResult:
    return reprocess_failed_normalizations(db, limit=limit)
