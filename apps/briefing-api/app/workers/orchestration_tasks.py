from datetime import date, datetime
from uuid import UUID

from app.db.session import SessionLocal
from app.models.orchestration import OrchestrationStepName
from app.schemas.orchestration import OrchestrationRunDetail, OrchestrationRunStepRead
from app.services.orchestration_service import (
    run_daily_pipeline as run_daily_pipeline_service,
)
from app.services.orchestration_service import (
    run_pipeline_for_window as run_pipeline_for_window_service,
)
from app.services.orchestration_service import (
    run_pipeline_step as run_pipeline_step_service,
)
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.orchestration_tasks.run_daily_pipeline")
def run_daily_pipeline(
    digest_date: str | None = None,
    dry_run: bool | None = None,
) -> dict:
    db = SessionLocal()
    try:
        result = run_daily_pipeline_service(
            db,
            digest_date=date.fromisoformat(digest_date) if digest_date else None,
            dry_run=dry_run,
            triggered_by="celery",
        )
        return OrchestrationRunDetail.model_validate(result).model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.orchestration_tasks.run_pipeline_for_window")
def run_pipeline_for_window(
    window_start: str,
    window_end: str,
    dry_run: bool | None = None,
) -> dict:
    db = SessionLocal()
    try:
        result = run_pipeline_for_window_service(
            db,
            window_start=datetime.fromisoformat(window_start),
            window_end=datetime.fromisoformat(window_end),
            dry_run=dry_run,
            triggered_by="celery",
        )
        return OrchestrationRunDetail.model_validate(result).model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.orchestration_tasks.run_pipeline_step")
def run_pipeline_step(run_id: str, step_name: str) -> dict:
    db = SessionLocal()
    try:
        result = run_pipeline_step_service(db, UUID(run_id), OrchestrationStepName(step_name))
        return OrchestrationRunStepRead.model_validate(result).model_dump(mode="json")
    finally:
        db.close()
