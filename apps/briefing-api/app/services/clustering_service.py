from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.article import Article, ArticleExtractionStatus
from app.models.event import EventArticle, EventArticleMatchType, EventStatus, NewsEvent
from app.models.source import Source
from app.schemas.clustering import ArticleClusteringResult, ClusteringBatchResult
from app.services.similarity_service import (
    MINIMUM_CLUSTER_CONFIDENCE,
    TEXT_SIMILARITY_THRESHOLD,
    TITLE_SIMILARITY_THRESHOLD,
    SimilarityScores,
    compare_article_text,
    hash_value,
    normalize_text,
    normalize_url,
)

DEFAULT_CLUSTERING_LIMIT = 100
MAX_CLUSTERING_LIMIT = 500
RECENT_EVENT_WINDOW_DAYS = 14


class ArticleNotFoundError(Exception):
    pass


class NewsEventNotFoundError(Exception):
    pass


class ArticleNotClusterableError(Exception):
    pass


class MatchCandidate:
    def __init__(
        self,
        *,
        event: NewsEvent,
        match_type: EventArticleMatchType,
        similarity_score: float,
        confidence_score: float,
        details: dict,
        created_event: bool = False,
    ) -> None:
        self.event = event
        self.match_type = match_type
        self.similarity_score = similarity_score
        self.confidence_score = confidence_score
        self.details = details
        self.created_event = created_event


def normalize_event_limit(limit: int) -> int:
    return max(1, min(limit, MAX_CLUSTERING_LIMIT))


def cluster_article(
    db: Session,
    article_id: UUID,
    *,
    reprocess: bool = False,
) -> ArticleClusteringResult:
    article = _get_article(db, article_id)
    if article.extraction_status != ArticleExtractionStatus.SUCCESS:
        return ArticleClusteringResult(
            article_id=article.id,
            source_id=article.source_id,
            status="skipped",
            reason="article_not_successful",
        )

    existing_link = _get_event_article_for_article(db, article.id)
    if existing_link is not None and not reprocess:
        return ArticleClusteringResult(
            article_id=article.id,
            source_id=article.source_id,
            status="already_clustered",
            event_id=existing_link.event_id,
            event_status=existing_link.event.status,
            match_type=existing_link.match_type,
            similarity_score=float(existing_link.similarity_score),
            confidence_score=float(existing_link.confidence_score),
        )

    if existing_link is not None:
        _detach_article(db, existing_link)

    candidate = _find_best_match(db, article)
    event = candidate.event
    if candidate.created_event:
        db.add(event)
        db.flush()

    link = EventArticle(
        event_id=event.id,
        article_id=article.id,
        source_id=article.source_id,
        match_type=candidate.match_type,
        similarity_score=_decimal_score(candidate.similarity_score),
        confidence_score=_decimal_score(candidate.confidence_score),
        is_primary=False,
        match_details=candidate.details,
    )
    db.add(link)
    db.flush()
    _refresh_event_aggregates(db, event.id)
    db.commit()
    db.refresh(event)
    db.refresh(link)

    return ArticleClusteringResult(
        article_id=article.id,
        source_id=article.source_id,
        status="clustered",
        event_id=event.id,
        event_status=event.status,
        match_type=link.match_type,
        similarity_score=float(link.similarity_score),
        confidence_score=float(link.confidence_score),
        created_event=candidate.created_event,
        updated_event=not candidate.created_event,
    )


def cluster_pending_articles(
    db: Session,
    *,
    limit: int = DEFAULT_CLUSTERING_LIMIT,
    reprocess: bool = False,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
) -> ClusteringBatchResult:
    normalized_limit = normalize_event_limit(limit)
    query = (
        select(Article)
        .options(joinedload(Article.source))
        .outerjoin(EventArticle, EventArticle.article_id == Article.id)
        .where(Article.extraction_status == ArticleExtractionStatus.SUCCESS)
        .order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())
        .limit(normalized_limit)
    )
    if not reprocess:
        query = query.where(EventArticle.id.is_(None))
    if fetched_after is not None:
        from app.services.demo_pipeline_service import apply_article_fetched_after

        query = apply_article_fetched_after(
            query,
            fetched_after,
            inclusive=fetched_after_inclusive,
        )

    articles = list(db.scalars(query))
    return _cluster_batch(db, articles, reprocess=reprocess)


def cluster_by_source(
    db: Session,
    source_id: UUID,
    *,
    limit: int = DEFAULT_CLUSTERING_LIMIT,
    reprocess: bool = False,
) -> ClusteringBatchResult:
    normalized_limit = normalize_event_limit(limit)
    query = (
        select(Article)
        .options(joinedload(Article.source))
        .outerjoin(EventArticle, EventArticle.article_id == Article.id)
        .where(Article.source_id == source_id)
        .where(Article.extraction_status == ArticleExtractionStatus.SUCCESS)
        .order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())
        .limit(normalized_limit)
    )
    if not reprocess:
        query = query.where(EventArticle.id.is_(None))

    articles = list(db.scalars(query))
    return _cluster_batch(db, articles, reprocess=reprocess)


def get_event(db: Session, event_id: UUID) -> NewsEvent:
    event = db.get(NewsEvent, event_id)
    if event is None:
        raise NewsEventNotFoundError("News event not found.")
    return event


def list_events(
    db: Session,
    *,
    limit: int,
    offset: int,
    category: str | None = None,
    region: str | None = None,
    status: EventStatus | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    source_id: UUID | None = None,
    min_confidence: float | None = None,
) -> tuple[list[NewsEvent], int]:
    filters = {
        "category": category,
        "region": region,
        "status": status,
        "published_from": published_from,
        "published_to": published_to,
        "source_id": source_id,
        "min_confidence": min_confidence,
    }
    query = _apply_event_filters(select(NewsEvent), filters).order_by(
        NewsEvent.published_at.desc().nullslast(),
        NewsEvent.created_at.desc(),
    )
    count_query = _apply_event_filters(select(func.count(distinct(NewsEvent.id))), filters)
    if source_id is not None:
        query = query.distinct()

    total = db.scalar(count_query) or 0
    events = list(db.scalars(query.limit(limit).offset(offset)))
    return events, total


def list_event_articles(
    db: Session,
    event_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[EventArticle], int]:
    get_event(db, event_id)
    total = (
        db.scalar(select(func.count(EventArticle.id)).where(EventArticle.event_id == event_id)) or 0
    )
    rows = list(
        db.scalars(
            select(EventArticle)
            .where(EventArticle.event_id == event_id)
            .order_by(EventArticle.is_primary.desc(), EventArticle.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
    )
    return rows, total


def _cluster_batch(
    db: Session,
    articles: list[Article],
    *,
    reprocess: bool,
) -> ClusteringBatchResult:
    results = [cluster_article(db, article.id, reprocess=reprocess) for article in articles]
    return ClusteringBatchResult(
        total_articles=len(articles),
        created_events=sum(1 for result in results if result.created_event),
        updated_events=sum(1 for result in results if result.updated_event),
        linked_articles=sum(
            1 for result in results if result.status in {"clustered", "already_clustered"}
        ),
        skipped_articles=sum(1 for result in results if result.status == "skipped"),
        results=results,
    )


def _find_best_match(db: Session, article: Article) -> MatchCandidate:
    return (
        _find_exact_url_match(db, article)
        or _find_exact_source_url_match(db, article)
        or _find_exact_hash_match(db, article)
        or _find_near_duplicate_match(db, article)
        or _create_event_candidate(article)
    )


def _find_exact_url_match(db: Session, article: Article) -> MatchCandidate | None:
    normalized_url = normalize_url(article.canonical_url)
    if not normalized_url:
        return None

    event = db.scalar(
        select(NewsEvent)
        .where(NewsEvent.status == EventStatus.ACTIVE)
        .where(NewsEvent.normalized_canonical_url == normalized_url)
        .order_by(NewsEvent.created_at.asc())
    )
    if event is None:
        return None

    return MatchCandidate(
        event=event,
        match_type=EventArticleMatchType.EXACT_URL,
        similarity_score=1.0,
        confidence_score=1.0,
        details={
            "normalized_article_canonical_url": normalized_url,
            "normalized_event_canonical_url": event.normalized_canonical_url,
            "threshold": 1.0,
        },
    )


def _find_exact_source_url_match(db: Session, article: Article) -> MatchCandidate | None:
    if normalize_url(article.canonical_url):
        return None
    normalized_source_url = normalize_url(article.source_url)
    if not normalized_source_url:
        return None

    candidates = _recent_event_links(db, article, require_recent=False)
    for link in candidates:
        candidate_source_url = normalize_url(link.article.source_url)
        if candidate_source_url == normalized_source_url:
            return MatchCandidate(
                event=link.event,
                match_type=EventArticleMatchType.EXACT_SOURCE_URL,
                similarity_score=1.0,
                confidence_score=1.0,
                details={
                    "normalized_article_source_url": normalized_source_url,
                    "normalized_candidate_source_url": candidate_source_url,
                    "threshold": 1.0,
                },
            )
    return None


def _find_exact_hash_match(db: Session, article: Article) -> MatchCandidate | None:
    if not article.content_hash:
        return None

    candidates = _recent_event_links(db, article, content_hash=article.content_hash)
    for link in candidates:
        guard_details = _hash_guard_details(article, link.article)
        if guard_details["category_region_conflict"]:
            continue
        if not guard_details["within_time_window"] and not guard_details["time_signal_missing"]:
            continue

        return MatchCandidate(
            event=link.event,
            match_type=EventArticleMatchType.EXACT_HASH,
            similarity_score=1.0,
            confidence_score=1.0,
            details={
                "content_hash": article.content_hash,
                "threshold": 1.0,
                **guard_details,
            },
        )
    return None


def _find_near_duplicate_match(db: Session, article: Article) -> MatchCandidate | None:
    best: MatchCandidate | None = None
    for link in _recent_event_links(db, article):
        candidate_article = link.article
        scores = compare_article_text(
            article.title,
            article.clean_text,
            candidate_article.title,
            candidate_article.clean_text,
        )
        candidate = _candidate_from_scores(article, link.event, scores)
        if candidate is None:
            continue
        if best is None or candidate.confidence_score > best.confidence_score:
            best = candidate
    return best


def _candidate_from_scores(
    article: Article,
    event: NewsEvent,
    scores: SimilarityScores,
) -> MatchCandidate | None:
    if scores.best_title_score >= TITLE_SIMILARITY_THRESHOLD:
        match_type = EventArticleMatchType.TITLE_SIMILARITY
        similarity = scores.best_title_score
        threshold = TITLE_SIMILARITY_THRESHOLD
    elif scores.text_token_score >= TEXT_SIMILARITY_THRESHOLD:
        match_type = EventArticleMatchType.TEXT_SIMILARITY
        similarity = scores.text_token_score
        threshold = TEXT_SIMILARITY_THRESHOLD
    else:
        return None

    category_signal, region_signal = _category_region_signals(article.source, event)
    confidence = min(1.0, similarity + category_signal + region_signal)
    if confidence < MINIMUM_CLUSTER_CONFIDENCE:
        return None

    return MatchCandidate(
        event=event,
        match_type=match_type,
        similarity_score=similarity,
        confidence_score=confidence,
        details={
            "title_sequence_score": round(scores.title_sequence_score, 3),
            "title_token_score": round(scores.title_token_score, 3),
            "text_token_score": round(scores.text_token_score, 3),
            "threshold": threshold,
            "minimum_confidence": MINIMUM_CLUSTER_CONFIDENCE,
            "category_signal": category_signal,
            "region_signal": region_signal,
        },
    )


def _create_event_candidate(article: Article) -> MatchCandidate:
    normalized_canonical_url = normalize_url(article.canonical_url)
    event = NewsEvent(
        canonical_title=article.title,
        canonical_url=article.canonical_url or article.source_url,
        normalized_canonical_url=normalized_canonical_url,
        primary_article_id=article.id,
        primary_source_id=article.source_id,
        event_key=_build_event_key(article),
        category=article.source.category if article.source else None,
        region=article.source.region if article.source else None,
        published_at=article.published_at,
        first_seen_at=_article_reference_time(article),
        last_seen_at=_article_reference_time(article),
        article_count=0,
        source_count=0,
        status=EventStatus.ACTIVE,
        confidence_score=Decimal("0.000"),
        event_metadata={
            "normalized_source_url": normalize_url(article.source_url),
            "created_from_article_id": str(article.id),
        },
    )
    return MatchCandidate(
        event=event,
        match_type=EventArticleMatchType.MANUAL,
        similarity_score=1.0,
        confidence_score=1.0,
        details={
            "reason": "new_event",
            "normalized_canonical_url": normalized_canonical_url,
            "normalized_source_url": normalize_url(article.source_url),
        },
        created_event=True,
    )


def _build_event_key(article: Article) -> str:
    normalized_canonical_url = normalize_url(article.canonical_url)
    if normalized_canonical_url:
        return f"url:{hash_value(normalized_canonical_url)[:64]}"

    normalized_source_url = normalize_url(article.source_url)
    if normalized_source_url:
        return f"source_url:{hash_value(normalized_source_url)[:57]}"

    if article.content_hash:
        return f"hash:{article.content_hash[:64]}"

    source = article.source
    date_bucket = (_article_reference_time(article) or datetime.now(UTC)).date().isoformat()
    fallback = "|".join(
        [
            normalize_text(article.title),
            date_bucket,
            source.category if source and source.category else "",
            source.region if source and source.region else "",
        ]
    )
    return f"title:{hash_value(fallback)[:62]}"


def _detach_article(db: Session, link: EventArticle) -> None:
    event_id = link.event_id
    event_status = link.event.status
    db.delete(link)
    db.flush()

    remaining = (
        db.scalar(select(func.count(EventArticle.id)).where(EventArticle.event_id == event_id)) or 0
    )
    if remaining == 0:
        event = db.get(NewsEvent, event_id)
        if event is not None and event_status != EventStatus.ARCHIVED:
            db.delete(event)
            db.flush()
        elif event is not None:
            event.article_count = 0
            event.source_count = 0
            event.primary_article_id = None
            event.primary_source_id = None
            db.flush()
        return

    _refresh_event_aggregates(db, event_id)


def _refresh_event_aggregates(db: Session, event_id: UUID) -> None:
    event = db.get(NewsEvent, event_id)
    if event is None:
        return

    links = list(
        db.scalars(
            select(EventArticle)
            .options(joinedload(EventArticle.article).joinedload(Article.source))
            .where(EventArticle.event_id == event_id)
            .order_by(EventArticle.created_at.asc())
        )
    )
    if not links:
        event.article_count = 0
        event.source_count = 0
        event.primary_article_id = None
        event.primary_source_id = None
        db.flush()
        return

    primary_link = max(links, key=_primary_sort_key)
    for link in links:
        link.is_primary = False
    db.flush()
    primary_link.is_primary = True

    primary_article = primary_link.article
    primary_source = primary_article.source
    reference_times = [_article_reference_time(link.article) for link in links]
    reference_times = [value for value in reference_times if value is not None]

    event.primary_article_id = primary_article.id
    event.primary_source_id = primary_article.source_id
    event.canonical_title = primary_article.title
    event.canonical_url = primary_article.canonical_url or primary_article.source_url
    event.normalized_canonical_url = normalize_url(primary_article.canonical_url)
    event.category = primary_source.category if primary_source else None
    event.region = primary_source.region if primary_source else None
    event.published_at = primary_article.published_at
    event.first_seen_at = min(reference_times) if reference_times else None
    event.last_seen_at = max(reference_times) if reference_times else None
    event.article_count = len(links)
    event.source_count = len({link.source_id for link in links})
    event.confidence_score = _decimal_score(
        sum(float(link.confidence_score) for link in links) / len(links)
    )
    event.event_metadata = {
        **(event.event_metadata or {}),
        "normalized_source_url": normalize_url(primary_article.source_url),
        "primary_selection_rule": "reliability_priority_content_earliest",
    }
    db.flush()


def _primary_sort_key(link: EventArticle) -> tuple:
    article = link.article
    source = article.source
    reliability = float(source.reliability_score) if source else 0.0
    priority = source.priority if source else 5
    has_content = bool(article.title and article.clean_text)
    article_time = _article_reference_time(article) or datetime.max.replace(tzinfo=UTC)
    created_at = article.created_at or datetime.max.replace(tzinfo=UTC)
    return (reliability, -priority, has_content, -article_time.timestamp(), -created_at.timestamp())


def _recent_event_links(
    db: Session,
    article: Article,
    *,
    content_hash: str | None = None,
    require_recent: bool = True,
) -> list[EventArticle]:
    article_time = _article_reference_time(article)
    query = (
        select(EventArticle)
        .options(
            joinedload(EventArticle.event),
            joinedload(EventArticle.article).joinedload(Article.source),
        )
        .join(NewsEvent, NewsEvent.id == EventArticle.event_id)
        .join(Article, Article.id == EventArticle.article_id)
        .where(NewsEvent.status == EventStatus.ACTIVE)
        .where(EventArticle.article_id != article.id)
        .order_by(EventArticle.is_primary.desc(), EventArticle.created_at.asc())
    )
    if content_hash:
        query = query.where(Article.content_hash == content_hash)
    if require_recent and article_time is not None:
        cutoff = article_time - timedelta(days=RECENT_EVENT_WINDOW_DAYS)
        upper = article_time + timedelta(days=RECENT_EVENT_WINDOW_DAYS)
        query = query.where(
            func.coalesce(Article.published_at, Article.created_at).between(cutoff, upper)
        )
    return list(db.scalars(query))


def _hash_guard_details(article: Article, candidate: Article) -> dict:
    article_time = _article_reference_time(article)
    candidate_time = _article_reference_time(candidate)
    time_signal_missing = article_time is None or candidate_time is None
    within_time_window = False
    if not time_signal_missing:
        within_time_window = abs(article_time - candidate_time) <= timedelta(
            days=RECENT_EVENT_WINDOW_DAYS
        )

    article_source = article.source
    candidate_source = candidate.source
    category_conflict = bool(
        article_source
        and candidate_source
        and article_source.category
        and candidate_source.category
        and article_source.category.lower() != candidate_source.category.lower()
    )
    region_conflict = bool(
        article_source
        and candidate_source
        and article_source.region
        and candidate_source.region
        and article_source.region.lower() != candidate_source.region.lower()
    )

    return {
        "within_time_window": within_time_window,
        "time_signal_missing": time_signal_missing,
        "category_region_conflict": category_conflict or region_conflict,
        "category_conflict": category_conflict,
        "region_conflict": region_conflict,
        "window_days": RECENT_EVENT_WINDOW_DAYS,
    }


def _category_region_signals(source: Source | None, event: NewsEvent) -> tuple[float, float]:
    category_signal = 0.0
    region_signal = 0.0
    if (
        source
        and source.category
        and event.category
        and source.category.lower() == event.category.lower()
    ):
        category_signal = 0.025
    if source and source.region and event.region and source.region.lower() == event.region.lower():
        region_signal = 0.025
    return category_signal, region_signal


def _apply_event_filters(query: Select, filters: dict) -> Select:
    if filters["source_id"] is not None:
        query = query.join(EventArticle, EventArticle.event_id == NewsEvent.id).where(
            EventArticle.source_id == filters["source_id"]
        )
    if filters["category"] is not None:
        query = query.where(NewsEvent.category == filters["category"])
    if filters["region"] is not None:
        query = query.where(NewsEvent.region == filters["region"])
    if filters["status"] is not None:
        query = query.where(NewsEvent.status == filters["status"])
    if filters["published_from"] is not None:
        query = query.where(NewsEvent.published_at >= filters["published_from"])
    if filters["published_to"] is not None:
        query = query.where(NewsEvent.published_at <= filters["published_to"])
    if filters["min_confidence"] is not None:
        query = query.where(NewsEvent.confidence_score >= filters["min_confidence"])
    return query


def _get_article(db: Session, article_id: UUID) -> Article:
    article = db.scalar(
        select(Article).options(joinedload(Article.source)).where(Article.id == article_id)
    )
    if article is None:
        raise ArticleNotFoundError("Article not found.")
    return article


def _get_event_article_for_article(db: Session, article_id: UUID) -> EventArticle | None:
    return db.scalar(
        select(EventArticle)
        .options(joinedload(EventArticle.event))
        .where(EventArticle.article_id == article_id)
    )


def _article_reference_time(article: Article) -> datetime | None:
    return article.published_at or article.created_at


def _decimal_score(value: float) -> Decimal:
    clamped = max(0.0, min(1.0, value))
    return Decimal(str(round(clamped, 3)))
