from uuid import UUID

from app.db.session import SessionLocal
from app.services.clustering_service import (
    cluster_article as run_cluster_article,
)
from app.services.clustering_service import (
    cluster_by_source as run_cluster_by_source,
)
from app.services.clustering_service import (
    cluster_pending_articles as run_cluster_pending_articles,
)
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.clustering_tasks.cluster_article")
def cluster_article(article_id: str, reprocess: bool = False) -> dict:
    db = SessionLocal()
    try:
        result = run_cluster_article(db, UUID(article_id), reprocess=reprocess)
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.clustering_tasks.cluster_pending_articles")
def cluster_pending_articles(limit: int = 100, reprocess: bool = False) -> dict:
    db = SessionLocal()
    try:
        result = run_cluster_pending_articles(db, limit=limit, reprocess=reprocess)
        return result.model_dump(mode="json")
    finally:
        db.close()


@celery_app.task(name="app.workers.clustering_tasks.cluster_by_source")
def cluster_by_source(source_id: str, limit: int = 100, reprocess: bool = False) -> dict:
    db = SessionLocal()
    try:
        result = run_cluster_by_source(db, UUID(source_id), limit=limit, reprocess=reprocess)
        return result.model_dump(mode="json")
    finally:
        db.close()
