from uuid import UUID

from app.db.session import SessionLocal
from app.services.ingestion_service import ingest_all_sources as run_all_sources_ingestion
from app.services.ingestion_service import ingest_source as run_source_ingestion
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.ingestion_tasks.ingest_source")
def ingest_source(source_id: str) -> dict:
    db = SessionLocal()
    try:
        result = run_source_ingestion(db, UUID(source_id))
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.ingestion_tasks.ingest_all_sources")
def ingest_all_sources() -> dict:
    db = SessionLocal()
    try:
        result = run_all_sources_ingestion(db)
        return result.model_dump(mode="json")
    finally:
        db.close()
