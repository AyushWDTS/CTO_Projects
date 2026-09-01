from datetime import datetime
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.digest import DigestDetailRead
from app.services.digest_service import build_digest
from app.services.digest_service import refresh_digest as run_refresh_digest
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.digest_tasks.build_daily_digest")
def build_daily_digest(limit: int = 15, include_low: bool = False) -> dict:
    db = SessionLocal()
    try:
        result = build_digest(db, limit=limit, include_low=include_low)
        return DigestDetailRead.model_validate(result).model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.digest_tasks.build_digest_for_window")
def build_digest_for_window(
    window_start: str,
    window_end: str,
    limit: int = 15,
    include_low: bool = False,
    refresh: bool = False,
) -> dict:
    db = SessionLocal()
    try:
        result = build_digest(
            db,
            window_start=datetime.fromisoformat(window_start),
            window_end=datetime.fromisoformat(window_end),
            limit=limit,
            include_low=include_low,
            refresh=refresh,
        )
        return DigestDetailRead.model_validate(result).model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.digest_tasks.refresh_digest")
def refresh_digest(digest_id: str) -> dict:
    db = SessionLocal()
    try:
        result = run_refresh_digest(db, UUID(digest_id))
        return DigestDetailRead.model_validate(result).model_dump(mode="json")
    finally:
        db.close()
