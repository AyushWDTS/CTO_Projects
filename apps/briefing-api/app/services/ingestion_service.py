import hashlib
import json
import sys
from datetime import UTC, datetime
from uuid import UUID

import feedparser
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.ingestion import FetchLogStatus, RawDocument, SourceFetchLog
from app.models.source import FetchMethod, Source
from app.schemas.ingestion import IngestionBatchResult, IngestionRunResult
from app.services.http_client import HttpFetchError, HttpFetchResponse, fetch_url
from app.services.source_service import get_source

MAX_RSS_ENTRIES_PER_SOURCE = 50
SUPPORTED_FETCH_METHODS = {FetchMethod.RSS, FetchMethod.STATIC_HTML}


def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


def _log(msg: str) -> None:
    print(f"[ingest {_ts()}] {msg}", file=sys.stderr, flush=True)


def ingest_source(db: Session, source_id: UUID) -> IngestionRunResult:
    source = get_source(db, source_id)

    if source.fetch_method not in SUPPORTED_FETCH_METHODS:
        return _record_skipped_result(db, source, "unsupported_fetch_method")

    if source.fetch_method == FetchMethod.RSS:
        return _ingest_rss_source(db, source)

    return _ingest_static_html_source(db, source)


def ingest_all_sources(db: Session) -> IngestionBatchResult:
    sources = list(
        db.scalars(
            select(Source)
            .where(Source.is_active.is_(True))
            .where(Source.fetch_method.in_([FetchMethod.RSS, FetchMethod.STATIC_HTML]))
            .order_by(Source.priority.asc(), Source.name.asc())
        )
    )

    _log(f"Fetching {len(sources)} sources sequentially")
    results: list[IngestionRunResult] = []
    for i, source in enumerate(sources, 1):
        t0 = datetime.now(UTC)
        _log(f"  [{i}/{len(sources)}] {source.name} ({source.fetch_method})")
        result = ingest_source(db, source.id)
        elapsed = round((datetime.now(UTC) - t0).total_seconds(), 1)
        status_label = result.status.value if hasattr(result.status, "value") else str(result.status)
        _log(
            f"  [{i}/{len(sources)}] {source.name} → {status_label} "
            f"found={result.items_found} stored={result.items_stored} ({elapsed}s)"
        )
        results.append(result)
    _log(f"Ingestion complete: {len(sources)} sources processed")
    return IngestionBatchResult(total_sources=len(sources), results=results)


def list_raw_documents(
    db: Session,
    *,
    limit: int,
    offset: int,
    source_id: UUID | None = None,
) -> tuple[list[RawDocument], int]:
    filters = {"source_id": source_id}
    query = _apply_raw_document_filters(select(RawDocument), filters).order_by(
        RawDocument.fetched_at.desc(),
        RawDocument.created_at.desc(),
    )
    count_query = _apply_raw_document_filters(select(func.count(RawDocument.id)), filters)

    total = db.scalar(count_query) or 0
    documents = list(db.scalars(query.limit(limit).offset(offset)))
    return documents, total


def list_fetch_logs(
    db: Session,
    *,
    limit: int,
    offset: int,
    source_id: UUID | None = None,
    status: FetchLogStatus | None = None,
) -> tuple[list[SourceFetchLog], int]:
    filters = {"source_id": source_id, "status": status}
    query = _apply_fetch_log_filters(select(SourceFetchLog), filters).order_by(
        SourceFetchLog.started_at.desc(),
        SourceFetchLog.created_at.desc(),
    )
    count_query = _apply_fetch_log_filters(select(func.count(SourceFetchLog.id)), filters)

    total = db.scalar(count_query) or 0
    logs = list(db.scalars(query.limit(limit).offset(offset)))
    return logs, total


def _ingest_rss_source(db: Session, source: Source) -> IngestionRunResult:
    if not source.rss_url:
        return _record_failed_result(db, source, "missing_rss_url")

    fetch_log = _start_fetch_log(db, source)

    try:
        response = fetch_url(source.rss_url)
        if response.status_code >= 400:
            return _record_failed_result(
                db,
                source,
                f"http_status_{response.status_code}",
                fetch_log=fetch_log,
                http_status=response.status_code,
            )

        parsed_feed = feedparser.parse(response.text)
        entries = list(parsed_feed.entries[:MAX_RSS_ENTRIES_PER_SOURCE])
        documents: list[RawDocument] = []
        skipped_duplicates = 0
        for entry in entries:
            document = _raw_document_from_rss_entry(source, response, parsed_feed.feed, entry)
            if _raw_document_already_stored(db, source.id, document.url, document.raw_hash):
                skipped_duplicates += 1
                continue
            documents.append(document)

        if documents:
            db.add_all(documents)
        _finish_fetch_log(
            fetch_log,
            status=FetchLogStatus.SUCCESS,
            http_status=response.status_code,
            items_found=len(entries),
            items_stored=len(documents),
        )
        _mark_source_success(source, fetch_log.finished_at)
        db.commit()

        return _result_from_log(fetch_log, documents)
    except (HttpFetchError, Exception) as exc:
        return _record_failed_result(db, source, str(exc), fetch_log=fetch_log)


def _ingest_static_html_source(db: Session, source: Source) -> IngestionRunResult:
    fetch_log = _start_fetch_log(db, source)

    try:
        response = fetch_url(source.url)
        if response.status_code >= 400:
            return _record_failed_result(
                db,
                source,
                f"http_status_{response.status_code}",
                fetch_log=fetch_log,
                http_status=response.status_code,
            )

        content_hash = _raw_hash(response.text)
        if _raw_document_already_stored(db, source.id, source.url, content_hash):
            _finish_fetch_log(
                fetch_log,
                status=FetchLogStatus.SUCCESS,
                http_status=response.status_code,
                items_found=1,
                items_stored=0,
            )
            _mark_source_success(source, fetch_log.finished_at)
            db.commit()
            return IngestionRunResult(
                source_id=source.id,
                status=FetchLogStatus.SUCCESS,
                reason="unchanged_content",
                items_found=1,
                items_stored=0,
                fetch_log_id=fetch_log.id,
                http_status=fetch_log.http_status,
            )

        document = _raw_document_from_static_html(source, response)
        db.add(document)
        _finish_fetch_log(
            fetch_log,
            status=FetchLogStatus.SUCCESS,
            http_status=response.status_code,
            items_found=1,
            items_stored=1,
        )
        _mark_source_success(source, fetch_log.finished_at)
        db.commit()

        return _result_from_log(fetch_log, [document])
    except (HttpFetchError, Exception) as exc:
        return _record_failed_result(db, source, str(exc), fetch_log=fetch_log)


def _record_skipped_result(db: Session, source: Source, reason: str) -> IngestionRunResult:
    started_at = _now()
    fetch_log = SourceFetchLog(
        source_id=source.id,
        status=FetchLogStatus.SKIPPED,
        started_at=started_at,
        finished_at=started_at,
        error_message=reason,
        items_found=0,
        items_stored=0,
    )
    db.add(fetch_log)
    db.commit()
    db.refresh(fetch_log)

    return IngestionRunResult(
        source_id=source.id,
        status=FetchLogStatus.SKIPPED,
        reason=reason,
        fetch_log_id=fetch_log.id,
    )


def _record_failed_result(
    db: Session,
    source: Source,
    error_message: str,
    *,
    fetch_log: SourceFetchLog | None = None,
    http_status: int | None = None,
) -> IngestionRunResult:
    if fetch_log is None:
        fetch_log = _start_fetch_log(db, source)

    _finish_fetch_log(
        fetch_log,
        status=FetchLogStatus.FAILED,
        http_status=http_status,
        error_message=error_message,
        items_found=0,
        items_stored=0,
    )
    _mark_source_failure(source, fetch_log.finished_at)
    db.commit()
    db.refresh(fetch_log)

    return IngestionRunResult(
        source_id=source.id,
        status=FetchLogStatus.FAILED,
        reason=error_message,
        fetch_log_id=fetch_log.id,
        http_status=fetch_log.http_status,
        error_message=error_message,
    )


def _start_fetch_log(db: Session, source: Source) -> SourceFetchLog:
    fetch_log = SourceFetchLog(
        source_id=source.id,
        status=FetchLogStatus.RUNNING,
        started_at=_now(),
    )
    db.add(fetch_log)
    db.flush()
    return fetch_log


def _finish_fetch_log(
    fetch_log: SourceFetchLog,
    *,
    status: FetchLogStatus,
    http_status: int | None = None,
    error_message: str | None = None,
    items_found: int | None = None,
    items_stored: int | None = None,
) -> None:
    fetch_log.status = status
    fetch_log.finished_at = _now()
    fetch_log.http_status = http_status
    fetch_log.error_message = error_message
    fetch_log.items_found = items_found
    fetch_log.items_stored = items_stored


def _mark_source_success(source: Source, fetched_at: datetime | None) -> None:
    timestamp = fetched_at or _now()
    source.last_fetched_at = timestamp
    source.last_success_at = timestamp
    source.failure_count = 0


def _mark_source_failure(source: Source, fetched_at: datetime | None) -> None:
    source.last_fetched_at = fetched_at or _now()
    source.failure_count += 1


def _raw_document_from_rss_entry(
    source: Source,
    response: HttpFetchResponse,
    feed: dict,
    entry: dict,
) -> RawDocument:
    entry_url = _entry_value(entry, "link") or response.url
    title = _entry_value(entry, "title")
    published = _entry_value(entry, "published")
    raw_content = _entry_raw_content(entry)
    metadata = {
        "feed_title": _entry_value(feed, "title"),
        "entry_title": title,
        "published": published,
        "rss_url": source.rss_url,
    }

    return _create_raw_document(
        source=source,
        url=entry_url,
        canonical_url=entry_url,
        content_type=response.content_type or "application/rss+xml",
        raw_content=raw_content,
        http_status=response.status_code,
        document_metadata=metadata,
    )


def _raw_document_from_static_html(source: Source, response: HttpFetchResponse) -> RawDocument:
    return _create_raw_document(
        source=source,
        url=source.url,
        canonical_url=response.url,
        content_type=response.content_type,
        raw_content=response.text,
        http_status=response.status_code,
        document_metadata={"source_url": source.url, "final_url": response.url},
    )


def _create_raw_document(
    *,
    source: Source,
    url: str,
    canonical_url: str | None,
    content_type: str | None,
    raw_content: str | None,
    http_status: int | None,
    document_metadata: dict | None,
) -> RawDocument:
    fetched_at = _now()
    return RawDocument(
        source_id=source.id,
        url=url,
        canonical_url=canonical_url,
        content_type=_normalize_content_type(content_type),
        raw_content=raw_content,
        raw_hash=_raw_hash(raw_content),
        raw_size_bytes=_raw_size_bytes(raw_content),
        http_status=http_status,
        fetched_at=fetched_at,
        document_metadata=document_metadata,
    )


def _entry_raw_content(entry: dict) -> str:
    content = entry.get("content")
    if isinstance(content, list) and content:
        value = content[0].get("value")
        if value:
            return str(value)

    for key in ("summary", "description", "title"):
        value = entry.get(key)
        if value:
            return str(value)

    return json.dumps({key: str(value) for key, value in entry.items()}, sort_keys=True)


def _entry_value(container: dict, key: str) -> str | None:
    value = container.get(key)
    if value is None:
        return None
    return str(value)


def _raw_hash(raw_content: str | None) -> str:
    return hashlib.sha256((raw_content or "").encode("utf-8")).hexdigest()


def _raw_document_already_stored(
    db: Session,
    source_id: UUID,
    url: str,
    raw_hash: str,
) -> bool:
    existing_id = db.scalar(
        select(RawDocument.id)
        .where(RawDocument.source_id == source_id)
        .where(RawDocument.url == url)
        .where(RawDocument.raw_hash == raw_hash)
        .limit(1)
    )
    return existing_id is not None


def _raw_size_bytes(raw_content: str | None) -> int:
    return len((raw_content or "").encode("utf-8"))


def _normalize_content_type(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    return content_type.split(";", maxsplit=1)[0].strip()[:100]


def _result_from_log(
    fetch_log: SourceFetchLog,
    documents: list[RawDocument],
) -> IngestionRunResult:
    return IngestionRunResult(
        source_id=fetch_log.source_id,
        status=fetch_log.status,
        items_found=fetch_log.items_found or 0,
        items_stored=fetch_log.items_stored or 0,
        raw_document_ids=[document.id for document in documents],
        fetch_log_id=fetch_log.id,
        http_status=fetch_log.http_status,
        error_message=fetch_log.error_message,
    )


def _apply_raw_document_filters(
    query: Select[tuple[RawDocument]] | Select[tuple[int]],
    filters: dict[str, object],
):
    if filters["source_id"] is not None:
        query = query.where(RawDocument.source_id == filters["source_id"])
    return query


def _apply_fetch_log_filters(
    query: Select[tuple[SourceFetchLog]] | Select[tuple[int]],
    filters: dict[str, object],
):
    if filters["source_id"] is not None:
        query = query.where(SourceFetchLog.source_id == filters["source_id"])
    if filters["status"] is not None:
        query = query.where(SourceFetchLog.status == filters["status"])
    return query


def _now() -> datetime:
    return datetime.now(UTC)
