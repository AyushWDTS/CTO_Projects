from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.orchestration import OrchestrationRunType, OrchestrationStatus
from app.schemas.orchestration import (
    OrchestrationRunDetail,
    OrchestrationRunList,
    OrchestrationRunRequest,
    OrchestrationRunResult,
    OrchestrationRunStepList,
)
from app.services.orchestration_service import (
    OrchestrationInvalidRequestError,
    OrchestrationRunAlreadyActiveError,
    OrchestrationRunNotFoundError,
    get_orchestration_run,
    list_orchestration_run_steps,
    list_orchestration_runs,
    run_daily_pipeline,
    run_demo_pipeline,
    run_pipeline_for_window,
)

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/run", response_model=OrchestrationRunResult)
def run_orchestration_endpoint(
    request: OrchestrationRunRequest,
    db: SessionDependency,
) -> OrchestrationRunResult:
    try:
        if request.window_start and request.window_end:
            run = run_pipeline_for_window(
                db,
                window_start=request.window_start,
                window_end=request.window_end,
                dry_run=request.dry_run,
                skip_ingestion=request.skip_ingestion,
                skip_normalization=request.skip_normalization,
                skip_clustering=request.skip_clustering,
                skip_ai=request.skip_ai,
                continue_on_ai_failure=request.continue_on_ai_failure,
                refresh_digest=request.refresh_digest,
                limit=request.limit,
                digest_limit=request.digest_limit,
                triggered_by=request.triggered_by,
            )
        else:
            run = run_daily_pipeline(
                db,
                digest_date=request.digest_date,
                dry_run=request.dry_run,
                skip_ingestion=request.skip_ingestion,
                skip_normalization=request.skip_normalization,
                skip_clustering=request.skip_clustering,
                skip_ai=request.skip_ai,
                continue_on_ai_failure=request.continue_on_ai_failure,
                refresh_digest=request.refresh_digest,
                limit=request.limit,
                digest_limit=request.digest_limit,
                triggered_by=request.triggered_by,
            )
        return OrchestrationRunResult(run=OrchestrationRunDetail.model_validate(run))
    except OrchestrationRunAlreadyActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrchestrationInvalidRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/demo/run", response_model=OrchestrationRunResult)
def run_demo_orchestration_endpoint(
    request: OrchestrationRunRequest,
    db: SessionDependency,
) -> OrchestrationRunResult:
    try:
        run = run_demo_pipeline(
            db,
            digest_date=request.digest_date,
            dry_run=request.dry_run,
            skip_ingestion=request.skip_ingestion,
            continue_on_ai_failure=request.continue_on_ai_failure,
            limit=request.limit,
            digest_limit=request.digest_limit,
            triggered_by=request.triggered_by,
        )
        return OrchestrationRunResult(run=OrchestrationRunDetail.model_validate(run))
    except OrchestrationRunAlreadyActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrchestrationInvalidRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/daily/run", response_model=OrchestrationRunResult)
def run_daily_orchestration_endpoint(
    request: OrchestrationRunRequest,
    db: SessionDependency,
) -> OrchestrationRunResult:
    try:
        run = run_daily_pipeline(
            db,
            digest_date=request.digest_date,
            dry_run=request.dry_run,
            skip_ingestion=request.skip_ingestion,
            skip_normalization=request.skip_normalization,
            skip_clustering=request.skip_clustering,
            skip_ai=request.skip_ai,
            continue_on_ai_failure=request.continue_on_ai_failure,
            refresh_digest=request.refresh_digest,
            limit=request.limit,
            digest_limit=request.digest_limit,
            triggered_by=request.triggered_by,
        )
        return OrchestrationRunResult(run=OrchestrationRunDetail.model_validate(run))
    except OrchestrationRunAlreadyActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrchestrationInvalidRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/runs", response_model=OrchestrationRunList)
def list_orchestration_runs_endpoint(
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    run_type: OrchestrationRunType | None = None,
    status: OrchestrationStatus | None = None,
    digest_date: date | None = None,
    triggered_by: str | None = None,
    lock_key: str | None = None,
    idempotency_key: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> OrchestrationRunList:
    rows, total = list_orchestration_runs(
        db,
        limit=limit,
        offset=offset,
        run_type=run_type,
        status=status,
        digest_date=digest_date,
        triggered_by=triggered_by,
        lock_key=lock_key,
        idempotency_key=idempotency_key,
        created_from=created_from,
        created_to=created_to,
    )
    return OrchestrationRunList(items=rows, total=total, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=OrchestrationRunDetail)
def get_orchestration_run_endpoint(
    run_id: UUID,
    db: SessionDependency,
) -> OrchestrationRunDetail:
    try:
        return get_orchestration_run(db, run_id)
    except OrchestrationRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/runs/{run_id}/steps", response_model=OrchestrationRunStepList)
def list_orchestration_run_steps_endpoint(
    run_id: UUID,
    db: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrchestrationRunStepList:
    try:
        rows, total = list_orchestration_run_steps(db, run_id, limit=limit, offset=offset)
        return OrchestrationRunStepList(items=rows, total=total, limit=limit, offset=offset)
    except OrchestrationRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
