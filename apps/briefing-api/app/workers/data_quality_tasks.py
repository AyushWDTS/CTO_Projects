from uuid import UUID

from app.db.session import SessionLocal
from app.models.data_quality import DataQualitySeverity
from app.services import data_quality_service
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.data_quality_tasks.run_data_quality_checks")
def run_data_quality_checks(
    source_id: str | None = None,
    min_severity: str | None = None,
) -> dict:
    db = SessionLocal()
    try:
        result = data_quality_service.run_data_quality_checks(
            db,
            source_id=UUID(source_id) if source_id else None,
            min_severity=DataQualitySeverity(min_severity) if min_severity else None,
        )
        return result.model_dump(mode="json", by_alias=True)
    finally:
        db.close()


@celery_app.task(name="app.workers.data_quality_tasks.check_source_health")
def check_source_health(source_id: str | None = None) -> dict:
    db = SessionLocal()
    try:
        result = data_quality_service.run_source_health_checks(
            db,
            source_id=UUID(source_id) if source_id else None,
        )
        return result.model_dump(mode="json", by_alias=True)
    finally:
        db.close()
