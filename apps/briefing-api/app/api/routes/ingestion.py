from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ingestion import FetchLogStatus
from app.schemas.ingestion import (
    IngestionBatchResult,
    IngestionRunResult,
    RawDocumentList,
    SourceFetchLogList,
)
from app.services.ingestion_service import (
    ingest_all_sources,
    ingest_source,
    list_fetch_logs,
    list_raw_documents,
)
from app.services.source_service import SourceNotFoundError

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/sources/{source_id}/run", response_model=IngestionRunResult)
def run_source_ingestion_endpoint(source_id: UUID, db: SessionDependency) -> IngestionRunResult:
    try:
        return ingest_source(db, source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/run", response_model=IngestionBatchResult)
def run_all_ingestion_endpoint(db: SessionDependency) -> IngestionBatchResult:
    return ingest_all_sources(db)


@router.get("/logs", response_model=SourceFetchLogList)
def list_fetch_logs_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_id: UUID | None = None,
    status: FetchLogStatus | None = None,
) -> SourceFetchLogList:
    logs, total = list_fetch_logs(
        db,
        limit=limit,
        offset=offset,
        source_id=source_id,
        status=status,
    )
    return SourceFetchLogList(items=logs, total=total, limit=limit, offset=offset)


@router.get("/raw-documents", response_model=RawDocumentList)
def list_raw_documents_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_id: UUID | None = None,
) -> RawDocumentList:
    documents, total = list_raw_documents(db, limit=limit, offset=offset, source_id=source_id)
    return RawDocumentList(items=documents, total=total, limit=limit, offset=offset)
