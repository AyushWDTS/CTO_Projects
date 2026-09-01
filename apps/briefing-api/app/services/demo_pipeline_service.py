from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select

from app.models.article import Article
from app.models.event import EventArticle
from app.models.ingestion import RawDocument
from app.models.orchestration import OrchestrationRun, OrchestrationStatus

SUCCESSFUL_RUN_STATUSES = (
    OrchestrationStatus.SUCCESS.value,
    OrchestrationStatus.PARTIAL_SUCCESS.value,
)


def resolve_demo_fetched_after(
    db,
    *,
    run_started_at: datetime,
    exclude_run_id: UUID | None = None,
) -> tuple[datetime, str, bool]:
    """Return watermark, source label, and whether the comparison should be inclusive."""
    query = (
        select(OrchestrationRun.finished_at)
        .where(OrchestrationRun.status.in_(SUCCESSFUL_RUN_STATUSES))
        .where(OrchestrationRun.finished_at.is_not(None))
        .order_by(OrchestrationRun.finished_at.desc())
        .limit(1)
    )
    if exclude_run_id is not None:
        query = query.where(OrchestrationRun.id != exclude_run_id)
    last_finished = db.scalar(query)
    if last_finished is not None:
        return ensure_utc(last_finished), "last_successful_run_finished_at", False
    return ensure_utc(run_started_at), "current_run_started_at", True


def fresh_fetch_event_ids_subquery(fetched_after: datetime, *, inclusive: bool = False):
    comparison = RawDocument.fetched_at >= fetched_after if inclusive else RawDocument.fetched_at > fetched_after
    return (
        select(EventArticle.event_id)
        .join(Article, Article.id == EventArticle.article_id)
        .join(RawDocument, RawDocument.id == Article.raw_document_id)
        .where(comparison)
        .distinct()
    )


def apply_raw_document_fetched_after(
    query: Select,
    fetched_after: datetime,
    *,
    inclusive: bool = False,
) -> Select:
    if inclusive:
        return query.where(RawDocument.fetched_at >= fetched_after)
    return query.where(RawDocument.fetched_at > fetched_after)


def apply_article_fetched_after(
    query: Select,
    fetched_after: datetime,
    *,
    inclusive: bool = False,
) -> Select:
    query = query.join(RawDocument, RawDocument.id == Article.raw_document_id)
    if inclusive:
        return query.where(RawDocument.fetched_at >= fetched_after)
    return query.where(RawDocument.fetched_at > fetched_after)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
