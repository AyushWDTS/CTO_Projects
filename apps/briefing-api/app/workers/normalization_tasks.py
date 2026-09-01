from uuid import UUID

from app.db.session import SessionLocal
from app.services.normalization_service import (
    normalize_by_source as run_normalize_by_source,
)
from app.services.normalization_service import (
    normalize_pending_raw_documents as run_normalize_pending_raw_documents,
)
from app.services.normalization_service import (
    normalize_raw_document as run_normalize_raw_document,
)
from app.services.normalization_service import (
    reprocess_failed_normalizations as run_reprocess_failed_normalizations,
)
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.normalization_tasks.normalize_raw_document")
def normalize_raw_document(raw_document_id: str) -> dict:
    db = SessionLocal()
    try:
        result = run_normalize_raw_document(db, UUID(raw_document_id))
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.normalization_tasks.normalize_pending_raw_documents")
def normalize_pending_raw_documents(limit: int = 100) -> dict:
    db = SessionLocal()
    try:
        result = run_normalize_pending_raw_documents(db, limit=limit)
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.normalization_tasks.normalize_by_source")
def normalize_by_source(source_id: str, limit: int = 100) -> dict:
    db = SessionLocal()
    try:
        result = run_normalize_by_source(db, UUID(source_id), limit=limit)
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.normalization_tasks.reprocess_failed_normalizations")
def reprocess_failed_normalizations(limit: int = 100) -> dict:
    db = SessionLocal()
    try:
        result = run_reprocess_failed_normalizations(db, limit=limit)
        return result.model_dump(mode="json")
    finally:
        db.close()
