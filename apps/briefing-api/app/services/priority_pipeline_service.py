from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.priority_pipeline_sources import PRIORITY_PIPELINE_SOURCE_NAMES
from app.models.article import Article, ArticleExtractionStatus
from app.models.event import EventArticle, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.models.ingestion import RawDocument
from app.models.source import Source
from app.schemas.clustering import ClusteringBatchResult
from app.schemas.event_analysis import EventAIAnalysisBatchResult
from app.schemas.normalization import NormalizationBatchResult
from app.services.clustering_service import cluster_by_source
from app.services.event_analysis_service import (
    analyze_pending_by_source_until_drained,
    count_analyzed_events_for_source,
    count_clustered_events_for_source,
    count_pending_analysis_for_source,
    pending_analysis_examples_for_source,
)
from app.services.normalization_service import (
    normalize_by_source_until_drained,
    count_pending_normalization_for_source,
)

DEFAULT_PRIORITY_PER_SOURCE_LIMIT = 50
MAX_PRIORITY_PER_SOURCE_LIMIT = 200
DEFAULT_PRIORITY_NORMALIZATION_ROUNDS = 5
DEFAULT_PRIORITY_ANALYSIS_ROUNDS = 5
CLUSTERED_ANALYSIS_PRIORITY_NAMES: tuple[str, ...] = (
    "RFID Journal",
    "IPC",
)


def normalize_priority_limit(limit: int) -> int:
    return max(1, min(limit, MAX_PRIORITY_PER_SOURCE_LIMIT))


def resolve_priority_sources(
    db: Session,
    *,
    source_names: tuple[str, ...] | None = None,
) -> list[Source]:
    names = source_names or PRIORITY_PIPELINE_SOURCE_NAMES
    rows = db.scalars(select(Source).where(Source.name.in_(names)).order_by(Source.name)).all()
    return list(rows)


def normalize_priority_sources(
    db: Session,
    *,
    limit_per_source: int = DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    max_rounds: int = DEFAULT_PRIORITY_NORMALIZATION_ROUNDS,
    source_names: tuple[str, ...] | None = None,
) -> dict:
    limit = normalize_priority_limit(limit_per_source)
    sources = resolve_priority_sources(db, source_names=source_names)
    results: list[dict] = []
    for source in sources:
        pending_before = count_pending_normalization_for_source(db, source.id)
        batch, rounds_used = normalize_by_source_until_drained(
            db,
            source.id,
            limit_per_batch=limit,
            max_rounds=max_rounds,
        )
        pending_after = count_pending_normalization_for_source(db, source.id)
        summary = _source_batch_summary(source, batch)
        summary["pending_before"] = pending_before
        summary["pending_after"] = pending_after
        summary["rounds_used"] = rounds_used
        results.append(summary)
    return {
        "stage": "normalization",
        "limit_per_source": limit,
        "max_rounds": max_rounds,
        "sources_processed": len(results),
        "results": results,
    }


def cluster_priority_sources(
    db: Session,
    *,
    limit_per_source: int = DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    source_names: tuple[str, ...] | None = None,
) -> dict:
    limit = normalize_priority_limit(limit_per_source)
    sources = resolve_priority_sources(db, source_names=source_names)
    results: list[dict] = []
    for source in sources:
        batch = cluster_by_source(db, source.id, limit=limit)
        results.append(_source_cluster_summary(source, batch))
    return {
        "stage": "clustering",
        "limit_per_source": limit,
        "sources_processed": len(results),
        "results": results,
    }


def analyze_priority_sources(
    db: Session,
    *,
    limit_per_source: int = DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    max_rounds: int = DEFAULT_PRIORITY_ANALYSIS_ROUNDS,
    source_names: tuple[str, ...] | None = None,
    clustered_events_only: bool = False,
) -> dict:
    limit = normalize_priority_limit(limit_per_source)
    sources = resolve_priority_sources(db, source_names=source_names)
    results: list[dict] = []
    total_failed = 0
    for source in sources:
        pending_before = count_pending_analysis_for_source(db, source.id)
        clustered_all_time = count_clustered_events_for_source(db, source.id)
        if clustered_events_only and pending_before == 0:
            results.append(
                _source_analysis_summary(
                    source,
                    pending_before=0,
                    clustered_all_time=clustered_all_time,
                    skipped=True,
                    skip_reason="no_pending_analysis",
                )
            )
            continue
        if pending_before == 0:
            results.append(
                _source_analysis_summary(
                    source,
                    pending_before=0,
                    clustered_all_time=clustered_all_time,
                    skipped=True,
                    skip_reason="no_pending_analysis",
                )
            )
            continue
        batch, rounds_used = analyze_pending_by_source_until_drained(
            db,
            source.id,
            limit_per_batch=limit,
            max_rounds=max_rounds,
        )
        total_failed += batch.failed
        pending_after = count_pending_analysis_for_source(db, source.id)
        summary = _source_analysis_summary(
            source,
            batch=batch,
            pending_before=pending_before,
            pending_after=pending_after,
            clustered_all_time=clustered_all_time,
            rounds_used=rounds_used,
        )
        results.append(summary)
    return {
        "stage": "event_analysis",
        "limit_per_source": limit,
        "max_rounds": max_rounds,
        "clustered_events_only": clustered_events_only,
        "sources_processed": len(results),
        "total_failed": total_failed,
        "results": results,
    }


def analyze_clustered_priority_sources(
    db: Session,
    *,
    limit_per_source: int = DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    max_rounds: int = DEFAULT_PRIORITY_ANALYSIS_ROUNDS,
    source_names: tuple[str, ...] | None = None,
) -> dict:
    names = source_names or CLUSTERED_ANALYSIS_PRIORITY_NAMES
    return analyze_priority_sources(
        db,
        limit_per_source=limit_per_source,
        max_rounds=max_rounds,
        source_names=names,
        clustered_events_only=True,
    )


def build_priority_funnel_report(
    db: Session,
    *,
    window_start: datetime,
    window_end: datetime,
    source_names: tuple[str, ...] | None = None,
    global_batch_limit: int = 200,
) -> dict:
    names = source_names or PRIORITY_PIPELINE_SOURCE_NAMES
    unclustered_global = int(
        db.scalar(
            select(func.count(Article.id))
            .outerjoin(EventArticle, EventArticle.article_id == Article.id)
            .where(Article.extraction_status == ArticleExtractionStatus.SUCCESS.value)
            .where(EventArticle.id.is_(None))
        )
        or 0
    )
    pending_norm_global = int(
        db.scalar(
            select(func.count(RawDocument.id))
            .outerjoin(Article, Article.raw_document_id == RawDocument.id)
            .where(Article.id.is_(None))
        )
        or 0
    )
    events_needing_analysis = int(
        db.scalar(
            select(func.count(NewsEvent.id))
            .outerjoin(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
            .where(
                (EventAIAnalysis.id.is_(None))
                | (EventAIAnalysis.status != EventAIAnalysisStatus.SUCCESS.value)
            )
        )
        or 0
    )

    rows: list[dict] = []
    for name in names:
        source = db.scalar(select(Source).where(Source.name == name))
        if source is None:
            rows.append(
                {
                    "source_name": name,
                    "source_id": None,
                    "status": "not_configured",
                    "starvation_diagnosis": "source_not_in_database",
                }
            )
            continue
        row = _funnel_row_for_source(
            db,
            source,
            window_start=window_start,
            window_end=window_end,
            global_batch_limit=global_batch_limit,
            unclustered_global=unclustered_global,
            events_needing_analysis=events_needing_analysis,
        )
        rows.append(row)

    return {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "global_backlog": {
            "pending_normalization": pending_norm_global,
            "unclustered_success_articles": unclustered_global,
            "events_needing_analysis": events_needing_analysis,
            "global_batch_limit": global_batch_limit,
        },
        "sources": rows,
    }


def _funnel_row_for_source(
    db: Session,
    source: Source,
    *,
    window_start: datetime,
    window_end: datetime,
    global_batch_limit: int,
    unclustered_global: int,
    events_needing_analysis: int,
) -> dict:
    source_id = source.id
    raw_ingested = _count_raw_documents(db, source_id, window_start, window_end)
    articles = _count_articles(db, source_id, window_start, window_end)
    norm_success = _count_articles(
        db,
        source_id,
        window_start,
        window_end,
        status=ArticleExtractionStatus.SUCCESS,
    )
    norm_failed = _count_articles(
        db,
        source_id,
        window_start,
        window_end,
        status=ArticleExtractionStatus.FAILED,
    )
    norm_duplicate = _count_articles(
        db,
        source_id,
        window_start,
        window_end,
        status=ArticleExtractionStatus.EXACT_DUPLICATE,
    )
    pending_norm = int(
        db.scalar(
            select(func.count(RawDocument.id))
            .outerjoin(Article, Article.raw_document_id == RawDocument.id)
            .where(RawDocument.source_id == source_id)
            .where(RawDocument.fetched_at >= window_start)
            .where(RawDocument.fetched_at < window_end)
            .where(Article.id.is_(None))
        )
        or 0
    )
    clustered = _count_clustered(db, source_id, window_start, window_end)
    analyzed = _count_analyzed(db, source_id, window_start, window_end)
    all_time_unclustered = int(
        db.scalar(
            select(func.count(Article.id))
            .outerjoin(EventArticle, EventArticle.article_id == Article.id)
            .where(Article.source_id == source_id)
            .where(Article.extraction_status == ArticleExtractionStatus.SUCCESS.value)
            .where(EventArticle.id.is_(None))
        )
        or 0
    )
    all_time_pending = count_pending_normalization_for_source(db, source_id)
    pending_examples = _pending_normalization_examples(
        db, source_id, window_start, window_end, limit=3
    )
    duplicate_examples = _duplicate_examples(
        db, source_id, window_start, window_end, limit=3
    )
    failed_examples = _failed_normalization_examples(
        db, source_id, window_start, window_end, limit=3
    )
    extraction_errors: list[str] = []
    if norm_failed:
        extraction_errors = list(
            db.scalars(
                select(Article.extraction_error)
                .join(RawDocument, Article.raw_document_id == RawDocument.id)
                .where(RawDocument.source_id == source_id)
                .where(RawDocument.fetched_at >= window_start)
                .where(RawDocument.fetched_at < window_end)
                .where(Article.extraction_status == ArticleExtractionStatus.FAILED.value)
                .limit(3)
            ).all()
        )

    diagnosis = _starvation_diagnosis(
        raw_ingested=raw_ingested,
        pending_normalization=pending_norm,
        all_time_pending_normalization=all_time_pending,
        normalization_success=norm_success,
        normalization_failed=norm_failed,
        normalization_duplicate=norm_duplicate,
        clustered=clustered,
        analyzed=analyzed,
        all_time_unclustered_success=all_time_unclustered,
        unclustered_global=unclustered_global,
        global_batch_limit=global_batch_limit,
        events_needing_analysis=events_needing_analysis,
    )
    root_cause = _normalization_root_cause(
        pending_normalization=pending_norm,
        all_time_pending_normalization=all_time_pending,
        normalization_success=norm_success,
        normalization_failed=norm_failed,
        normalization_duplicate=norm_duplicate,
        clustered=clustered,
        analyzed=analyzed,
        fetch_method=str(source.fetch_method),
    )

    return {
        "source_name": source.name,
        "source_id": str(source_id),
        "fetch_method": str(source.fetch_method),
        "raw_ingested": raw_ingested,
        "articles": articles,
        "normalization_success": norm_success,
        "normalization_failed": norm_failed,
        "normalization_duplicate": norm_duplicate,
        "pending_normalization": pending_norm,
        "all_time_pending_normalization": all_time_pending,
        "clustered": clustered,
        "analyzed": analyzed,
        "all_time_unclustered_success": all_time_unclustered,
        "extraction_errors": extraction_errors,
        "pending_examples": pending_examples,
        "duplicate_examples": duplicate_examples,
        "failed_examples": failed_examples,
        "starvation_diagnosis": diagnosis,
        "normalization_root_cause": root_cause,
        "likely_starved_by_global_batch": diagnosis.startswith("likely_batch_starvation")
        or root_cause.startswith("global_normalization_backlog"),
        "analysis_diagnostic": _analysis_diagnostic_for_source(
            db,
            source_id,
            window_clustered=clustered,
            window_analyzed=analyzed,
            events_needing_analysis_global=events_needing_analysis,
            global_batch_limit=global_batch_limit,
        ),
    }


def _starvation_diagnosis(
    *,
    raw_ingested: int,
    pending_normalization: int,
    all_time_pending_normalization: int = 0,
    normalization_success: int,
    normalization_failed: int,
    normalization_duplicate: int = 0,
    clustered: int,
    analyzed: int,
    all_time_unclustered_success: int,
    unclustered_global: int,
    global_batch_limit: int,
    events_needing_analysis: int = 0,
) -> str:
    if raw_ingested == 0:
        return "no_ingest_in_window"
    if clustered > 0 and analyzed == 0:
        if events_needing_analysis > global_batch_limit:
            return "likely_batch_starvation_at_analysis"
        return "likely_batch_starvation_at_analysis"
    if pending_normalization > 0 or (
        all_time_pending_normalization > 0 and normalization_success == 0 and clustered == 0
    ):
        if all_time_pending_normalization > global_batch_limit:
            return "blocked_at_normalization_backlog"
        return "blocked_at_normalization"
    if normalization_success == 0 and normalization_failed > 0:
        return "blocked_at_extraction_failure"
    if normalization_success == 0 and normalization_duplicate > 0:
        return "normalization_exact_duplicates_only"
    if normalization_success > 0 and clustered == 0:
        if all_time_unclustered_success > 0 and unclustered_global > global_batch_limit:
            return "likely_batch_starvation_at_clustering"
        if all_time_unclustered_success > 0:
            return "blocked_at_clustering_backlog"
        return "not_clustered_yet"
    if clustered > 0 and analyzed == 0:
        if events_needing_analysis > global_batch_limit:
            return "likely_batch_starvation_at_analysis"
        return "likely_batch_starvation_at_analysis"
    if analyzed > 0:
        return "reached_analysis"
    return "unknown"


def _normalization_root_cause(
    *,
    pending_normalization: int,
    all_time_pending_normalization: int,
    normalization_success: int,
    normalization_failed: int,
    normalization_duplicate: int,
    clustered: int,
    analyzed: int,
    fetch_method: str,
) -> str:
    if all_time_pending_normalization > 200:
        return (
            "global_normalization_backlog: raw documents waiting; global batch (200/run) "
            "processes newest feeds first"
        )
    if pending_normalization > 0:
        return "window_pending_normalization: raw docs in window not yet normalized"
    if normalization_failed > 0 and normalization_success == 0:
        return "extraction_failure: empty or unsupported raw content"
    if normalization_duplicate > 0 and normalization_success == 0:
        if fetch_method == "static_html":
            return (
                "static_html_repeat_snapshots: unchanged homepage re-ingested; "
                "canonical_url+content_hash marked exact_duplicate"
            )
        return (
            "rss_repeat_items: re-ingested RSS entries match prior canonical_url+content_hash"
        )
    if normalization_duplicate > normalization_success and fetch_method == "static_html":
        return (
            "static_html_mostly_duplicates: first snapshot succeeded; later identical fetches "
            "marked exact_duplicate and never cluster"
        )
    if clustered > 0 and analyzed == 0:
        return (
            "analysis_backlog: event exists but global analyze_pending_events batch has not "
            "reached this source yet; use priority analysis pass"
        )
    if normalization_success > 0 and clustered == 0:
        return "clustering_backlog: success articles waiting to cluster"
    if analyzed > 0:
        return "pipeline_reached_analysis"
    return "no_clear_blocker_in_window"


def _count_raw_documents(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
) -> int:
    return int(
        db.scalar(
            select(func.count(RawDocument.id))
            .where(RawDocument.source_id == source_id)
            .where(RawDocument.fetched_at >= window_start)
            .where(RawDocument.fetched_at < window_end)
        )
        or 0
    )


def _count_articles(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
    *,
    status: ArticleExtractionStatus | None = None,
) -> int:
    query = (
        select(func.count(Article.id))
        .join(RawDocument, Article.raw_document_id == RawDocument.id)
        .where(RawDocument.source_id == source_id)
        .where(RawDocument.fetched_at >= window_start)
        .where(RawDocument.fetched_at < window_end)
    )
    if status is not None:
        query = query.where(Article.extraction_status == status.value)
    return int(db.scalar(query) or 0)


def _count_clustered(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
) -> int:
    return int(
        db.scalar(
            select(func.count(EventArticle.id))
            .join(Article, EventArticle.article_id == Article.id)
            .join(RawDocument, Article.raw_document_id == RawDocument.id)
            .where(RawDocument.source_id == source_id)
            .where(RawDocument.fetched_at >= window_start)
            .where(RawDocument.fetched_at < window_end)
        )
        or 0
    )


def _count_analyzed(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(EventAIAnalysis.id)))
            .join(NewsEvent, EventAIAnalysis.event_id == NewsEvent.id)
            .join(EventArticle, EventArticle.event_id == NewsEvent.id)
            .join(Article, EventArticle.article_id == Article.id)
            .join(RawDocument, Article.raw_document_id == RawDocument.id)
            .where(RawDocument.source_id == source_id)
            .where(RawDocument.fetched_at >= window_start)
            .where(RawDocument.fetched_at < window_end)
            .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value)
        )
        or 0
    )


def _pending_normalization_examples(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
    *,
    limit: int,
) -> list[dict[str, str]]:
    rows = db.execute(
        select(RawDocument.url, RawDocument.fetched_at)
        .outerjoin(Article, Article.raw_document_id == RawDocument.id)
        .where(RawDocument.source_id == source_id)
        .where(RawDocument.fetched_at >= window_start)
        .where(RawDocument.fetched_at < window_end)
        .where(Article.id.is_(None))
        .order_by(RawDocument.fetched_at.desc())
        .limit(limit)
    ).all()
    return [
        {"url": str(url), "fetched_at": fetched_at.isoformat() if fetched_at else ""}
        for url, fetched_at in rows
    ]


def _duplicate_examples(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
    *,
    limit: int,
) -> list[dict[str, str]]:
    rows = db.execute(
        select(Article.title, Article.canonical_url, Article.duplicate_of_article_id)
        .join(RawDocument, Article.raw_document_id == RawDocument.id)
        .where(RawDocument.source_id == source_id)
        .where(RawDocument.fetched_at >= window_start)
        .where(RawDocument.fetched_at < window_end)
        .where(Article.extraction_status == ArticleExtractionStatus.EXACT_DUPLICATE.value)
        .limit(limit)
    ).all()
    return [
        {
            "title": str(title or ""),
            "url": str(url or ""),
            "duplicate_of_article_id": str(dup_id) if dup_id else "",
        }
        for title, url, dup_id in rows
    ]


def _failed_normalization_examples(
    db: Session,
    source_id: UUID,
    window_start: datetime,
    window_end: datetime,
    *,
    limit: int,
) -> list[dict[str, str]]:
    rows = db.execute(
        select(Article.title, Article.canonical_url, Article.extraction_error)
        .join(RawDocument, Article.raw_document_id == RawDocument.id)
        .where(RawDocument.source_id == source_id)
        .where(RawDocument.fetched_at >= window_start)
        .where(RawDocument.fetched_at < window_end)
        .where(Article.extraction_status == ArticleExtractionStatus.FAILED.value)
        .limit(limit)
    ).all()
    return [
        {
            "title": str(title or ""),
            "url": str(url or ""),
            "error": str(error or ""),
        }
        for title, url, error in rows
    ]


def _source_batch_summary(source: Source, batch: NormalizationBatchResult) -> dict:
    created = sum(1 for item in batch.results if item.article_id is not None)
    failed = sum(1 for item in batch.results if item.status == ArticleExtractionStatus.FAILED)
    success = sum(1 for item in batch.results if item.status == ArticleExtractionStatus.SUCCESS)
    duplicate = sum(
        1 for item in batch.results if item.status == ArticleExtractionStatus.EXACT_DUPLICATE
    )
    return {
        "source_id": str(source.id),
        "source_name": source.name,
        "items_processed": batch.total_raw_documents,
        "items_created": created,
        "items_failed": failed,
        "normalization_success": success,
        "normalization_duplicate": duplicate,
    }


def _source_cluster_summary(source: Source, batch: ClusteringBatchResult) -> dict:
    return {
        "source_id": str(source.id),
        "source_name": source.name,
        "items_processed": batch.total_articles,
        "created_events": batch.created_events,
        "linked_articles": batch.linked_articles,
        "skipped_articles": batch.skipped_articles,
    }


def _analysis_diagnostic_for_source(
    db: Session,
    source_id: UUID,
    *,
    window_clustered: int,
    window_analyzed: int,
    events_needing_analysis_global: int,
    global_batch_limit: int,
) -> dict:
    clustered_all_time = count_clustered_events_for_source(db, source_id)
    analyzed_all_time = count_analyzed_events_for_source(db, source_id)
    pending_analysis = count_pending_analysis_for_source(db, source_id)
    examples = pending_analysis_examples_for_source(db, source_id, limit=3)

    if clustered_all_time == 0:
        drop_off = "not_clustered_yet"
        cause = "no_clustered_events_for_source"
    elif pending_analysis == 0 and analyzed_all_time > 0:
        drop_off = "reached_analysis"
        cause = "analysis_complete_for_clustered_events"
    elif pending_analysis > 0:
        drop_off = "clustering_to_analysis_gap"
        if events_needing_analysis_global > global_batch_limit:
            cause = "global_analysis_queue_starvation"
        else:
            cause = "pending_analysis_not_yet_scheduled"
    else:
        drop_off = "unknown"
        cause = "no_pending_analysis_and_not_analyzed"

    return {
        "clustered_events_all_time": clustered_all_time,
        "analyzed_events_all_time": analyzed_all_time,
        "pending_analysis_events": pending_analysis,
        "window_clustered": window_clustered,
        "window_analyzed": window_analyzed,
        "global_events_needing_analysis": events_needing_analysis_global,
        "global_batch_limit": global_batch_limit,
        "analysis_drop_off": drop_off,
        "analysis_drop_off_cause": cause,
        "pending_analysis_examples": examples,
        "reached_by_global_queue": pending_analysis == 0 and analyzed_all_time > 0,
        "starved_by_global_queue": pending_analysis > 0 and events_needing_analysis_global > 0,
    }


def _source_analysis_summary(
    source: Source,
    *,
    batch: EventAIAnalysisBatchResult | None = None,
    pending_before: int = 0,
    pending_after: int = 0,
    clustered_all_time: int = 0,
    rounds_used: int = 0,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict:
    if skipped or batch is None:
        return {
            "source_id": str(source.id),
            "source_name": source.name,
            "skipped": True,
            "skip_reason": skip_reason,
            "pending_before": pending_before,
            "pending_after": pending_after,
            "clustered_events_all_time": clustered_all_time,
            "items_processed": 0,
            "analyzed": 0,
            "failed": 0,
        }
    return {
        "source_id": str(source.id),
        "source_name": source.name,
        "skipped": False,
        "pending_before": pending_before,
        "pending_after": pending_after,
        "clustered_events_all_time": clustered_all_time,
        "rounds_used": rounds_used,
        "items_processed": batch.total_events,
        "analyzed": batch.analyzed,
        "failed": batch.failed,
    }
