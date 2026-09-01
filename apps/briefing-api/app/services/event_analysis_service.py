import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Select, distinct, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.event import EventArticle, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.schemas.event_analysis import (
    EventAIAnalysisBatchResult,
    EventAIAnalysisRead,
    EventAIModelOutput,
)
from app.services.ai_provider import (
    AIProviderError,
    EventAnalysisProvider,
    MissingAIAPIKeyError,
    get_ai_provider,
)
from app.services.ai_response_parser import InvalidModelJsonError, parse_model_json
from app.services.event_context_service import EventContextNotFoundError, build_event_context
from app.services.briefing_text_service import distinct_summary
from app.services.prompt_service import PROMPT_VERSION, build_event_analysis_prompt

DEFAULT_EVENT_ANALYSIS_LIMIT = 50
MAX_EVENT_ANALYSIS_LIMIT = 200


class EventAIAnalysisNotFoundError(Exception):
    pass


class NewsEventNotFoundError(Exception):
    pass


def normalize_analysis_limit(limit: int) -> int:
    return max(1, min(limit, MAX_EVENT_ANALYSIS_LIMIT))


def analyze_event(
    db: Session,
    event_id: UUID,
    *,
    force: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysis:
    settings = settings or get_settings()
    provider = provider or get_ai_provider(settings)

    try:
        context = build_event_context(db, event_id, settings=settings)
    except EventContextNotFoundError as exc:
        raise NewsEventNotFoundError(str(exc)) from exc

    analysis = _lock_or_create_analysis(db, event_id)
    if (
        not force
        and analysis.status == EventAIAnalysisStatus.SUCCESS.value
        and analysis.content_signature == context.content_signature
    ):
        db.commit()
        db.refresh(analysis)
        return analysis

    _apply_traceability(analysis, context)
    analysis.status = EventAIAnalysisStatus.PENDING.value
    analysis.error_message = None
    analysis.content_signature = context.content_signature
    db.flush()

    if context.context_article_count == 0:
        _apply_skipped(analysis, "no_event_articles")
        db.commit()
        db.refresh(analysis)
        return analysis

    prompt = build_event_analysis_prompt(context)
    try:
        response = provider.analyze(prompt)
        output = _parse_model_output(response.content)
        _apply_success(analysis, output, response, settings)
    except MissingAIAPIKeyError:
        _apply_failed(analysis, "missing_ai_api_key")
    except InvalidModelJsonError as exc:
        _apply_failed(
            analysis,
            "invalid_ai_json",
            detail=str(exc),
            raw_preview=exc.raw_content,
        )
    except (AIProviderError, ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
        reason = "invalid_ai_json" if not isinstance(exc, AIProviderError) else "ai_provider_error"
        _apply_failed(analysis, reason, detail=str(exc))

    db.commit()
    db.refresh(analysis)
    return analysis


def analyze_pending_events(
    db: Session,
    *,
    limit: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    normalized_limit = normalize_analysis_limit(limit)
    query = (
        select(NewsEvent.id)
        .outerjoin(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
        .where(
            (EventAIAnalysis.id.is_(None))
            | (EventAIAnalysis.status != EventAIAnalysisStatus.SUCCESS.value)
        )
        .order_by(NewsEvent.published_at.desc().nullslast(), NewsEvent.created_at.desc())
        .limit(normalized_limit)
    )
    if fetched_after is not None:
        from app.services.demo_pipeline_service import fresh_fetch_event_ids_subquery

        query = query.where(
            NewsEvent.id.in_(
                fresh_fetch_event_ids_subquery(
                    fetched_after,
                    inclusive=fetched_after_inclusive,
                )
            )
        )
    event_ids = list(db.scalars(query))
    return _analyze_event_ids(db, event_ids, provider=provider, settings=settings)


def analyze_by_source(
    db: Session,
    source_id: UUID,
    *,
    limit: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    force: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    return analyze_pending_by_source(
        db,
        source_id,
        limit=limit,
        force=force,
        provider=provider,
        settings=settings,
    )


def analyze_pending_by_source(
    db: Session,
    source_id: UUID,
    *,
    limit: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    force: bool = False,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    event_ids = list(
        db.scalars(
            _pending_analysis_query(
                source_id,
                fetched_after=fetched_after,
                fetched_after_inclusive=fetched_after_inclusive,
            )
            .order_by(
                NewsEvent.published_at.desc().nullslast(),
                NewsEvent.created_at.desc(),
            )
            .limit(normalize_analysis_limit(limit))
        )
    )
    return _analyze_event_ids(
        db,
        event_ids,
        force=force,
        provider=provider,
        settings=settings,
    )


def analyze_pending_by_source_until_drained(
    db: Session,
    source_id: UUID,
    *,
    limit_per_batch: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    max_rounds: int = 10,
    force: bool = False,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> tuple[EventAIAnalysisBatchResult, int]:
    normalized_batch_limit = normalize_analysis_limit(limit_per_batch)
    max_rounds = max(1, max_rounds)
    all_results: list[EventAIAnalysisRead] = []
    rounds_used = 0
    for _ in range(max_rounds):
        event_ids = list(
            db.scalars(
                _pending_analysis_query(
                source_id,
                fetched_after=fetched_after,
                fetched_after_inclusive=fetched_after_inclusive,
            )
                .order_by(
                    NewsEvent.published_at.desc().nullslast(),
                    NewsEvent.created_at.desc(),
                )
                .limit(normalized_batch_limit)
            )
        )
        rounds_used += 1
        if not event_ids:
            break
        batch = _analyze_event_ids(
            db,
            event_ids,
            force=force,
            provider=provider,
            settings=settings,
        )
        all_results.extend(batch.results)
        if len(event_ids) < normalized_batch_limit:
            break
    return (
        EventAIAnalysisBatchResult(
            total_events=len(all_results),
            analyzed=sum(
                1 for result in all_results if result.status == EventAIAnalysisStatus.SUCCESS
            ),
            skipped=sum(
                1 for result in all_results if result.status == EventAIAnalysisStatus.SKIPPED
            ),
            failed=sum(
                1 for result in all_results if result.status == EventAIAnalysisStatus.FAILED
            ),
            results=all_results,
        ),
        rounds_used,
    )


def count_pending_analysis_for_source(db: Session, source_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(NewsEvent.id)))
            .select_from(EventArticle)
            .join(NewsEvent, NewsEvent.id == EventArticle.event_id)
            .outerjoin(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
            .where(EventArticle.source_id == source_id)
            .where(
                (EventAIAnalysis.id.is_(None))
                | (EventAIAnalysis.status != EventAIAnalysisStatus.SUCCESS.value)
            )
        )
        or 0
    )


def count_clustered_events_for_source(db: Session, source_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(NewsEvent.id)))
            .select_from(EventArticle)
            .join(NewsEvent, NewsEvent.id == EventArticle.event_id)
            .where(EventArticle.source_id == source_id)
        )
        or 0
    )


def count_analyzed_events_for_source(db: Session, source_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(NewsEvent.id)))
            .select_from(EventArticle)
            .join(NewsEvent, NewsEvent.id == EventArticle.event_id)
            .join(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
            .where(EventArticle.source_id == source_id)
            .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value)
        )
        or 0
    )


def pending_analysis_examples_for_source(
    db: Session,
    source_id: UUID,
    *,
    limit: int = 3,
) -> list[dict[str, str]]:
    rows = db.execute(
        select(
            NewsEvent.id,
            NewsEvent.canonical_title,
            NewsEvent.published_at,
            NewsEvent.created_at,
        )
        .select_from(EventArticle)
        .join(NewsEvent, NewsEvent.id == EventArticle.event_id)
        .outerjoin(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
        .where(EventArticle.source_id == source_id)
        .where(
            (EventAIAnalysis.id.is_(None))
            | (EventAIAnalysis.status != EventAIAnalysisStatus.SUCCESS.value)
        )
        .group_by(
            NewsEvent.id,
            NewsEvent.canonical_title,
            NewsEvent.published_at,
            NewsEvent.created_at,
        )
        .order_by(NewsEvent.published_at.desc().nullslast(), NewsEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "event_id": str(event_id),
            "headline": str(title or ""),
            "published_at": (
                published_at.isoformat()
                if published_at is not None
                else (created_at.isoformat() if created_at is not None else "")
            ),
        }
        for event_id, title, published_at, created_at in rows
    ]


def _pending_analysis_query(
    source_id: UUID,
    *,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
):
    query = (
        select(NewsEvent.id)
        .select_from(EventArticle)
        .join(NewsEvent, NewsEvent.id == EventArticle.event_id)
        .outerjoin(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
        .where(EventArticle.source_id == source_id)
        .where(
            (EventAIAnalysis.id.is_(None))
            | (EventAIAnalysis.status != EventAIAnalysisStatus.SUCCESS.value)
        )
        .group_by(NewsEvent.id, NewsEvent.published_at, NewsEvent.created_at)
    )
    if fetched_after is not None:
        from app.services.demo_pipeline_service import fresh_fetch_event_ids_subquery

        query = query.where(
            NewsEvent.id.in_(
                fresh_fetch_event_ids_subquery(
                    fetched_after,
                    inclusive=fetched_after_inclusive,
                )
            )
        )
    return query


def analyze_by_category(
    db: Session,
    category: str,
    *,
    limit: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    force: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    query = (
        select(NewsEvent.id)
        .where(NewsEvent.category == category)
        .order_by(NewsEvent.published_at.desc().nullslast(), NewsEvent.created_at.desc())
        .limit(normalize_analysis_limit(limit))
    )
    return _analyze_event_ids(
        db,
        list(db.scalars(query)),
        force=force,
        provider=provider,
        settings=settings,
    )


def analyze_by_region(
    db: Session,
    region: str,
    *,
    limit: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    force: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    query = (
        select(NewsEvent.id)
        .where(NewsEvent.region == region)
        .order_by(NewsEvent.published_at.desc().nullslast(), NewsEvent.created_at.desc())
        .limit(normalize_analysis_limit(limit))
    )
    return _analyze_event_ids(
        db,
        list(db.scalars(query)),
        force=force,
        provider=provider,
        settings=settings,
    )


def reprocess_failed_ai_analyses(
    db: Session,
    *,
    limit: int = DEFAULT_EVENT_ANALYSIS_LIMIT,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    event_ids = list(
        db.scalars(
            select(EventAIAnalysis.event_id)
            .where(EventAIAnalysis.status == EventAIAnalysisStatus.FAILED.value)
            .order_by(EventAIAnalysis.updated_at.asc())
            .limit(normalize_analysis_limit(limit))
        )
    )
    return _analyze_event_ids(db, event_ids, force=True, provider=provider, settings=settings)


def get_event_ai_analysis(db: Session, event_id: UUID) -> EventAIAnalysis:
    analysis = db.scalar(select(EventAIAnalysis).where(EventAIAnalysis.event_id == event_id))
    if analysis is None:
        raise EventAIAnalysisNotFoundError("Event AI analysis not found.")
    return analysis


def list_event_ai_analyses(
    db: Session,
    *,
    limit: int,
    offset: int,
    status: EventAIAnalysisStatus | None = None,
    importance_tier: str | None = None,
    min_relevance_score: float | None = None,
    min_urgency_score: float | None = None,
    source_id: UUID | None = None,
    category: str | None = None,
    region: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> tuple[list[EventAIAnalysis], int]:
    filters = {
        "status": status,
        "importance_tier": importance_tier,
        "min_relevance_score": min_relevance_score,
        "min_urgency_score": min_urgency_score,
        "source_id": source_id,
        "category": category,
        "region": region,
        "created_from": created_from,
        "created_to": created_to,
    }
    query = _apply_analysis_filters(select(EventAIAnalysis), filters).order_by(
        EventAIAnalysis.created_at.desc()
    )
    count_query = _apply_analysis_filters(select(func.count(distinct(EventAIAnalysis.id))), filters)
    if source_id is not None:
        query = query.distinct()
    analyses = list(db.scalars(query.limit(limit).offset(offset)))
    total = db.scalar(count_query) or 0
    return analyses, total


def _analyze_event_ids(
    db: Session,
    event_ids: list[UUID],
    *,
    force: bool = False,
    provider: EventAnalysisProvider | None = None,
    settings: Settings | None = None,
) -> EventAIAnalysisBatchResult:
    results = [
        EventAIAnalysisRead.model_validate(
            analyze_event(db, event_id, force=force, provider=provider, settings=settings)
        )
        for event_id in event_ids
    ]
    return EventAIAnalysisBatchResult(
        total_events=len(event_ids),
        analyzed=sum(1 for result in results if result.status == EventAIAnalysisStatus.SUCCESS),
        skipped=sum(1 for result in results if result.status == EventAIAnalysisStatus.SKIPPED),
        failed=sum(1 for result in results if result.status == EventAIAnalysisStatus.FAILED),
        results=results,
    )


def _lock_or_create_analysis(db: Session, event_id: UUID) -> EventAIAnalysis:
    db.execute(
        insert(EventAIAnalysis)
        .values(event_id=event_id, status=EventAIAnalysisStatus.PENDING.value)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    db.flush()
    analysis = db.scalar(
        select(EventAIAnalysis)
        .where(EventAIAnalysis.event_id == event_id)
        .with_for_update()
    )
    if analysis is None:
        raise EventAIAnalysisNotFoundError("Event AI analysis not found.")
    return analysis


def _parse_model_output(content: str) -> EventAIModelOutput:
    parsed = parse_model_json(content)
    return EventAIModelOutput.model_validate(parsed)


def _apply_success(
    analysis: EventAIAnalysis,
    output: EventAIModelOutput,
    response,
    settings: Settings,
) -> None:
    analysis.summary = distinct_summary(
        output.short_summary,
        output.summary,
        fallback=output.key_points[0] if output.key_points else None,
    ) or output.summary
    analysis.short_summary = output.short_summary[:500]
    analysis.why_it_matters = output.why_it_matters
    analysis.key_points = output.key_points
    analysis.entities = [entity.model_dump() for entity in output.entities]
    analysis.topics = output.topics
    analysis.sentiment = output.sentiment.value
    analysis.relevance_score = _decimal_score(output.relevance_score)
    analysis.urgency_score = _decimal_score(output.urgency_score)
    analysis.importance_tier = output.importance_tier.value if output.importance_tier else None
    analysis.suggested_action = output.suggested_action
    analysis.affected_business_area = output.affected_business_area
    analysis.confidence_score = _decimal_score(output.confidence_score)
    analysis.model_name = response.model_name
    analysis.prompt_version = PROMPT_VERSION
    analysis.prompt_tokens = response.usage.prompt_tokens
    analysis.completion_tokens = response.usage.completion_tokens
    analysis.total_tokens = response.usage.total_tokens
    analysis.estimated_cost = _estimate_cost(response.usage, settings)
    analysis.status = EventAIAnalysisStatus.SUCCESS.value
    analysis.error_message = None
    metadata = {
        **(analysis.analysis_metadata or {}),
        "scoring": {
            "importance_tier_source": "model_or_service_fallback",
            "scores_clamped": True,
        },
        "briefing": _briefing_metadata_from_output(output),
    }
    metadata.pop("error_detail", None)
    metadata.pop("raw_model_preview", None)
    analysis.analysis_metadata = metadata


def _apply_traceability(analysis: EventAIAnalysis, context) -> None:
    analysis.source_article_ids = context.source_article_ids
    analysis.source_urls = context.source_urls
    analysis.primary_article_id = context.primary_article_id
    analysis.context_article_count = context.context_article_count
    analysis.analysis_metadata = {
        **(analysis.analysis_metadata or {}),
        **context.metadata,
    }


def _apply_failed(
    analysis: EventAIAnalysis,
    reason: str,
    *,
    detail: str | None = None,
    raw_preview: str | None = None,
) -> None:
    analysis.status = EventAIAnalysisStatus.FAILED.value
    analysis.error_message = reason
    metadata = {
        **(analysis.analysis_metadata or {}),
        "error_detail": detail,
    }
    if raw_preview:
        metadata["raw_model_preview"] = raw_preview
    analysis.analysis_metadata = metadata


def _apply_skipped(analysis: EventAIAnalysis, reason: str) -> None:
    analysis.status = EventAIAnalysisStatus.SKIPPED.value
    analysis.error_message = reason


def _briefing_metadata_from_output(output: EventAIModelOutput) -> dict:
    return {
        "briefing_section": output.briefing_section,
        "category": output.category,
        "country_or_region": output.country_or_region,
        "urgency": output.urgency,
        "suggested_owner": output.suggested_owner,
        "action_bucket": output.action_bucket,
        "why_it_matters_to_wdts": output.why_it_matters_to_wdts,
        "signal_type": output.signal_type,
    }


def _apply_analysis_filters(query: Select, filters: dict) -> Select:
    if filters["source_id"] is not None:
        query = (
            query.join(NewsEvent, NewsEvent.id == EventAIAnalysis.event_id)
            .join(EventArticle, EventArticle.event_id == NewsEvent.id)
            .where(EventArticle.source_id == filters["source_id"])
        )
    elif filters["category"] is not None or filters["region"] is not None:
        query = query.join(NewsEvent, NewsEvent.id == EventAIAnalysis.event_id)
    if filters["status"] is not None:
        query = query.where(EventAIAnalysis.status == filters["status"])
    if filters["importance_tier"] is not None:
        query = query.where(EventAIAnalysis.importance_tier == filters["importance_tier"])
    if filters["min_relevance_score"] is not None:
        query = query.where(EventAIAnalysis.relevance_score >= filters["min_relevance_score"])
    if filters["min_urgency_score"] is not None:
        query = query.where(EventAIAnalysis.urgency_score >= filters["min_urgency_score"])
    if filters["category"] is not None:
        query = query.where(NewsEvent.category == filters["category"])
    if filters["region"] is not None:
        query = query.where(NewsEvent.region == filters["region"])
    if filters["created_from"] is not None:
        query = query.where(EventAIAnalysis.created_at >= filters["created_from"])
    if filters["created_to"] is not None:
        query = query.where(EventAIAnalysis.created_at <= filters["created_to"])
    return query


def _decimal_score(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(max(0.0, min(1.0, value)), 3)))


def _estimate_cost(usage, settings: Settings) -> Decimal:
    input_cost = (usage.prompt_tokens / 1000) * settings.AI_ESTIMATED_INPUT_COST_PER_1K_TOKENS
    output_cost = (
        usage.completion_tokens / 1000
    ) * settings.AI_ESTIMATED_OUTPUT_COST_PER_1K_TOKENS
    return Decimal(str(round(input_cost + output_cost, 6)))
