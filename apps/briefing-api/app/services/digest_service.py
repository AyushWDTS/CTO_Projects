from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.digest import Digest, DigestItem, DigestSection, DigestStatus
from app.models.event import EventArticle, EventStatus, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus, ImportanceTier
from app.schemas.digest import DigestPreview, DigestPreviewItem
from app.services.briefing_text_service import distinct_summary
from app.services.digest_ranking_service import (
    DEFAULT_MIN_SCORE,
    RANKING_VERSION,
    DigestCandidate,
    decimal_score,
    flatten_coo_metadata,
    mark_top_five_candidates,
    score_digest_candidate,
    score_fallback_digest_candidate,
    select_ranked_candidates,
)
from app.services.digest_selection_audit import DigestSelectionAudit
from app.services.wdts_relevance_service import assess_wdts_relevance

DEFAULT_DIGEST_LIMIT = 15
MAX_DIGEST_BUILD_LIMIT = 50
DEFAULT_DIGEST_LIST_LIMIT = 50
MAX_DIGEST_LIST_LIMIT = 500


class DigestNotFoundError(Exception):
    pass


class InvalidDigestWindowError(Exception):
    pass


def normalize_digest_build_limit(limit: int) -> int:
    return max(1, min(limit, MAX_DIGEST_BUILD_LIMIT))


def normalize_digest_list_limit(limit: int) -> int:
    return max(1, min(limit, MAX_DIGEST_LIST_LIMIT))


def build_digest(
    db: Session,
    *,
    digest_date: date | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    limit: int = DEFAULT_DIGEST_LIMIT,
    category: str | None = None,
    region: str | None = None,
    min_score: float | None = DEFAULT_MIN_SCORE,
    include_low: bool = False,
    monitor_limit: int | None = None,
    refresh: bool = False,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
    now: datetime | None = None,
) -> Digest:
    resolved_date, resolved_start, resolved_end = resolve_digest_window(
        digest_date=digest_date,
        window_start=window_start,
        window_end=window_end,
        now=now,
    )
    build_limit = normalize_digest_build_limit(limit)
    existing = _get_digest_for_window(db, resolved_date, resolved_start, resolved_end, lock=refresh)
    if existing is not None and not refresh:
        _load_digest_items(existing)
        if not _should_rebuild_empty_digest(
            db,
            existing,
            category=category,
            region=region,
            min_score=min_score,
        ):
            if _backfill_digest_item_coo_metadata(existing):
                db.commit()
                db.refresh(existing)
                _load_digest_items(existing)
            return existing

    digest = existing or Digest(
        digest_date=resolved_date,
        window_start=resolved_start,
        window_end=resolved_end,
        title=_digest_title(resolved_date),
        status=DigestStatus.DRAFT.value,
    )
    if existing is None:
        db.add(digest)
        db.flush()

    _rebuild_digest_items(
        db,
        digest,
        limit=build_limit,
        category=category,
        region=region,
        min_score=min_score,
        include_low=include_low,
        monitor_limit=monitor_limit,
        fetched_after=fetched_after,
        fetched_after_inclusive=fetched_after_inclusive,
    )
    db.commit()
    db.refresh(digest)
    _load_digest_items(digest)
    return digest


def preview_digest(
    db: Session,
    *,
    digest_date: date | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    limit: int = DEFAULT_DIGEST_LIMIT,
    category: str | None = None,
    region: str | None = None,
    min_score: float | None = DEFAULT_MIN_SCORE,
    include_low: bool = False,
    now: datetime | None = None,
) -> DigestPreview:
    resolved_date, resolved_start, resolved_end = resolve_digest_window(
        digest_date=digest_date,
        window_start=window_start,
        window_end=window_end,
        now=now,
    )
    build_limit = normalize_digest_build_limit(limit)
    candidates = select_digest_candidates(
        db,
        window_start=resolved_start,
        window_end=resolved_end,
        category=category,
        region=region,
        min_score=min_score,
    )
    selected = select_ranked_candidates(candidates, limit=build_limit, include_low=include_low)
    metadata = _build_metadata(
        limit=build_limit,
        include_low=include_low,
        category=category,
        region=region,
        min_score=min_score,
        window_start=resolved_start,
        window_end=resolved_end,
    )
    counts = _tier_counts(selected)
    return DigestPreview(
        digest_date=resolved_date,
        window_start=resolved_start,
        window_end=resolved_end,
        title=_digest_title(resolved_date),
        total_candidates=len(candidates),
        total_selected=len(selected),
        critical_count=counts["critical"],
        important_count=counts["important"],
        monitor_count=counts["monitor"],
        metadata=metadata,
        items=[_preview_item(candidate, rank) for rank, candidate in enumerate(selected, start=1)],
    )


def refresh_digest(db: Session, digest_id: UUID) -> Digest:
    digest = db.scalar(select(Digest).where(Digest.id == digest_id).with_for_update())
    if digest is None:
        raise DigestNotFoundError("Digest not found.")

    metadata = digest.digest_metadata or {}
    _rebuild_digest_items(
        db,
        digest,
        limit=normalize_digest_build_limit(int(metadata.get("limit", DEFAULT_DIGEST_LIMIT))),
        category=metadata.get("category"),
        region=metadata.get("region"),
        min_score=metadata.get("min_score"),
        include_low=bool(metadata.get("include_low", False)),
    )
    db.commit()
    db.refresh(digest)
    _load_digest_items(digest)
    return digest


def get_digest(db: Session, digest_id: UUID) -> Digest:
    digest = db.get(Digest, digest_id)
    if digest is None:
        raise DigestNotFoundError("Digest not found.")
    _load_digest_items(digest)
    return digest


def list_digests(
    db: Session,
    *,
    limit: int,
    offset: int,
    status: DigestStatus | None = None,
    digest_date: date | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> tuple[list[Digest], int]:
    filters = {
        "status": status,
        "digest_date": digest_date,
        "created_from": created_from,
        "created_to": created_to,
    }
    query = _apply_digest_filters(select(Digest), filters).order_by(
        Digest.digest_date.desc(),
        Digest.created_at.desc(),
    )
    count_query = _apply_digest_filters(select(func.count(Digest.id)), filters)
    normalized_limit = normalize_digest_list_limit(limit)
    total = db.scalar(count_query) or 0
    rows = list(db.scalars(query.limit(normalized_limit).offset(offset)))
    return rows, total


def list_digest_items(
    db: Session,
    digest_id: UUID,
    *,
    limit: int,
    offset: int,
    section: str | None = None,
    importance_tier: ImportanceTier | None = None,
    min_score: float | None = DEFAULT_MIN_SCORE,
) -> tuple[list[DigestItem], int]:
    get_digest(db, digest_id)
    filters = {
        "digest_id": digest_id,
        "section": section,
        "importance_tier": importance_tier.value if importance_tier else None,
        "min_score": min_score,
    }
    query = _apply_digest_item_filters(select(DigestItem), filters).order_by(DigestItem.rank.asc())
    count_query = _apply_digest_item_filters(select(func.count(DigestItem.id)), filters)
    normalized_limit = normalize_digest_list_limit(limit)
    total = db.scalar(count_query) or 0
    rows = list(db.scalars(query.limit(normalized_limit).offset(offset)))
    return rows, total


def select_digest_candidates(
    db: Session,
    *,
    window_start: datetime,
    window_end: datetime,
    category: str | None = None,
    region: str | None = None,
    min_score: float | None = DEFAULT_MIN_SCORE,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
    audit: DigestSelectionAudit | None = None,
) -> list[DigestCandidate]:
    timestamp_expr = func.coalesce(
        NewsEvent.published_at,
        NewsEvent.first_seen_at,
        NewsEvent.created_at,
    )
    query = (
        select(NewsEvent, EventAIAnalysis)
        .join(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
        .options(joinedload(NewsEvent.primary_source))
        .where(NewsEvent.status == EventStatus.ACTIVE)
        .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value)
        .where(timestamp_expr >= window_start)
        .where(timestamp_expr < window_end)
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
    if category is not None:
        query = query.where(NewsEvent.category == category)
    if region is not None:
        query = query.where(NewsEvent.region == region)

    candidates = []
    has_ai_rows = False
    for event, analysis in db.execute(query).all():
        has_ai_rows = True
        event_timestamp = _event_timestamp(event)
        candidate = score_digest_candidate(
            event,
            analysis,
            event_timestamp=event_timestamp,
            window_start=window_start,
            window_end=window_end,
        )
        verdict = assess_wdts_relevance(event, analysis)
        headline = analysis.short_summary or event.canonical_title or ""
        source = event.primary_source
        if audit is not None:
            audit.record_gate(
                event_id=event.id,
                headline=headline,
                eligible=verdict.is_eligible,
                reason=verdict.reject_reason or "passed_wdts_gate",
                source_id=source.id if source else None,
                source_name=source.name if source else None,
                wdts_relevance_score=verdict.wdts_relevance_score,
                ai_relevance_score=(
                    float(analysis.relevance_score)
                    if analysis.relevance_score is not None
                    else None
                ),
                domain_hits=verdict.domain_hits,
                importance_tier=analysis.importance_tier,
            )
        if not verdict.is_eligible:
            continue
        if min_score is None or candidate.final_score >= min_score:
            candidates.append(candidate)
    if has_ai_rows:
        return candidates
    return _select_fallback_digest_candidates(
        db,
        window_start=window_start,
        window_end=window_end,
        category=category,
        region=region,
        min_score=min_score,
        fetched_after=fetched_after,
        fetched_after_inclusive=fetched_after_inclusive,
        audit=audit,
    )


def _select_fallback_digest_candidates(
    db: Session,
    *,
    window_start: datetime,
    window_end: datetime,
    category: str | None,
    region: str | None,
    min_score: float | None,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
    audit: DigestSelectionAudit | None = None,
) -> list[DigestCandidate]:
    timestamp_expr = func.coalesce(
        NewsEvent.published_at,
        NewsEvent.first_seen_at,
        NewsEvent.created_at,
    )
    query = (
        select(NewsEvent)
        .join(EventArticle, EventArticle.event_id == NewsEvent.id)
        .options(
            joinedload(NewsEvent.primary_source),
            joinedload(NewsEvent.primary_article),
            joinedload(NewsEvent.event_articles).joinedload(EventArticle.article),
        )
        .where(NewsEvent.status == EventStatus.ACTIVE)
        .where(timestamp_expr >= window_start)
        .where(timestamp_expr < window_end)
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
    if category is not None:
        query = query.where(NewsEvent.category == category)
    if region is not None:
        query = query.where(NewsEvent.region == region)

    candidates = []
    for event in db.scalars(query).unique().all():
        event_timestamp = _event_timestamp(event)
        candidate = score_fallback_digest_candidate(
            event,
            event_timestamp=event_timestamp,
            window_start=window_start,
            window_end=window_end,
        )
        verdict = assess_wdts_relevance(event, candidate.analysis)
        headline = candidate.analysis.short_summary or event.canonical_title or ""
        source = event.primary_source
        if audit is not None:
            audit.record_gate(
                event_id=event.id,
                headline=headline,
                eligible=verdict.is_eligible,
                reason=verdict.reject_reason or "passed_wdts_gate",
                source_id=source.id if source else None,
                source_name=source.name if source else None,
                wdts_relevance_score=verdict.wdts_relevance_score,
                ai_relevance_score=(
                    float(candidate.analysis.relevance_score)
                    if candidate.analysis.relevance_score is not None
                    else None
                ),
                domain_hits=verdict.domain_hits,
                importance_tier=candidate.analysis.importance_tier,
            )
        if not verdict.is_eligible:
            continue
        if min_score is None or candidate.final_score >= min_score:
            candidates.append(candidate)
    return candidates


def resolve_digest_window(
    *,
    digest_date: date | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    now: datetime | None = None,
) -> tuple[date, datetime, datetime]:
    if window_start is not None or window_end is not None:
        if window_start is None or window_end is None:
            raise InvalidDigestWindowError("Both window_start and window_end are required.")
        start = _ensure_utc(window_start)
        end = _ensure_utc(window_end)
        if start >= end:
            raise InvalidDigestWindowError("window_start must be before window_end.")
        target_date = digest_date or start.date()
        return target_date, start, end

    target_date = digest_date or _ensure_utc(now or datetime.now(UTC)).date()
    start = datetime.combine(target_date, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return target_date, start, end


def _rebuild_digest_items(
    db: Session,
    digest: Digest,
    *,
    limit: int,
    category: str | None,
    region: str | None,
    min_score: float | None,
    include_low: bool,
    monitor_limit: int | None = None,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
) -> None:
    db.execute(delete(DigestItem).where(DigestItem.digest_id == digest.id))
    audit = DigestSelectionAudit()
    candidates = select_digest_candidates(
        db,
        window_start=digest.window_start,
        window_end=digest.window_end,
        category=category,
        region=region,
        min_score=min_score,
        fetched_after=fetched_after,
        fetched_after_inclusive=fetched_after_inclusive,
        audit=audit,
    )
    from app.services.digest_ranking_service import MONITOR_TIER_CAP, select_ranked_candidates

    selected = select_ranked_candidates(
        candidates,
        limit=limit,
        include_low=include_low,
        monitor_limit=monitor_limit if monitor_limit is not None else MONITOR_TIER_CAP,
        audit=audit,
    )
    mark_top_five_candidates(selected)
    counts = _tier_counts(selected)

    digest.title = _digest_title(digest.digest_date)
    digest.total_candidates = len(candidates)
    digest.total_selected = len(selected)
    digest.critical_count = counts["critical"]
    digest.important_count = counts["important"]
    digest.monitor_count = counts["monitor"]
    metadata = _build_metadata(
        limit=limit,
        include_low=include_low,
        category=category,
        region=region,
        min_score=min_score,
        window_start=digest.window_start,
        window_end=digest.window_end,
    )
    metadata["selection_audit"] = audit.to_dict()
    digest.digest_metadata = metadata
    db.flush()

    for rank, candidate in enumerate(selected, start=1):
        db.add(_digest_item_from_candidate(digest.id, candidate, rank))
    db.flush()


def _should_rebuild_empty_digest(
    db: Session,
    digest: Digest,
    *,
    category: str | None,
    region: str | None,
    min_score: float | None,
) -> bool:
    if digest.status != DigestStatus.DRAFT.value:
        return False
    if digest.total_candidates or digest.total_selected or digest.items:
        return False

    candidates = select_digest_candidates(
        db,
        window_start=digest.window_start,
        window_end=digest.window_end,
        category=category,
        region=region,
        min_score=min_score,
    )
    return bool(candidates)


def _digest_item_from_candidate(
    digest_id: UUID,
    candidate: DigestCandidate,
    rank: int,
) -> DigestItem:
    analysis = candidate.analysis
    headline = analysis.short_summary or candidate.event.canonical_title
    key_point_fallback = None
    if analysis.key_points:
        first_point = analysis.key_points[0]
        if isinstance(first_point, str) and first_point.strip():
            key_point_fallback = first_point.strip()
    return DigestItem(
        digest_id=digest_id,
        event_id=candidate.event.id,
        event_ai_analysis_id=analysis.id,
        rank=rank,
        section=candidate.section.value,
        final_score=decimal_score(candidate.final_score),
        relevance_score=decimal_score(candidate.relevance_score),
        urgency_score=decimal_score(candidate.urgency_score),
        source_authority_score=decimal_score(candidate.source_authority_score),
        recency_score=decimal_score(candidate.recency_score),
        business_impact_score=decimal_score(candidate.business_impact_score),
        importance_tier=analysis.importance_tier,
        headline=headline,
        summary=distinct_summary(headline, analysis.summary, fallback=key_point_fallback),
        why_it_matters=analysis.why_it_matters,
        suggested_action=analysis.suggested_action,
        source_urls=analysis.source_urls,
        item_metadata=flatten_coo_metadata(candidate.metadata),
    )


def _backfill_digest_item_coo_metadata(digest: Digest) -> bool:
    changed = False
    for item in digest.items:
        flattened = flatten_coo_metadata(item.item_metadata)
        if flattened != (item.item_metadata or {}):
            item.item_metadata = flattened
            changed = True
    return changed


def _preview_item(candidate: DigestCandidate, rank: int) -> DigestPreviewItem:
    item = _digest_item_from_candidate(UUID(int=0), candidate, rank)
    return DigestPreviewItem(
        event_id=item.event_id,
        event_ai_analysis_id=item.event_ai_analysis_id,
        rank=item.rank,
        section=DigestSection(item.section),
        final_score=item.final_score,
        relevance_score=item.relevance_score,
        urgency_score=item.urgency_score,
        source_authority_score=item.source_authority_score,
        recency_score=item.recency_score,
        business_impact_score=item.business_impact_score,
        importance_tier=item.importance_tier,
        headline=item.headline,
        summary=item.summary,
        why_it_matters=item.why_it_matters,
        suggested_action=item.suggested_action,
        source_urls=item.source_urls,
        metadata=item.item_metadata,
    )


def _get_digest_for_window(
    db: Session,
    digest_date: date,
    window_start: datetime,
    window_end: datetime,
    *,
    lock: bool,
) -> Digest | None:
    query = select(Digest).where(
        Digest.digest_date == digest_date,
        Digest.window_start == window_start,
        Digest.window_end == window_end,
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _load_digest_items(digest: Digest) -> None:
    _ = digest.items


def _apply_digest_filters(query: Select, filters: dict) -> Select:
    if filters["status"] is not None:
        query = query.where(Digest.status == filters["status"])
    if filters["digest_date"] is not None:
        query = query.where(Digest.digest_date == filters["digest_date"])
    if filters["created_from"] is not None:
        query = query.where(Digest.created_at >= _ensure_utc(filters["created_from"]))
    if filters["created_to"] is not None:
        query = query.where(Digest.created_at <= _ensure_utc(filters["created_to"]))
    return query


def _apply_digest_item_filters(query: Select, filters: dict) -> Select:
    query = query.where(DigestItem.digest_id == filters["digest_id"])
    if filters["section"] is not None:
        query = query.where(DigestItem.section == filters["section"])
    if filters["importance_tier"] is not None:
        query = query.where(DigestItem.importance_tier == filters["importance_tier"])
    if filters["min_score"] is not None:
        query = query.where(DigestItem.final_score >= filters["min_score"])
    return query


def _build_metadata(
    *,
    limit: int,
    include_low: bool,
    category: str | None,
    region: str | None,
    min_score: float | None,
    window_start: datetime,
    window_end: datetime,
) -> dict:
    return {
        "ranking_version": RANKING_VERSION,
        "limit": limit,
        "include_low": include_low,
        "category": category,
        "region": region,
        "min_score": min_score,
        "window_start": _isoformat_utc(window_start),
        "window_end": _isoformat_utc(window_end),
    }


def _tier_counts(candidates: list[DigestCandidate]) -> dict[str, int]:
    return {
        "critical": sum(1 for item in candidates if item.analysis.importance_tier == "critical"),
        "important": sum(1 for item in candidates if item.analysis.importance_tier == "important"),
        "monitor": sum(1 for item in candidates if item.analysis.importance_tier == "monitor"),
    }


def _event_timestamp(event: NewsEvent) -> datetime:
    value = event.published_at or event.first_seen_at or event.created_at
    return _ensure_utc(value)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _isoformat_utc(value: datetime) -> str:
    return _ensure_utc(value).isoformat()


def _digest_title(digest_date: date) -> str:
    return f"WDTS Daily News Digest – {digest_date.isoformat()}"
