from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID

import feedparser
import httpx
from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.article import Article, ArticleExtractionStatus
from app.models.data_quality import (
    DataQualityFinding,
    DataQualityRun,
    DataQualityRunStatus,
    DataQualityScopeType,
    DataQualitySeverity,
    SourceHealthCheck,
    SourceHealthStatus,
)
from app.models.digest import Digest
from app.models.event import EventStatus, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.models.ingestion import RawDocument, SourceFetchLog
from app.models.orchestration import OrchestrationRun
from app.models.source import FetchMethod, Source
from app.schemas.data_quality import (
    DataQualityFindingRead,
    DataQualityRunRead,
    DataQualityRunResult,
    DataQualitySummary,
    SourceHealthCheckRead,
    SourceHealthRunResult,
)
from app.services.source_service import get_source

SOURCE_HEALTH_TIMEOUT_SECONDS = 10.0
SOURCE_HEALTH_MAX_REDIRECTS = 3
SOURCE_HEALTH_MAX_RESPONSE_BYTES = 1_000_000
SOURCE_HEALTH_USER_AGENT = "NewsIntelligenceBot/0.1"
SUPPORTED_INGESTION_METHODS = {FetchMethod.RSS, FetchMethod.STATIC_HTML}
SUSPICIOUS_SMALL_RAW_BYTES = 64
HIGH_FAILURE_COUNT = 3
LOW_EVENT_CONFIDENCE = 0.500
REPEATED_FETCH_LOG_THRESHOLD = 3

SEVERITY_ORDER = {
    DataQualitySeverity.INFO.value: 0,
    DataQualitySeverity.WARNING.value: 1,
    DataQualitySeverity.ERROR.value: 2,
    DataQualitySeverity.CRITICAL.value: 3,
}


@dataclass(frozen=True)
class SourceHealthFetchResponse:
    status_code: int
    content_size_bytes: int
    text: str
    latency_ms: int
    final_url: str


class SourceHealthFetchError(Exception):
    def __init__(
        self,
        reason: str,
        *,
        latency_ms: int | None = None,
        http_status: int | None = None,
        content_size_bytes: int | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.latency_ms = latency_ms
        self.http_status = http_status
        self.content_size_bytes = content_size_bytes


def severity_values_at_or_above(min_severity: DataQualitySeverity | str | None) -> list[str]:
    if min_severity is None:
        return list(SEVERITY_ORDER)
    severity = min_severity.value if isinstance(min_severity, DataQualitySeverity) else min_severity
    minimum = SEVERITY_ORDER[severity]
    return [value for value, order in SEVERITY_ORDER.items() if order >= minimum]


def fetch_source_health_url(
    url: str,
    *,
    timeout_seconds: float = SOURCE_HEALTH_TIMEOUT_SECONDS,
    max_redirects: int = SOURCE_HEALTH_MAX_REDIRECTS,
    max_response_bytes: int = SOURCE_HEALTH_MAX_RESPONSE_BYTES,
) -> SourceHealthFetchResponse:
    started = monotonic()
    headers = {"User-Agent": SOURCE_HEALTH_USER_AGENT}

    try:
        with httpx.Client(
            follow_redirects=True,
            max_redirects=max_redirects,
            timeout=timeout_seconds,
            headers=headers,
        ) as client:
            with client.stream("GET", url) as response:
                chunks: list[bytes] = []
                total_size = 0
                for chunk in response.iter_bytes():
                    total_size += len(chunk)
                    if total_size > max_response_bytes:
                        raise SourceHealthFetchError(
                            "max_response_size_exceeded",
                            latency_ms=_elapsed_ms(started),
                            http_status=response.status_code,
                            content_size_bytes=total_size,
                        )
                    chunks.append(chunk)

                body = b"".join(chunks)
                return SourceHealthFetchResponse(
                    status_code=response.status_code,
                    content_size_bytes=len(body),
                    text=body.decode(response.encoding or "utf-8", errors="replace"),
                    latency_ms=_elapsed_ms(started),
                    final_url=str(response.url),
                )
    except SourceHealthFetchError:
        raise
    except httpx.TooManyRedirects as exc:
        raise SourceHealthFetchError("too_many_redirects", latency_ms=_elapsed_ms(started)) from exc
    except httpx.TimeoutException as exc:
        raise SourceHealthFetchError("timeout", latency_ms=_elapsed_ms(started)) from exc
    except httpx.HTTPError as exc:
        raise SourceHealthFetchError(str(exc), latency_ms=_elapsed_ms(started)) from exc


def run_source_health_checks(
    db: Session,
    *,
    source_id: UUID | None = None,
) -> SourceHealthRunResult:
    sources = (
        [get_source(db, source_id)]
        if source_id
        else list(
            db.scalars(
                select(Source)
                .where(Source.is_active.is_(True))
                .order_by(Source.priority, Source.name)
            )
        )
    )

    checks = [_check_source_health(source) for source in sources]
    db.add_all(checks)
    db.commit()
    for check in checks:
        db.refresh(check)

    status_counts = Counter(check.status for check in checks)
    return SourceHealthRunResult(
        total_sources=len(sources),
        status_counts=dict(status_counts),
        results=[SourceHealthCheckRead.model_validate(check) for check in checks],
    )


def run_data_quality_checks(
    db: Session,
    *,
    source_id: UUID | None = None,
    min_severity: DataQualitySeverity | None = None,
) -> DataQualityRunResult:
    if source_id is not None:
        get_source(db, source_id)

    started_at = _now()
    run = DataQualityRun(
        status=DataQualityRunStatus.RUNNING.value,
        started_at=started_at,
        scope_source_id=source_id,
        min_severity=min_severity.value if min_severity else None,
        run_metadata={"severity_order": list(SEVERITY_ORDER)},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        findings = _collect_quality_findings(db, run.id, source_id=source_id)
        allowed = set(severity_values_at_or_above(min_severity))
        filtered = [finding for finding in findings if finding.severity in allowed]
        db.add_all(filtered)

        finished_at = _now()
        run.status = DataQualityRunStatus.SUCCESS.value
        run.finished_at = finished_at
        run.duration_seconds = _duration_seconds(started_at, finished_at)
        run.total_findings = len(filtered)
        db.commit()
    except Exception as exc:
        finished_at = _now()
        run.status = DataQualityRunStatus.FAILED.value
        run.finished_at = finished_at
        run.duration_seconds = _duration_seconds(started_at, finished_at)
        run.run_metadata = {**(run.run_metadata or {}), "error_message": str(exc)}
        db.commit()
        raise

    db.refresh(run)
    for finding in filtered:
        db.refresh(finding)

    severity_counts = Counter(finding.severity for finding in filtered)
    return DataQualityRunResult(
        run=DataQualityRunRead.model_validate(run),
        severity_counts=dict(severity_counts),
        findings=[DataQualityFindingRead.model_validate(finding) for finding in filtered],
    )


def list_data_quality_findings(
    db: Session,
    *,
    limit: int,
    offset: int,
    run_id: UUID | None = None,
    severity: DataQualitySeverity | None = None,
    min_severity: DataQualitySeverity | None = None,
    check_name: str | None = None,
    scope_type: DataQualityScopeType | None = None,
    source_id: UUID | None = None,
) -> tuple[list[DataQualityFinding], int]:
    filters = {
        "run_id": run_id,
        "severity": severity,
        "min_severity": min_severity,
        "check_name": check_name,
        "scope_type": scope_type,
        "source_id": source_id,
    }
    query = _apply_finding_filters(select(DataQualityFinding), filters).order_by(
        DataQualityFinding.created_at.desc(),
        DataQualityFinding.severity.desc(),
    )
    count_query = _apply_finding_filters(select(func.count(DataQualityFinding.id)), filters)
    total = db.scalar(count_query) or 0
    findings = list(db.scalars(query.limit(limit).offset(offset)))
    return findings, total


def list_source_health_checks(
    db: Session,
    *,
    limit: int,
    offset: int,
    source_id: UUID | None = None,
    status: SourceHealthStatus | None = None,
) -> tuple[list[SourceHealthCheck], int]:
    filters = {"source_id": source_id, "status": status}
    query = _apply_source_health_filters(select(SourceHealthCheck), filters).order_by(
        SourceHealthCheck.checked_at.desc(),
        SourceHealthCheck.created_at.desc(),
    )
    count_query = _apply_source_health_filters(select(func.count(SourceHealthCheck.id)), filters)
    total = db.scalar(count_query) or 0
    checks = list(db.scalars(query.limit(limit).offset(offset)))
    return checks, total


def get_data_quality_summary(db: Session) -> DataQualitySummary:
    latest_run = db.scalar(
        select(DataQualityRun).order_by(DataQualityRun.created_at.desc()).limit(1)
    )
    severity_counts: Counter[str] = Counter()
    latest_findings: list[DataQualityFinding] = []

    if latest_run is not None:
        rows = db.execute(
            select(DataQualityFinding.severity, func.count(DataQualityFinding.id))
            .where(DataQualityFinding.run_id == latest_run.id)
            .group_by(DataQualityFinding.severity)
        )
        severity_counts.update({severity: count for severity, count in rows})
        latest_findings = list(
            db.scalars(
                select(DataQualityFinding)
                .where(DataQualityFinding.run_id == latest_run.id)
                .where(DataQualityFinding.severity.in_(severity_values_at_or_above(DataQualitySeverity.ERROR)))
                .order_by(DataQualityFinding.created_at.desc())
                .limit(10)
            )
        )

    latest_health_subquery = (
        select(
            SourceHealthCheck.source_id,
            func.max(SourceHealthCheck.checked_at).label("checked_at"),
        )
        .group_by(SourceHealthCheck.source_id)
        .subquery()
    )
    health_rows = db.execute(
        select(SourceHealthCheck.status, func.count(SourceHealthCheck.id))
        .join(
            latest_health_subquery,
            and_(
                SourceHealthCheck.source_id == latest_health_subquery.c.source_id,
                SourceHealthCheck.checked_at == latest_health_subquery.c.checked_at,
            ),
        )
        .group_by(SourceHealthCheck.status)
    )
    source_health_counts = {status: count for status, count in health_rows}

    return DataQualitySummary(
        latest_run=DataQualityRunRead.model_validate(latest_run) if latest_run else None,
        severity_counts=dict(severity_counts),
        source_health_counts=source_health_counts,
        latest_findings=[
            DataQualityFindingRead.model_validate(finding) for finding in latest_findings
        ],
    )


def _check_source_health(source: Source) -> SourceHealthCheck:
    checked_at = _now()
    metadata = {
        "fetch_method": source.fetch_method.value,
        "network_safety": {
            "timeout_seconds": SOURCE_HEALTH_TIMEOUT_SECONDS,
            "max_redirects": SOURCE_HEALTH_MAX_REDIRECTS,
            "max_response_bytes": SOURCE_HEALTH_MAX_RESPONSE_BYTES,
            "user_agent": SOURCE_HEALTH_USER_AGENT,
        },
    }

    if source.fetch_method == FetchMethod.RSS and not source.rss_url:
        return _source_health_check(
            source,
            status=SourceHealthStatus.FAILING,
            checked_at=checked_at,
            error_reason="missing_rss_url",
            recommendation="add_rss_url_or_change_fetch_method",
            metadata=metadata,
        )

    if source.fetch_method not in SUPPORTED_INGESTION_METHODS:
        return _source_health_check(
            source,
            status=SourceHealthStatus.SKIPPED,
            checked_at=checked_at,
            error_reason="unsupported_fetch_method",
            recommendation="source health checks support rss and static_html sources only",
            metadata=metadata,
        )

    url = source.rss_url if source.fetch_method == FetchMethod.RSS else source.url
    try:
        response = fetch_source_health_url(url)
    except SourceHealthFetchError as exc:
        return _source_health_check(
            source,
            status=SourceHealthStatus.FAILING,
            checked_at=checked_at,
            latency_ms=exc.latency_ms,
            http_status=exc.http_status,
            content_size_bytes=exc.content_size_bytes,
            error_reason=exc.reason,
            recommendation="review_source_url_or_network_availability",
            metadata=metadata,
        )

    if response.status_code >= 400:
        return _source_health_check(
            source,
            status=SourceHealthStatus.FAILING,
            checked_at=checked_at,
            latency_ms=response.latency_ms,
            http_status=response.status_code,
            content_size_bytes=response.content_size_bytes,
            error_reason=f"http_status_{response.status_code}",
            recommendation="review_source_url_or_access_requirements",
            metadata={**metadata, "final_url": response.final_url},
        )

    if source.fetch_method == FetchMethod.RSS:
        parsed = feedparser.parse(response.text)
        item_count = len(parsed.entries)
        status = SourceHealthStatus.HEALTHY if item_count > 0 else SourceHealthStatus.DEGRADED
        recommendation = None if item_count > 0 else "rss_feed_returned_zero_items"
        return _source_health_check(
            source,
            status=status,
            checked_at=checked_at,
            latency_ms=response.latency_ms,
            http_status=response.status_code,
            item_count=item_count,
            content_size_bytes=response.content_size_bytes,
            recommendation=recommendation,
            metadata={**metadata, "final_url": response.final_url},
        )

    status = (
        SourceHealthStatus.HEALTHY
        if response.content_size_bytes > 0
        else SourceHealthStatus.DEGRADED
    )
    return _source_health_check(
        source,
        status=status,
        checked_at=checked_at,
        latency_ms=response.latency_ms,
        http_status=response.status_code,
        content_size_bytes=response.content_size_bytes,
        recommendation=None if response.content_size_bytes > 0 else "empty_static_html_response",
        metadata={**metadata, "final_url": response.final_url},
    )


def _source_health_check(
    source: Source,
    *,
    status: SourceHealthStatus,
    checked_at: datetime,
    latency_ms: int | None = None,
    http_status: int | None = None,
    item_count: int | None = None,
    content_size_bytes: int | None = None,
    error_reason: str | None = None,
    recommendation: str | None = None,
    metadata: dict | None = None,
) -> SourceHealthCheck:
    return SourceHealthCheck(
        source_id=source.id,
        status=status.value,
        checked_at=checked_at,
        finished_at=_now(),
        latency_ms=latency_ms,
        http_status=http_status,
        item_count=item_count,
        content_size_bytes=content_size_bytes,
        error_reason=error_reason,
        recommendation=recommendation,
        health_metadata=metadata,
    )


def _collect_quality_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []

    source_query = select(Source)
    if source_id:
        source_query = source_query.where(Source.id == source_id)
    for source in db.scalars(source_query):
        if source.is_active and source.fetch_method == FetchMethod.RSS and not source.rss_url:
            findings.append(
                _finding(
                    run_id,
                    check_name="active_rss_source_missing_rss_url",
                    scope_type=DataQualityScopeType.SOURCE,
                    scope_id=source.id,
                    source_id=source.id,
                    severity=DataQualitySeverity.ERROR,
                    message=f"Active RSS source '{source.name}' is missing rss_url.",
                    recommendation="add_rss_url_or_change_fetch_method",
                )
            )
        if source.is_active and source.fetch_method not in SUPPORTED_INGESTION_METHODS:
            findings.append(
                _finding(
                    run_id,
                    check_name="active_source_unsupported_ingestion_method",
                    scope_type=DataQualityScopeType.SOURCE,
                    scope_id=source.id,
                    source_id=source.id,
                    severity=DataQualitySeverity.WARNING,
                    message=(
                        f"Active source '{source.name}' uses unsupported method "
                        f"'{source.fetch_method}'."
                    ),
                    recommendation="use manual until an ingestible method is available",
                )
            )
        if (
            source.is_active
            and source.fetch_method == FetchMethod.MANUAL
            and not _has_manual_notes(source)
        ):
            findings.append(
                _finding(
                    run_id,
                    check_name="manual_source_missing_activation_notes",
                    scope_type=DataQualityScopeType.SOURCE,
                    scope_id=source.id,
                    source_id=source.id,
                    severity=DataQualitySeverity.INFO,
                    message=f"Manual source '{source.name}' does not explain activation status.",
                    recommendation="add notes describing why the source remains manual",
                )
            )
        if source.failure_count >= HIGH_FAILURE_COUNT:
            findings.append(
                _finding(
                    run_id,
                    check_name="source_high_failure_count",
                    scope_type=DataQualityScopeType.SOURCE,
                    scope_id=source.id,
                    source_id=source.id,
                    severity=(
                        DataQualitySeverity.ERROR
                        if source.failure_count >= 5
                        else DataQualitySeverity.WARNING
                    ),
                    message=f"Source '{source.name}' has failure_count={source.failure_count}.",
                    recommendation="review source URL, fetch method, or feed stability",
                )
            )
        if source.is_active and source.last_success_at is None:
            findings.append(
                _finding(
                    run_id,
                    check_name="active_source_never_successfully_fetched",
                    scope_type=DataQualityScopeType.SOURCE,
                    scope_id=source.id,
                    source_id=source.id,
                    severity=DataQualitySeverity.WARNING,
                    message=(
                        f"Active source '{source.name}' has never completed a "
                        "successful fetch."
                    ),
                    recommendation=(
                        "run ingestion or review whether this source is intentionally manual"
                    ),
                )
            )

    findings.extend(_raw_document_findings(db, run_id, source_id=source_id))
    findings.extend(_article_findings(db, run_id, source_id=source_id))
    findings.extend(_event_findings(db, run_id, source_id=source_id))
    findings.extend(_analysis_findings(db, run_id, source_id=source_id))
    findings.extend(_digest_findings(db, run_id))
    findings.extend(_orchestration_findings(db, run_id))
    findings.extend(_zero_item_fetch_log_findings(db, run_id, source_id=source_id))
    findings.extend(_timeout_fetch_log_findings(db, run_id, source_id=source_id))
    return findings


def _raw_document_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    query = select(RawDocument)
    if source_id:
        query = query.where(RawDocument.source_id == source_id)
    findings = []
    for document in db.scalars(query):
        if not document.raw_content:
            findings.append(
                _finding(
                    run_id,
                    check_name="raw_document_empty_content",
                    scope_type=DataQualityScopeType.RAW_DOCUMENT,
                    scope_id=document.id,
                    source_id=document.source_id,
                    severity=DataQualitySeverity.ERROR,
                    message="Raw document has empty raw_content.",
                    recommendation="review ingestion response and source health",
                )
            )
        elif (
            document.raw_size_bytes is not None
            and document.raw_size_bytes < SUSPICIOUS_SMALL_RAW_BYTES
        ):
            findings.append(
                _finding(
                    run_id,
                    check_name="raw_document_suspiciously_small",
                    scope_type=DataQualityScopeType.RAW_DOCUMENT,
                    scope_id=document.id,
                    source_id=document.source_id,
                    severity=DataQualitySeverity.WARNING,
                    message=f"Raw document is only {document.raw_size_bytes} bytes.",
                    recommendation=(
                        "review whether the fetched content is a placeholder or error page"
                    ),
                )
            )
    return findings


def _article_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    query = select(Article)
    if source_id:
        query = query.where(Article.source_id == source_id)
    findings = []
    for article in db.scalars(query):
        if article.extraction_status in {
            ArticleExtractionStatus.FAILED,
            ArticleExtractionStatus.SKIPPED,
        }:
            findings.append(
                _finding(
                    run_id,
                    check_name="article_extraction_not_successful",
                    scope_type=DataQualityScopeType.ARTICLE,
                    scope_id=article.id,
                    source_id=article.source_id,
                    severity=(
                        DataQualitySeverity.ERROR
                        if article.extraction_status == ArticleExtractionStatus.FAILED
                        else DataQualitySeverity.WARNING
                    ),
                    message=f"Article extraction status is {article.extraction_status}.",
                    recommendation="review raw document and extraction path",
                    metadata={"extraction_error": article.extraction_error},
                )
            )
        if article.extraction_status == ArticleExtractionStatus.SUCCESS:
            missing = [
                field
                for field, value in {
                    "title": article.title,
                    "clean_text": article.clean_text,
                    "canonical_url": article.canonical_url,
                    "published_at": article.published_at,
                }.items()
                if not value
            ]
            if missing:
                findings.append(
                    _finding(
                        run_id,
                        check_name="successful_article_missing_fields",
                        scope_type=DataQualityScopeType.ARTICLE,
                        scope_id=article.id,
                        source_id=article.source_id,
                        severity=DataQualitySeverity.WARNING,
                        message=f"Successful article is missing fields: {', '.join(missing)}.",
                        recommendation="review extraction selectors and source metadata",
                        metadata={"missing_fields": missing},
                    )
                )
    return findings


def _event_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    query = select(NewsEvent).where(NewsEvent.status == EventStatus.ACTIVE)
    if source_id:
        query = query.where(NewsEvent.primary_source_id == source_id)
    findings = []
    for event in db.scalars(query):
        if event.article_count == 0:
            findings.append(
                _finding(
                    run_id,
                    check_name="active_event_zero_articles",
                    scope_type=DataQualityScopeType.EVENT,
                    scope_id=event.id,
                    source_id=event.primary_source_id,
                    severity=DataQualitySeverity.CRITICAL,
                    message="Active event has zero linked articles.",
                    recommendation="review clustering linkage and event refresh behavior",
                )
            )
        if float(event.confidence_score or 0) < LOW_EVENT_CONFIDENCE:
            findings.append(
                _finding(
                    run_id,
                    check_name="active_event_low_confidence",
                    scope_type=DataQualityScopeType.EVENT,
                    scope_id=event.id,
                    source_id=event.primary_source_id,
                    severity=DataQualitySeverity.WARNING,
                    message=f"Active event confidence is {event.confidence_score}.",
                    recommendation="review clustering match details",
                )
            )
    return findings


def _analysis_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    query = select(EventAIAnalysis, NewsEvent).join(
        NewsEvent,
        EventAIAnalysis.event_id == NewsEvent.id,
    )
    if source_id:
        query = query.where(NewsEvent.primary_source_id == source_id)
    findings = []
    for analysis, event in db.execute(query):
        if analysis.status == EventAIAnalysisStatus.FAILED:
            error_message = analysis.error_message or ""
            severity = (
                DataQualitySeverity.WARNING
                if error_message == "missing_ai_api_key"
                else DataQualitySeverity.ERROR
            )
            findings.append(
                _finding(
                    run_id,
                    check_name="failed_ai_analysis",
                    scope_type=DataQualityScopeType.ANALYSIS,
                    scope_id=analysis.id,
                    source_id=event.primary_source_id,
                    severity=severity,
                    message=f"AI analysis failed for event {analysis.event_id}.",
                    recommendation="review AI configuration or provider output",
                    metadata={"error_message": error_message},
                )
            )
    return findings


def _digest_findings(db: Session, run_id: UUID) -> list[DataQualityFinding]:
    findings = []
    for digest in db.scalars(select(Digest).where(Digest.total_selected == 0)):
        successful_event_count = db.scalar(
            select(func.count(EventAIAnalysis.id))
            .join(NewsEvent, EventAIAnalysis.event_id == NewsEvent.id)
            .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS)
            .where(NewsEvent.status == EventStatus.ACTIVE)
            .where(_event_timestamp_filter(digest.window_start, digest.window_end))
        ) or 0
        if successful_event_count > 0:
            findings.append(
                _finding(
                    run_id,
                    check_name="digest_zero_selected_with_candidates",
                    scope_type=DataQualityScopeType.DIGEST,
                    scope_id=digest.id,
                    source_id=None,
                    severity=DataQualitySeverity.WARNING,
                    message=(
                        "Digest has zero selected items while successful analyzed "
                        "events exist in its window."
                    ),
                    recommendation="review digest filters, min_score, and ranking thresholds",
                    metadata={"successful_event_count": successful_event_count},
                )
            )
    return findings


def _orchestration_findings(db: Session, run_id: UUID) -> list[DataQualityFinding]:
    findings = []
    for run in db.scalars(
        select(OrchestrationRun).where(OrchestrationRun.status.in_(["failed", "partial_success"]))
    ):
        findings.append(
            _finding(
                run_id,
                check_name="orchestration_run_not_successful",
                scope_type=DataQualityScopeType.ORCHESTRATION_RUN,
                scope_id=run.id,
                source_id=None,
                severity=(
                    DataQualitySeverity.ERROR
                    if run.status == "failed"
                    else DataQualitySeverity.WARNING
                ),
                message=f"Orchestration run ended with status {run.status}.",
                recommendation="review orchestration run steps and upstream failures",
                metadata={"error_message": run.error_message},
            )
        )
    return findings


def _zero_item_fetch_log_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    query = (
        select(SourceFetchLog.source_id, func.count(SourceFetchLog.id))
        .join(Source, SourceFetchLog.source_id == Source.id)
        .where(Source.fetch_method == FetchMethod.RSS)
        .where(SourceFetchLog.items_found == 0)
        .group_by(SourceFetchLog.source_id)
        .having(func.count(SourceFetchLog.id) >= REPEATED_FETCH_LOG_THRESHOLD)
    )
    if source_id:
        query = query.where(SourceFetchLog.source_id == source_id)
    findings = []
    for log_source_id, count in db.execute(query):
        findings.append(
            _finding(
                run_id,
                check_name="recent_repeated_zero_item_rss_fetch_logs",
                scope_type=DataQualityScopeType.SOURCE,
                scope_id=log_source_id,
                source_id=log_source_id,
                severity=DataQualitySeverity.WARNING,
                message=f"RSS source has {count} zero-item fetch logs.",
                recommendation=(
                    "review feed content, rss_url stability, or ingestion parser behavior"
                ),
                metadata={"zero_item_log_count": count},
            )
        )
    return findings


def _timeout_fetch_log_findings(
    db: Session,
    run_id: UUID,
    *,
    source_id: UUID | None,
) -> list[DataQualityFinding]:
    query = (
        select(SourceFetchLog.source_id, func.count(SourceFetchLog.id))
        .where(func.lower(SourceFetchLog.error_message).contains("timeout"))
        .group_by(SourceFetchLog.source_id)
        .having(func.count(SourceFetchLog.id) >= REPEATED_FETCH_LOG_THRESHOLD)
    )
    if source_id:
        query = query.where(SourceFetchLog.source_id == source_id)
    findings = []
    for log_source_id, count in db.execute(query):
        findings.append(
            _finding(
                run_id,
                check_name="recent_repeated_timeout_fetch_logs",
                scope_type=DataQualityScopeType.SOURCE,
                scope_id=log_source_id,
                source_id=log_source_id,
                severity=DataQualitySeverity.WARNING,
                message=f"Source has {count} timeout fetch logs.",
                recommendation="review source responsiveness, URL stability, or fetch method",
                metadata={"timeout_log_count": count},
            )
        )
    return findings


def _has_manual_notes(source: Source) -> bool:
    return len((source.notes or "").strip()) >= 30


def _finding(
    run_id: UUID,
    *,
    check_name: str,
    scope_type: DataQualityScopeType,
    scope_id: UUID | None,
    source_id: UUID | None,
    severity: DataQualitySeverity,
    message: str,
    recommendation: str | None = None,
    metadata: dict | None = None,
) -> DataQualityFinding:
    return DataQualityFinding(
        run_id=run_id,
        check_name=check_name,
        scope_type=scope_type.value,
        scope_id=scope_id,
        source_id=source_id,
        severity=severity.value,
        message=message,
        recommendation=recommendation,
        finding_metadata=metadata,
    )


def _apply_finding_filters(
    query: Select[tuple[DataQualityFinding]] | Select[tuple[int]],
    filters: dict[str, object],
):
    if filters["run_id"] is not None:
        query = query.where(DataQualityFinding.run_id == filters["run_id"])
    if filters["severity"] is not None:
        query = query.where(DataQualityFinding.severity == filters["severity"])
    elif filters["min_severity"] is not None:
        query = query.where(
            DataQualityFinding.severity.in_(
                severity_values_at_or_above(filters["min_severity"])
            )
        )
    if filters["check_name"] is not None:
        query = query.where(DataQualityFinding.check_name == filters["check_name"])
    if filters["scope_type"] is not None:
        query = query.where(DataQualityFinding.scope_type == filters["scope_type"])
    if filters["source_id"] is not None:
        query = query.where(DataQualityFinding.source_id == filters["source_id"])
    return query


def _apply_source_health_filters(
    query: Select[tuple[SourceHealthCheck]] | Select[tuple[int]],
    filters: dict[str, object],
):
    if filters["source_id"] is not None:
        query = query.where(SourceHealthCheck.source_id == filters["source_id"])
    if filters["status"] is not None:
        query = query.where(SourceHealthCheck.status == filters["status"])
    return query


def _event_timestamp_filter(window_start: datetime, window_end: datetime):
    timestamp = func.coalesce(NewsEvent.published_at, NewsEvent.first_seen_at, NewsEvent.created_at)
    return and_(timestamp >= window_start, timestamp < window_end)


def _now() -> datetime:
    return datetime.now(UTC)


def _elapsed_ms(started: float) -> int:
    return int((monotonic() - started) * 1000)


def _duration_seconds(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds())
