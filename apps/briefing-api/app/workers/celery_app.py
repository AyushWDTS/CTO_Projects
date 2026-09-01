from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "news_intelligence_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

if settings.ORCHESTRATION_ENABLED:
    minute, hour, day_of_month, month_of_year, day_of_week = (
        settings.ORCHESTRATION_DAILY_SCHEDULE_CRON.split()
    )
    celery_app.conf.beat_schedule = {
        "phase8-daily-pipeline": {
            "task": "app.workers.orchestration_tasks.run_daily_pipeline",
            "schedule": crontab(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week,
            ),
        }
    }
    celery_app.conf.timezone = settings.ORCHESTRATION_TIMEZONE


@celery_app.task(name="app.workers.celery_app.ping")
def ping() -> str:
    return "pong"


from app.workers import (  # noqa: E402, F401
    clustering_tasks,
    data_quality_tasks,
    digest_tasks,
    event_analysis_tasks,
    ingestion_tasks,
    normalization_tasks,
    orchestration_tasks,
)
