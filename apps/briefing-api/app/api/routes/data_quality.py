from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.data_quality import (
    DataQualityScopeType,
    DataQualitySeverity,
    SourceHealthStatus,
)
from app.schemas.data_quality import (
    DataQualityFindingList,
    DataQualityRunResult,
    DataQualitySummary,
    SourceHealthCheckList,
    SourceHealthRunResult,
)
from app.services.data_quality_service import (
    get_data_quality_summary,
    list_data_quality_findings,
    list_source_health_checks,
    run_data_quality_checks,
    run_source_health_checks,
)
from app.services.source_service import SourceNotFoundError

router = APIRouter(prefix="/api/v1/data-quality", tags=["data-quality"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/run", response_model=DataQualityRunResult)
def run_data_quality_checks_endpoint(
    db: SessionDependency,
    source_id: UUID | None = None,
    min_severity: DataQualitySeverity | None = None,
) -> DataQualityRunResult:
    try:
        return run_data_quality_checks(db, source_id=source_id, min_severity=min_severity)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/source-health/run", response_model=SourceHealthRunResult)
def run_source_health_checks_endpoint(
    db: SessionDependency,
    source_id: UUID | None = None,
) -> SourceHealthRunResult:
    try:
        return run_source_health_checks(db, source_id=source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/checks", response_model=DataQualityFindingList)
def list_data_quality_findings_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    run_id: UUID | None = None,
    severity: DataQualitySeverity | None = None,
    min_severity: DataQualitySeverity | None = None,
    check_name: str | None = None,
    scope_type: DataQualityScopeType | None = None,
    source_id: UUID | None = None,
) -> DataQualityFindingList:
    findings, total = list_data_quality_findings(
        db,
        limit=limit,
        offset=offset,
        run_id=run_id,
        severity=severity,
        min_severity=min_severity,
        check_name=check_name,
        scope_type=scope_type,
        source_id=source_id,
    )
    return DataQualityFindingList(items=findings, total=total, limit=limit, offset=offset)


@router.get("/source-health", response_model=SourceHealthCheckList)
def list_source_health_checks_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_id: UUID | None = None,
    status: SourceHealthStatus | None = None,
) -> SourceHealthCheckList:
    checks, total = list_source_health_checks(
        db,
        limit=limit,
        offset=offset,
        source_id=source_id,
        status=status,
    )
    return SourceHealthCheckList(items=checks, total=total, limit=limit, offset=offset)


@router.get("/summary", response_model=DataQualitySummary)
def get_data_quality_summary_endpoint(db: SessionDependency) -> DataQualitySummary:
    return get_data_quality_summary(db)
