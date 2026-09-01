import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, time
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.models.orchestration import (
    OrchestrationRun,
    OrchestrationRunStep,
    OrchestrationRunType,
    OrchestrationStatus,
    OrchestrationStepName,
)
from app.services.clustering_service import cluster_pending_articles
from app.services.demo_pipeline_service import ensure_utc, resolve_demo_fetched_after
from app.services.digest_service import build_digest, resolve_digest_window
from app.services.event_analysis_service import analyze_pending_events
from app.services.ingestion_service import ingest_all_sources
from app.services.normalization_service import normalize_pending_raw_documents
from app.services.priority_pipeline_service import (
    DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    analyze_clustered_priority_sources,
    analyze_priority_sources,
    cluster_priority_sources,
    normalize_priority_sources,
)

DEFAULT_ORCHESTRATION_LIMIT = 200
MAX_ORCHESTRATION_LIMIT = 500
DEFAULT_DIGEST_LIMIT = 15
STEP_SEQUENCE = [
    OrchestrationStepName.INGESTION,
    OrchestrationStepName.NORMALIZATION,
    OrchestrationStepName.CLUSTERING,
    OrchestrationStepName.EVENT_ANALYSIS,
    OrchestrationStepName.DIGEST_BUILD,
]


class OrchestrationRunNotFoundError(Exception):
    pass


class OrchestrationInvalidRequestError(Exception):
    pass


class OrchestrationRunAlreadyActiveError(Exception):
    pass


@dataclass
class PipelineOptions:
    digest_date: date | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    dry_run: bool = True
    skip_ingestion: bool = False
    skip_normalization: bool = False
    skip_clustering: bool = False
    skip_ai: bool = False
    continue_on_ai_failure: bool = False
    refresh_digest: bool = False
    limit: int = DEFAULT_ORCHESTRATION_LIMIT
    digest_limit: int = DEFAULT_DIGEST_LIMIT
    triggered_by: str = "manual"
    run_type: OrchestrationRunType = OrchestrationRunType.MANUAL
    demo_mode: bool = False
    fetched_after: datetime | None = None
    fetched_after_inclusive: bool = False
    watermark_source: str | None = None


def run_daily_pipeline(
    db: Session,
    *,
    digest_date: date | None = None,
    dry_run: bool | None = None,
    skip_ingestion: bool = False,
    skip_normalization: bool = False,
    skip_clustering: bool = False,
    skip_ai: bool = False,
    continue_on_ai_failure: bool = False,
    refresh_digest: bool = False,
    limit: int = DEFAULT_ORCHESTRATION_LIMIT,
    digest_limit: int = DEFAULT_DIGEST_LIMIT,
    triggered_by: str = "manual",
    settings: Settings | None = None,
) -> OrchestrationRun:
    settings = settings or get_settings()
    return _run_pipeline(
        db,
        PipelineOptions(
            digest_date=digest_date,
            dry_run=settings.ORCHESTRATION_DEFAULT_DRY_RUN if dry_run is None else dry_run,
            skip_ingestion=skip_ingestion,
            skip_normalization=skip_normalization,
            skip_clustering=skip_clustering,
            skip_ai=skip_ai,
            continue_on_ai_failure=continue_on_ai_failure,
            refresh_digest=refresh_digest,
            limit=limit,
            digest_limit=digest_limit,
            triggered_by=triggered_by,
            run_type=OrchestrationRunType.DAILY,
        ),
        settings=settings,
    )


def run_demo_pipeline(
    db: Session,
    *,
    digest_date: date | None = None,
    dry_run: bool | None = None,
    skip_ingestion: bool = False,
    continue_on_ai_failure: bool = False,
    limit: int = DEFAULT_ORCHESTRATION_LIMIT,
    digest_limit: int = DEFAULT_DIGEST_LIMIT,
    triggered_by: str = "demo",
    settings: Settings | None = None,
) -> OrchestrationRun:
    """Run ingest → normalize → cluster → analyze → digest on newly fetched content only."""
    settings = settings or get_settings()
    return _run_pipeline(
        db,
        PipelineOptions(
            digest_date=digest_date,
            dry_run=settings.ORCHESTRATION_DEFAULT_DRY_RUN if dry_run is None else dry_run,
            skip_ingestion=skip_ingestion,
            skip_normalization=False,
            skip_clustering=False,
            skip_ai=False,
            continue_on_ai_failure=continue_on_ai_failure,
            refresh_digest=True,
            limit=limit,
            digest_limit=digest_limit,
            triggered_by=triggered_by,
            run_type=OrchestrationRunType.MANUAL,
            demo_mode=True,
        ),
        settings=settings,
    )


def run_pipeline_for_window(
    db: Session,
    *,
    window_start: datetime,
    window_end: datetime,
    dry_run: bool | None = None,
    skip_ingestion: bool = False,
    skip_normalization: bool = False,
    skip_clustering: bool = False,
    skip_ai: bool = False,
    continue_on_ai_failure: bool = False,
    refresh_digest: bool = False,
    limit: int = DEFAULT_ORCHESTRATION_LIMIT,
    digest_limit: int = DEFAULT_DIGEST_LIMIT,
    triggered_by: str = "manual",
    settings: Settings | None = None,
) -> OrchestrationRun:
    settings = settings or get_settings()
    return _run_pipeline(
        db,
        PipelineOptions(
            window_start=window_start,
            window_end=window_end,
            dry_run=settings.ORCHESTRATION_DEFAULT_DRY_RUN if dry_run is None else dry_run,
            skip_ingestion=skip_ingestion,
            skip_normalization=skip_normalization,
            skip_clustering=skip_clustering,
            skip_ai=skip_ai,
            continue_on_ai_failure=continue_on_ai_failure,
            refresh_digest=refresh_digest,
            limit=limit,
            digest_limit=digest_limit,
            triggered_by=triggered_by,
            run_type=OrchestrationRunType.WINDOW,
        ),
        settings=settings,
    )


def run_pipeline_step(
    db: Session,
    run_id: UUID,
    step_name: OrchestrationStepName,
) -> OrchestrationRunStep:
    step = db.scalar(
        select(OrchestrationRunStep).where(
            OrchestrationRunStep.run_id == run_id,
            OrchestrationRunStep.step_name == step_name.value,
        )
    )
    if step is None:
        raise OrchestrationRunNotFoundError("Orchestration step not found.")
    return step


def list_orchestration_runs(
    db: Session,
    *,
    limit: int,
    offset: int,
    run_type: OrchestrationRunType | None = None,
    status: OrchestrationStatus | None = None,
    digest_date: date | None = None,
    triggered_by: str | None = None,
    lock_key: str | None = None,
    idempotency_key: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> tuple[list[OrchestrationRun], int]:
    filters = {
        "run_type": run_type.value if run_type else None,
        "status": status.value if status else None,
        "digest_date": digest_date,
        "triggered_by": triggered_by,
        "lock_key": lock_key,
        "idempotency_key": idempotency_key,
        "created_from": created_from,
        "created_to": created_to,
    }
    query = _apply_run_filters(select(OrchestrationRun), filters).order_by(
        OrchestrationRun.created_at.desc()
    )
    count_query = _apply_run_filters(select(func.count(OrchestrationRun.id)), filters)
    normalized_limit = max(1, min(limit, MAX_ORCHESTRATION_LIMIT))
    rows = list(db.scalars(query.limit(normalized_limit).offset(offset)))
    return rows, db.scalar(count_query) or 0


def get_orchestration_run(db: Session, run_id: UUID) -> OrchestrationRun:
    run = (
        db.execute(
            select(OrchestrationRun)
            .options(joinedload(OrchestrationRun.steps))
            .where(OrchestrationRun.id == run_id)
        )
        .unique()
        .scalar_one_or_none()
    )
    if run is None:
        raise OrchestrationRunNotFoundError("Orchestration run not found.")
    return run


def list_orchestration_run_steps(
    db: Session,
    run_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[OrchestrationRunStep], int]:
    get_orchestration_run(db, run_id)
    normalized_limit = max(1, min(limit, MAX_ORCHESTRATION_LIMIT))
    total = (
        db.scalar(
            select(func.count(OrchestrationRunStep.id)).where(
                OrchestrationRunStep.run_id == run_id
            )
        )
        or 0
    )
    steps = list(
        db.scalars(
            select(OrchestrationRunStep)
            .where(OrchestrationRunStep.run_id == run_id)
            .order_by(OrchestrationRunStep.step_order.asc())
            .limit(normalized_limit)
            .offset(offset)
        )
    )
    return steps, total


def compute_pipeline_keys(
    *,
    run_type: OrchestrationRunType,
    digest_date: date,
    window_start: datetime,
    window_end: datetime,
    limit: int,
    digest_limit: int,
    refresh_digest: bool,
    demo_mode: bool = False,
) -> tuple[str, str]:
    start = _iso(window_start)
    end = _iso(window_end)
    lock_key = f"{run_type.value}:{start}:{end}"
    if demo_mode:
        lock_key = f"demo:{lock_key}"
    idempotency_key = (
        f"{lock_key}:date={digest_date.isoformat()}:limit={limit}:"
        f"digest_limit={digest_limit}:refresh={str(refresh_digest).lower()}"
        f":demo={str(demo_mode).lower()}"
    )
    return lock_key[:255], idempotency_key[:255]


def _run_pipeline(db: Session, options: PipelineOptions, *, settings: Settings) -> OrchestrationRun:
    _validate_options(options, settings)
    resolved_date, resolved_start, resolved_end = resolve_digest_window(
        digest_date=options.digest_date,
        window_start=options.window_start,
        window_end=options.window_end,
    )
    options.limit = max(1, min(options.limit, MAX_ORCHESTRATION_LIMIT))
    options.digest_limit = max(1, min(options.digest_limit, 50))
    lock_key, idempotency_key = compute_pipeline_keys(
        run_type=options.run_type,
        digest_date=resolved_date,
        window_start=resolved_start,
        window_end=resolved_end,
        limit=options.limit,
        digest_limit=options.digest_limit,
        refresh_digest=options.refresh_digest,
        demo_mode=options.demo_mode,
    )
    lock_acquired = _try_advisory_lock(db, lock_key)
    if not lock_acquired:
        raise OrchestrationRunAlreadyActiveError("run_already_active")

    run = _create_run(
        db,
        options=options,
        digest_date=resolved_date,
        window_start=resolved_start,
        window_end=resolved_end,
        lock_key=lock_key,
        idempotency_key=idempotency_key,
    )
    _log(f"Pipeline started run_id={run.id} date={resolved_date} demo={options.demo_mode}")
    partial_success = False
    try:
        _execute_pipeline(db, run, options)
    except Exception as exc:
        run.status = OrchestrationStatus.FAILED.value
        run.error_message = str(exc)
        _finish_run(run)
        db.commit()
    else:
        partial_success = any(
            step.status == OrchestrationStatus.FAILED.value
            for step in run.steps
            if step.step_name == OrchestrationStepName.EVENT_ANALYSIS.value
        )
        run.status = (
            OrchestrationStatus.PARTIAL_SUCCESS.value
            if partial_success
            else OrchestrationStatus.SUCCESS.value
        )
        _finish_run(run)
        db.commit()
    finally:
        _release_advisory_lock(db, lock_key)

    return get_orchestration_run(db, run.id)


def _execute_pipeline(
    db: Session,
    run: OrchestrationRun,
    options: PipelineOptions,
) -> None:
    run.status = OrchestrationStatus.RUNNING.value
    run.started_at = datetime.now(UTC)
    if options.demo_mode:
        fetched_after, watermark_source, inclusive = resolve_demo_fetched_after(
            db,
            run_started_at=run.started_at,
            exclude_run_id=run.id,
        )
        options.fetched_after = fetched_after
        options.fetched_after_inclusive = inclusive
        options.watermark_source = watermark_source
        _log(
            f"Demo watermark: fetched_after={ensure_utc(fetched_after).isoformat()} "
            f"source={watermark_source} inclusive={inclusive}"
        )
        run.run_metadata = {
            **(run.run_metadata or {}),
            "demo_mode": True,
            "fetched_after": ensure_utc(fetched_after).isoformat(),
            "fetched_after_inclusive": inclusive,
            "watermark_source": watermark_source,
        }
    db.commit()
    digest_id: UUID | None = None
    for step_name in STEP_SEQUENCE:
        step = _get_step(run, step_name)
        if _should_skip(step_name, options):
            _skip_step(db, step, _skip_reason(step_name, options))
            continue
        try:
            result = _run_step(db, run, step, options, digest_id)
            if step_name == OrchestrationStepName.DIGEST_BUILD:
                digest_id = UUID(result["digest_id"])
                run.digest_id = digest_id
                db.commit()
        except Exception as exc:
            _fail_step(db, step, exc)
            if step_name == OrchestrationStepName.EVENT_ANALYSIS and options.continue_on_ai_failure:
                continue
            mark_remaining_steps_skipped(
                db,
                run.id,
                after_step_order=step.step_order,
                reason="upstream_failed",
                failed_step=step_name.value,
            )
            raise


def _run_step(
    db: Session,
    run: OrchestrationRun,
    step: OrchestrationRunStep,
    options: PipelineOptions,
    digest_id: UUID | None,
) -> dict:
    _start_step(db, step)
    handlers: dict[OrchestrationStepName, Callable[[], dict]] = {
        OrchestrationStepName.INGESTION: lambda: _ingestion_step(db),
        OrchestrationStepName.NORMALIZATION: lambda: _normalization_step(db, options),
        OrchestrationStepName.CLUSTERING: lambda: _clustering_step(db, options),
        OrchestrationStepName.EVENT_ANALYSIS: lambda: _event_analysis_step(db, options),
        OrchestrationStepName.DIGEST_BUILD: lambda: _digest_step(db, run, options),
    }
    result = handlers[OrchestrationStepName(step.step_name)]()
    _finish_step(db, step, result)
    return result


def _ingestion_step(db: Session) -> dict:
    result = ingest_all_sources(db)
    return {
        "items_processed": result.total_sources,
        "items_created": sum(item.items_stored for item in result.results),
        "items_failed": sum(1 for item in result.results if item.status == "failed"),
        "metadata": result.model_dump(mode="json"),
    }


def _normalization_step(db: Session, options: PipelineOptions) -> dict:
    fetched_after = options.fetched_after if options.demo_mode else None
    if options.demo_mode:
        result = normalize_pending_raw_documents(
            db,
            limit=options.limit,
            fetched_after=fetched_after,
            fetched_after_inclusive=options.fetched_after_inclusive,
        )
        failed = sum(1 for item in result.results if item.status == "failed")
        return {
            "items_processed": result.total_raw_documents,
            "items_created": sum(1 for item in result.results if item.article_id is not None),
            "items_failed": failed,
            "metadata": {
                "demo_mode": True,
                "fetched_after": ensure_utc(fetched_after).isoformat() if fetched_after else None,
                "watermark_source": options.watermark_source,
                "global": result.model_dump(mode="json"),
                "priority_first": False,
            },
        }

    priority_limit = min(options.limit, DEFAULT_PRIORITY_PER_SOURCE_LIMIT)
    priority = normalize_priority_sources(
        db,
        limit_per_source=priority_limit,
    )
    result = normalize_pending_raw_documents(db, limit=options.limit)
    failed = sum(1 for item in result.results if item.status == "failed")
    priority_created = sum(item["items_created"] for item in priority["results"])
    return {
        "items_processed": result.total_raw_documents + sum(
            item["items_processed"] for item in priority["results"]
        ),
        "items_created": sum(1 for item in result.results if item.article_id is not None)
        + priority_created,
        "items_failed": failed + sum(item["items_failed"] for item in priority["results"]),
        "metadata": {
            "global": result.model_dump(mode="json"),
            "priority_sources": priority,
            "priority_first": True,
        },
    }


def _clustering_step(db: Session, options: PipelineOptions) -> dict:
    fetched_after = options.fetched_after if options.demo_mode else None
    if options.demo_mode:
        result = cluster_pending_articles(
            db,
            limit=options.limit,
            fetched_after=fetched_after,
            fetched_after_inclusive=options.fetched_after_inclusive,
        )
        return {
            "items_processed": result.total_articles,
            "items_created": result.created_events,
            "items_failed": 0,
            "metadata": {
                "demo_mode": True,
                "fetched_after": ensure_utc(fetched_after).isoformat() if fetched_after else None,
                "watermark_source": options.watermark_source,
                "global": result.model_dump(mode="json"),
                "priority_first": False,
            },
        }

    priority_limit = min(options.limit, DEFAULT_PRIORITY_PER_SOURCE_LIMIT)
    priority = cluster_priority_sources(
        db,
        limit_per_source=priority_limit,
    )
    result = cluster_pending_articles(db, limit=options.limit)
    priority_created = sum(item["created_events"] for item in priority["results"])
    return {
        "items_processed": result.total_articles + sum(
            item["items_processed"] for item in priority["results"]
        ),
        "items_created": result.created_events + priority_created,
        "items_failed": 0,
        "metadata": {
            "global": result.model_dump(mode="json"),
            "priority_sources": priority,
            "priority_first": True,
        },
    }


def _event_analysis_step(db: Session, options: PipelineOptions) -> dict:
    fetched_after = options.fetched_after if options.demo_mode else None
    if options.demo_mode:
        result = analyze_pending_events(
            db,
            limit=options.limit,
            fetched_after=fetched_after,
            fetched_after_inclusive=options.fetched_after_inclusive,
        )
        if result.failed:
            raise RuntimeError("event_analysis_failed")
        return {
            "items_processed": result.total_events,
            "items_created": result.analyzed,
            "items_failed": 0,
            "metadata": {
                "demo_mode": True,
                "fetched_after": ensure_utc(fetched_after).isoformat() if fetched_after else None,
                "watermark_source": options.watermark_source,
                "global": result.model_dump(mode="json"),
                "priority_first": False,
            },
        }

    priority_limit = min(options.limit, DEFAULT_PRIORITY_PER_SOURCE_LIMIT)
    clustered = analyze_clustered_priority_sources(
        db,
        limit_per_source=priority_limit,
    )
    priority = analyze_priority_sources(
        db,
        limit_per_source=priority_limit,
    )
    result = analyze_pending_events(db, limit=options.limit)
    total_failed = result.failed + priority["total_failed"] + clustered["total_failed"]
    if total_failed:
        raise RuntimeError("event_analysis_failed")
    return {
        "items_processed": result.total_events
        + sum(item.get("items_processed", 0) for item in priority["results"])
        + sum(item.get("items_processed", 0) for item in clustered["results"]),
        "items_created": result.analyzed
        + sum(item.get("analyzed", 0) for item in priority["results"])
        + sum(item.get("analyzed", 0) for item in clustered["results"]),
        "items_failed": 0,
        "metadata": {
            "global": result.model_dump(mode="json"),
            "clustered_priority_sources": clustered,
            "priority_sources": priority,
            "priority_first": True,
        },
    }


def _digest_step(db: Session, run: OrchestrationRun, options: PipelineOptions) -> dict:
    window_start = run.window_start
    window_end = run.window_end
    fetched_after = options.fetched_after if options.demo_mode else None
    if options.demo_mode and fetched_after is not None:
        target_date = run.digest_date
        window_start = datetime.combine(target_date, time.min, tzinfo=UTC)
        window_end = window_start + timedelta(days=1)

    digest = build_digest(
        db,
        digest_date=run.digest_date,
        window_start=window_start,
        window_end=window_end,
        limit=options.digest_limit,
        refresh=options.refresh_digest,
        include_low=False,
        fetched_after=fetched_after,
        fetched_after_inclusive=options.fetched_after_inclusive,
    )
    return {
        "digest_id": str(digest.id),
        "items_processed": digest.total_candidates,
        "items_created": digest.total_selected,
        "items_failed": 0,
        "metadata": {
            "digest_id": str(digest.id),
            "total_candidates": digest.total_candidates,
            "total_selected": digest.total_selected,
            "demo_mode": options.demo_mode,
            "fetched_after": ensure_utc(fetched_after).isoformat() if fetched_after else None,
            "digest_window_start": ensure_utc(window_start).isoformat(),
            "digest_window_end": ensure_utc(window_end).isoformat(),
        },
    }






def _create_run(
    db: Session,
    *,
    options: PipelineOptions,
    digest_date: date,
    window_start: datetime,
    window_end: datetime,
    lock_key: str,
    idempotency_key: str,
) -> OrchestrationRun:
    run = OrchestrationRun(
        run_type=options.run_type.value,
        digest_date=digest_date,
        window_start=window_start,
        window_end=window_end,
        lock_key=lock_key,
        idempotency_key=idempotency_key,
        triggered_by=options.triggered_by,
        dry_run=options.dry_run,
        continue_on_ai_failure=options.continue_on_ai_failure,
        run_metadata={
            "limit": options.limit,
            "digest_limit": options.digest_limit,
            "refresh_digest": options.refresh_digest,
            "skip_ingestion": options.skip_ingestion,
            "skip_normalization": options.skip_normalization,
            "skip_clustering": options.skip_clustering,
            "skip_ai": options.skip_ai,
            "demo_mode": options.demo_mode,
        },
    )
    db.add(run)
    db.flush()
    for index, step_name in enumerate(STEP_SEQUENCE, start=1):
        db.add(
            OrchestrationRunStep(
                run_id=run.id,
                step_name=step_name.value,
                step_order=index,
            )
        )
    db.commit()
    db.refresh(run)
    _ = run.steps
    return run


def _log(msg: str) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[pipeline {ts}] {msg}", file=sys.stderr, flush=True)


def _start_step(db: Session, step: OrchestrationRunStep) -> None:
    step.status = OrchestrationStatus.RUNNING.value
    step.started_at = datetime.now(UTC)
    db.commit()
    _log(f"START  {step.step_name}")


def _finish_step(db: Session, step: OrchestrationRunStep, result: dict) -> None:
    step.status = OrchestrationStatus.SUCCESS.value
    step.items_processed = result.get("items_processed")
    step.items_created = result.get("items_created")
    step.items_failed = result.get("items_failed")
    step.step_metadata = result.get("metadata")
    _finish_step_timestamps(step)
    db.commit()
    dur = step.duration_seconds or 0
    processed = result.get("items_processed", 0)
    created = result.get("items_created", 0)
    _log(f"DONE   {step.step_name} ({dur}s) processed={processed} created={created}")


def _fail_step(db: Session, step: OrchestrationRunStep, exc: Exception) -> None:
    step.status = OrchestrationStatus.FAILED.value
    step.error_message = str(exc)
    _finish_step_timestamps(step)
    db.commit()
    _log(f"FAILED {step.step_name}: {exc}")


def mark_remaining_steps_skipped(
    db: Session,
    run_id: UUID,
    *,
    after_step_order: int,
    reason: str = "upstream_failed",
    failed_step: str,
) -> None:
    now = datetime.now(UTC)
    steps = db.scalars(
        select(OrchestrationRunStep)
        .where(
            OrchestrationRunStep.run_id == run_id,
            OrchestrationRunStep.step_order > after_step_order,
            OrchestrationRunStep.status == OrchestrationStatus.PENDING.value,
        )
        .order_by(OrchestrationRunStep.step_order.asc())
    )
    for step in steps:
        step.status = OrchestrationStatus.SKIPPED.value
        step.finished_at = now
        step.duration_seconds = 0 if step.started_at is None else step.duration_seconds
        step.step_metadata = {"reason": reason, "failed_step": failed_step}
    db.commit()


def _skip_step(db: Session, step: OrchestrationRunStep, reason: str) -> None:
    now = datetime.now(UTC)
    step.status = OrchestrationStatus.SKIPPED.value
    step.started_at = now
    step.finished_at = now
    step.duration_seconds = 0
    step.step_metadata = {"reason": reason}
    db.commit()


def _finish_step_timestamps(step: OrchestrationRunStep) -> None:
    step.finished_at = datetime.now(UTC)
    if step.started_at:
        step.duration_seconds = max(0, int((step.finished_at - step.started_at).total_seconds()))


def _finish_run(run: OrchestrationRun) -> None:
    run.finished_at = datetime.now(UTC)
    if run.started_at:
        run.duration_seconds = max(0, int((run.finished_at - run.started_at).total_seconds()))


def _should_skip(
    step_name: OrchestrationStepName,
    options: PipelineOptions,
) -> bool:
    return (
        (step_name == OrchestrationStepName.INGESTION and options.skip_ingestion)
        or (step_name == OrchestrationStepName.NORMALIZATION and options.skip_normalization)
        or (step_name == OrchestrationStepName.CLUSTERING and options.skip_clustering)
        or (step_name == OrchestrationStepName.EVENT_ANALYSIS and options.skip_ai)
    )


def _skip_reason(
    step_name: OrchestrationStepName,
    options: PipelineOptions,
) -> str:
    return "requested_skip"


def _validate_options(options: PipelineOptions, settings: Settings) -> None:
    if (options.window_start is None) != (options.window_end is None):
        raise OrchestrationInvalidRequestError(
            "window_start and window_end must be provided together"
        )
    if options.window_start and options.window_end and options.window_start >= options.window_end:
        raise OrchestrationInvalidRequestError("window_start must be before window_end")


def _get_step(run: OrchestrationRun, step_name: OrchestrationStepName) -> OrchestrationRunStep:
    for step in run.steps:
        if step.step_name == step_name.value:
            return step
    raise OrchestrationRunNotFoundError("Orchestration step not found.")


def _try_advisory_lock(db: Session, lock_key: str) -> bool:
    return bool(
        db.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": lock_key},
        )
    )


def _release_advisory_lock(db: Session, lock_key: str) -> None:
    db.execute(text("SELECT pg_advisory_unlock(hashtext(:lock_key))"), {"lock_key": lock_key})
    db.commit()


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _apply_run_filters(query: Select, filters: dict[str, Any]) -> Select:
    if filters["run_type"] is not None:
        query = query.where(OrchestrationRun.run_type == filters["run_type"])
    if filters["status"] is not None:
        query = query.where(OrchestrationRun.status == filters["status"])
    if filters["digest_date"] is not None:
        query = query.where(OrchestrationRun.digest_date == filters["digest_date"])
    if filters["triggered_by"] is not None:
        query = query.where(OrchestrationRun.triggered_by == filters["triggered_by"])
    if filters["lock_key"] is not None:
        query = query.where(OrchestrationRun.lock_key == filters["lock_key"])
    if filters["idempotency_key"] is not None:
        query = query.where(OrchestrationRun.idempotency_key == filters["idempotency_key"])
    if filters["created_from"] is not None:
        query = query.where(OrchestrationRun.created_at >= filters["created_from"])
    if filters["created_to"] is not None:
        query = query.where(OrchestrationRun.created_at <= filters["created_to"])
    return query
