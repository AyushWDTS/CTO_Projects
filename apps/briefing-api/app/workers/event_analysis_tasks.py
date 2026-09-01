from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.event_analysis import EventAIAnalysisRead
from app.services.event_analysis_service import (
    analyze_by_source as run_analyze_by_source,
)
from app.services.event_analysis_service import (
    analyze_event as run_analyze_event,
)
from app.services.event_analysis_service import (
    analyze_pending_events as run_analyze_pending_events,
)
from app.services.event_analysis_service import (
    reprocess_failed_ai_analyses as run_reprocess_failed_ai_analyses,
)
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.event_analysis_tasks.analyze_event")
def analyze_event(event_id: str, force: bool = False) -> dict:
    db = SessionLocal()
    try:
        result = run_analyze_event(db, UUID(event_id), force=force)
        return EventAIAnalysisRead.model_validate(result).model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.event_analysis_tasks.analyze_pending_events")
def analyze_pending_events(limit: int = 50) -> dict:
    db = SessionLocal()
    try:
        result = run_analyze_pending_events(db, limit=limit)
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.event_analysis_tasks.analyze_by_source")
def analyze_by_source(source_id: str, limit: int = 50, force: bool = False) -> dict:
    db = SessionLocal()
    try:
        result = run_analyze_by_source(db, UUID(source_id), limit=limit, force=force)
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.event_analysis_tasks.reprocess_failed_ai_analyses")
def reprocess_failed_ai_analyses(limit: int = 50) -> dict:
    db = SessionLocal()
    try:
        result = run_reprocess_failed_ai_analyses(db, limit=limit)
        return result.model_dump(mode="json")
    finally:
        db.close()
