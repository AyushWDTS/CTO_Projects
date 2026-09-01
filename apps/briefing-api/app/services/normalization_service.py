from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.article import Article, ArticleExtractionStatus
from app.models.ingestion import RawDocument
from app.models.source import Source
from app.schemas.normalization import NormalizationBatchResult, NormalizationRunResult
from app.services.extraction_service import ExtractionResult, extract_raw_document

DEFAULT_NORMALIZATION_LIMIT = 100
MAX_NORMALIZATION_LIMIT = 500


class RawDocumentNotFoundError(Exception):
    pass


class ArticleNotFoundError(Exception):
    pass


def normalize_raw_document(db: Session, raw_document_id: UUID) -> NormalizationRunResult:
    raw_document = _get_raw_document(db, raw_document_id)
    existing_article = _get_article_for_raw_document(db, raw_document_id)
    if existing_article is not None:
        return _result_from_article(existing_article)

    return _normalize_raw_document(db, raw_document)


def normalize_pending_raw_documents(
    db: Session,
    *,
    limit: int = DEFAULT_NORMALIZATION_LIMIT,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
) -> NormalizationBatchResult:
    normalized_limit = normalize_limit(limit)
    query = (
        select(RawDocument)
        .options(joinedload(RawDocument.source))
        .outerjoin(Article, Article.raw_document_id == RawDocument.id)
        .where(Article.id.is_(None))
        .order_by(RawDocument.fetched_at.desc(), RawDocument.created_at.desc())
        .limit(normalized_limit)
    )
    if fetched_after is not None:
        from app.services.demo_pipeline_service import apply_raw_document_fetched_after

        query = apply_raw_document_fetched_after(
            query,
            fetched_after,
            inclusive=fetched_after_inclusive,
        )
    raw_documents = list(db.scalars(query))
    return _normalize_batch(db, raw_documents)


def normalize_by_source(
    db: Session,
    source_id: UUID,
    *,
    limit: int = DEFAULT_NORMALIZATION_LIMIT,
    fetched_after: datetime | None = None,
    fetched_after_inclusive: bool = False,
) -> NormalizationBatchResult:
    normalized_limit = normalize_limit(limit)
    query = (
        select(RawDocument)
        .options(joinedload(RawDocument.source))
        .outerjoin(Article, Article.raw_document_id == RawDocument.id)
        .where(RawDocument.source_id == source_id)
        .where(Article.id.is_(None))
        .order_by(RawDocument.fetched_at.desc(), RawDocument.created_at.desc())
        .limit(normalized_limit)
    )
    if fetched_after is not None:
        from app.services.demo_pipeline_service import apply_raw_document_fetched_after

        query = apply_raw_document_fetched_after(
            query,
            fetched_after,
            inclusive=fetched_after_inclusive,
        )
    raw_documents = list(db.scalars(query))
    return _normalize_batch(db, raw_documents)


def count_pending_normalization_for_source(db: Session, source_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count(RawDocument.id))
            .outerjoin(Article, Article.raw_document_id == RawDocument.id)
            .where(RawDocument.source_id == source_id)
            .where(Article.id.is_(None))
        )
        or 0
    )


def count_pending_normalization(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(RawDocument.id))
            .outerjoin(Article, Article.raw_document_id == RawDocument.id)
            .where(Article.id.is_(None))
        )
        or 0
    )


def normalize_by_source_until_drained(
    db: Session,
    source_id: UUID,
    *,
    limit_per_batch: int = DEFAULT_NORMALIZATION_LIMIT,
    max_rounds: int = 10,
) -> tuple[NormalizationBatchResult, int]:
    normalized_batch_limit = normalize_limit(limit_per_batch)
    max_rounds = max(1, max_rounds)
    all_results: list[NormalizationRunResult] = []
    rounds_used = 0
    for _ in range(max_rounds):
        batch = normalize_by_source(db, source_id, limit=normalized_batch_limit)
        rounds_used += 1
        all_results.extend(batch.results)
        if batch.total_raw_documents == 0:
            break
    return (
        NormalizationBatchResult(
            total_raw_documents=len(all_results),
            results=all_results,
        ),
        rounds_used,
    )


def reprocess_failed_normalizations(
    db: Session,
    *,
    limit: int = DEFAULT_NORMALIZATION_LIMIT,
) -> NormalizationBatchResult:
    normalized_limit = normalize_limit(limit)
    articles = list(
        db.scalars(
            select(Article)
            .options(joinedload(Article.raw_document).joinedload(RawDocument.source))
            .where(Article.extraction_status == ArticleExtractionStatus.FAILED)
            .order_by(Article.updated_at.asc())
            .limit(normalized_limit)
        )
    )
    results = [
        _normalize_raw_document(db, article.raw_document, existing_article=article)
        for article in articles
    ]
    return NormalizationBatchResult(total_raw_documents=len(articles), results=results)


def get_article(db: Session, article_id: UUID) -> Article:
    article = db.get(Article, article_id)
    if article is None:
        raise ArticleNotFoundError("Article not found.")
    return article


def list_articles(
    db: Session,
    *,
    limit: int,
    offset: int,
    source_id: UUID | None = None,
    status: ArticleExtractionStatus | None = None,
    category: str | None = None,
    region: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    content_type: str | None = None,
) -> tuple[list[Article], int]:
    filters = {
        "source_id": source_id,
        "status": status,
        "category": category,
        "region": region,
        "published_from": published_from,
        "published_to": published_to,
        "content_type": content_type,
    }
    query = _apply_article_filters(select(Article).join(Source), filters).order_by(
        Article.published_at.desc().nullslast(),
        Article.created_at.desc(),
    )
    count_query = _apply_article_filters(select(func.count(Article.id)).join(Source), filters)

    total = db.scalar(count_query) or 0
    articles = list(db.scalars(query.limit(limit).offset(offset)))
    return articles, total


def normalize_limit(limit: int) -> int:
    return max(1, min(limit, MAX_NORMALIZATION_LIMIT))


def _normalize_batch(
    db: Session,
    raw_documents: list[RawDocument],
) -> NormalizationBatchResult:
    results = [_normalize_raw_document(db, raw_document) for raw_document in raw_documents]
    return NormalizationBatchResult(total_raw_documents=len(raw_documents), results=results)


def _normalize_raw_document(
    db: Session,
    raw_document: RawDocument,
    *,
    existing_article: Article | None = None,
) -> NormalizationRunResult:
    extraction = extract_raw_document(raw_document)
    duplicate = _find_exact_duplicate(db, raw_document, extraction, existing_article)
    article = existing_article or Article(
        raw_document_id=raw_document.id,
        source_id=raw_document.source_id,
    )

    _apply_extraction(article, raw_document, extraction, duplicate)
    db.add(article)
    db.commit()
    db.refresh(article)
    return _result_from_article(article)


def _apply_extraction(
    article: Article,
    raw_document: RawDocument,
    extraction: ExtractionResult,
    duplicate: Article | None,
) -> None:
    status = extraction.status
    if duplicate is not None:
        status = ArticleExtractionStatus.EXACT_DUPLICATE

    article.raw_document_id = raw_document.id
    article.source_id = raw_document.source_id
    article.title = extraction.title
    article.canonical_url = extraction.canonical_url
    article.source_url = extraction.source_url or raw_document.url
    article.content_type = extraction.content_type
    article.clean_text = extraction.clean_text
    article.excerpt = extraction.excerpt
    article.author = extraction.author
    article.published_at = extraction.published_at
    article.language = extraction.language
    article.content_hash = extraction.content_hash
    article.extraction_status = status
    article.extraction_error = (
        "exact_duplicate"
        if status == ArticleExtractionStatus.EXACT_DUPLICATE
        else extraction.extraction_error
    )
    article.duplicate_of_article_id = duplicate.id if duplicate else None
    article.article_metadata = extraction.metadata


def _find_exact_duplicate(
    db: Session,
    raw_document: RawDocument,
    extraction: ExtractionResult,
    existing_article: Article | None,
) -> Article | None:
    if extraction.status != ArticleExtractionStatus.SUCCESS:
        return None
    if not extraction.canonical_url or not extraction.content_hash:
        return None

    query = (
        select(Article)
        .where(Article.canonical_url == extraction.canonical_url)
        .where(Article.content_hash == extraction.content_hash)
        .where(Article.raw_document_id != raw_document.id)
        .order_by(Article.created_at.asc())
    )
    if existing_article is not None:
        query = query.where(Article.id != existing_article.id)
    return db.scalar(query)


def _get_raw_document(db: Session, raw_document_id: UUID) -> RawDocument:
    raw_document = db.scalar(
        select(RawDocument)
        .options(joinedload(RawDocument.source))
        .where(RawDocument.id == raw_document_id)
    )
    if raw_document is None:
        raise RawDocumentNotFoundError("Raw document not found.")
    return raw_document


def _get_article_for_raw_document(db: Session, raw_document_id: UUID) -> Article | None:
    return db.scalar(select(Article).where(Article.raw_document_id == raw_document_id))


def _result_from_article(article: Article) -> NormalizationRunResult:
    return NormalizationRunResult(
        raw_document_id=article.raw_document_id,
        source_id=article.source_id,
        status=article.extraction_status,
        article_id=article.id,
        reason=article.extraction_error,
        duplicate_of_article_id=article.duplicate_of_article_id,
    )


def _apply_article_filters(
    query: Select[tuple[Article]] | Select[tuple[int]],
    filters: dict[str, object],
):
    if filters["source_id"] is not None:
        query = query.where(Article.source_id == filters["source_id"])
    if filters["status"] is not None:
        query = query.where(Article.extraction_status == filters["status"])
    if filters["category"] is not None:
        query = query.where(Source.category == filters["category"])
    if filters["region"] is not None:
        query = query.where(Source.region == filters["region"])
    if filters["published_from"] is not None:
        query = query.where(Article.published_at >= filters["published_from"])
    if filters["published_to"] is not None:
        query = query.where(Article.published_at <= filters["published_to"])
    if filters["content_type"] is not None:
        query = query.where(Article.content_type == filters["content_type"])
    return query
