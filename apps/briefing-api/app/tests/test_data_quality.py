from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import engine
from app.data.source_catalog import all_catalog_sources, validate_source_catalog
from app.db.session import get_db
from app.main import app
from app.models.data_quality import (
    DataQualityFinding,
    DataQualitySeverity,
    SourceHealthCheck,
    SourceHealthStatus,
)
from app.models.ingestion import FetchLogStatus, SourceFetchLog
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.source import SourceCreate
from app.services import data_quality_service
from app.services.data_quality_service import (
    SourceHealthFetchResponse,
    run_data_quality_checks,
    run_source_health_checks,
    severity_values_at_or_above,
)
from app.services.source_service import create_source
from app.workers.celery_app import celery_app


@pytest.fixture
def db() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def api_client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def make_source(db: Session, **overrides: object) -> Source:
    suffix = uuid4()
    payload: dict[str, object] = {
        "name": f"Data Quality Source {suffix}",
        "url": f"https://quality.example.com/{suffix}",
        "source_type": SourceType.NEWS_SITE,
        "category": "gaming",
        "region": "US",
        "priority": 3,
        "fetch_method": FetchMethod.MANUAL,
        "fetch_frequency_minutes": 1440,
        "reliability_score": 0.70,
    }
    payload.update(overrides)
    return create_source(db, SourceCreate(**payload))


def make_catalog_source(**overrides: object) -> SourceCreate:
    payload: dict[str, object] = {
        "name": "Catalog Validation Source",
        "url": f"https://catalog.example.com/{uuid4()}",
        "source_type": SourceType.NEWS_SITE,
        "category": "gaming",
        "region": "US",
        "priority": 3,
        "fetch_method": FetchMethod.MANUAL,
        "fetch_frequency_minutes": 1440,
        "reliability_score": 0.70,
        "notes": "Manual source kept for watchlist coverage until a stable feed is confirmed.",
    }
    payload.update(overrides)
    return SourceCreate(**payload)


def deactivate_existing_sources(db: Session) -> None:
    db.execute(update(Source).values(is_active=False))
    db.commit()


def test_source_catalog_validates_current_catalog() -> None:
    validate_source_catalog()
    assert len(all_catalog_sources()) >= 10


def test_source_catalog_validation_rejects_duplicate_urls() -> None:
    first = make_catalog_source(
        name="Catalog One",
        url="https://catalog.example.com/source",
    )
    duplicate = SourceCreate(**first.model_dump())

    with pytest.raises(ValueError, match="Duplicate source URL"):
        validate_source_catalog([first, duplicate])


def test_source_catalog_validation_rejects_duplicate_rss_urls() -> None:
    first = make_catalog_source(
        name="Catalog RSS One",
        url="https://catalog.example.com/source-one",
        rss_url="https://catalog.example.com/feed.xml",
        fetch_method=FetchMethod.RSS,
        notes="Verified RSS source for automated ingestion.",
    )
    second = make_catalog_source(
        name="Catalog RSS Two",
        url="https://catalog.example.com/source-two",
        rss_url="https://catalog.example.com/feed.xml",
        fetch_method=FetchMethod.RSS,
        notes="Verified RSS source for automated ingestion.",
    )

    with pytest.raises(ValueError, match="Duplicate RSS URL"):
        validate_source_catalog([first, second])


def test_source_catalog_validation_rejects_bad_fetch_method_rss_combo() -> None:
    invalid = make_catalog_source(
        name="Bad Manual RSS",
        url="https://catalog.example.com/manual",
        rss_url="https://catalog.example.com/manual-feed.xml",
        fetch_method=FetchMethod.MANUAL,
    )

    with pytest.raises(ValueError, match="Only RSS fetch_method may define rss_url"):
        validate_source_catalog([invalid])


def test_source_catalog_validation_rejects_manual_source_missing_notes() -> None:
    invalid = make_catalog_source(notes="Too short")

    with pytest.raises(ValueError, match="Manual source is missing activation notes"):
        validate_source_catalog([invalid])


def test_source_catalog_validation_rejects_unknown_category_and_region() -> None:
    invalid_category = make_catalog_source(category="speculative")
    invalid_region = make_catalog_source(region="Atlantis")

    with pytest.raises(ValueError, match="Unknown source category"):
        validate_source_catalog([invalid_category])
    with pytest.raises(ValueError, match="Unknown source region"):
        validate_source_catalog([invalid_region])


def test_source_catalog_validation_rejects_priority_and_reliability_ranges() -> None:
    invalid_priority = make_catalog_source().model_copy(update={"priority": 6})
    invalid_reliability = make_catalog_source().model_copy(
        update={"reliability_score": 1.1}
    )

    with pytest.raises(ValueError, match="Invalid source priority"):
        validate_source_catalog([invalid_priority])
    with pytest.raises(ValueError, match="Invalid source reliability score"):
        validate_source_catalog([invalid_reliability])


def test_severity_values_at_or_above() -> None:
    assert severity_values_at_or_above(DataQualitySeverity.WARNING) == [
        "warning",
        "error",
        "critical",
    ]
    assert severity_values_at_or_above(DataQualitySeverity.CRITICAL) == ["critical"]


def test_source_health_rss_success_without_mutating_ingestion_state(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deactivate_existing_sources(db)
    source = make_source(
        db,
        fetch_method=FetchMethod.RSS,
        rss_url="https://quality.example.com/feed.xml",
    )
    before = (source.last_fetched_at, source.last_success_at, source.failure_count)

    def fake_fetch(url: str) -> SourceHealthFetchResponse:
        assert url == "https://quality.example.com/feed.xml"
        return SourceHealthFetchResponse(
            status_code=200,
            content_size_bytes=144,
            text="<rss><channel><item><title>One</title></item></channel></rss>",
            latency_ms=12,
            final_url=url,
        )

    monkeypatch.setattr(data_quality_service, "fetch_source_health_url", fake_fetch)

    result = run_source_health_checks(db, source_id=source.id)
    db.refresh(source)
    check = result.results[0]

    assert check.status == SourceHealthStatus.HEALTHY
    assert check.item_count == 1
    assert (source.last_fetched_at, source.last_success_at, source.failure_count) == before


def test_source_health_missing_rss_url_and_manual_skip_without_network(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deactivate_existing_sources(db)
    rss_source = make_source(db, fetch_method=FetchMethod.RSS, rss_url=None)
    manual_source = make_source(db, fetch_method=FetchMethod.MANUAL)

    def fail_if_called(url: str) -> SourceHealthFetchResponse:
        raise AssertionError(f"Unexpected source health network call to {url}")

    monkeypatch.setattr(data_quality_service, "fetch_source_health_url", fail_if_called)

    missing_result = run_source_health_checks(db, source_id=rss_source.id)
    manual_result = run_source_health_checks(db, source_id=manual_source.id)

    assert missing_result.results[0].status == SourceHealthStatus.FAILING
    assert missing_result.results[0].recommendation == "add_rss_url_or_change_fetch_method"
    assert manual_result.results[0].status == SourceHealthStatus.SKIPPED
    assert manual_result.results[0].error_reason == "unsupported_fetch_method"


def test_data_quality_run_filters_min_severity_and_sets_source_id(db: Session) -> None:
    deactivate_existing_sources(db)
    source = make_source(db, fetch_method=FetchMethod.RSS, rss_url=None)
    make_source(db, fetch_method=FetchMethod.MANUAL)

    result = run_data_quality_checks(
        db,
        source_id=source.id,
        min_severity=DataQualitySeverity.ERROR,
    )
    findings = list(
        db.scalars(select(DataQualityFinding).where(DataQualityFinding.run_id == result.run.id))
    )

    assert result.run.status == "success"
    assert result.run.total_findings >= 1
    assert all(finding.severity in {"error", "critical"} for finding in findings)
    assert any(finding.check_name == "active_rss_source_missing_rss_url" for finding in findings)
    assert all(
        finding.source_id == source.id for finding in findings if finding.scope_type == "source"
    )


def test_data_quality_flags_repeated_zero_item_rss_fetch_logs(db: Session) -> None:
    deactivate_existing_sources(db)
    source = make_source(
        db,
        fetch_method=FetchMethod.RSS,
        rss_url="https://quality.example.com/feed.xml",
    )
    now = datetime.now(UTC)
    db.add_all(
        [
            SourceFetchLog(
                source_id=source.id,
                status=FetchLogStatus.SUCCESS,
                started_at=now,
                finished_at=now,
                items_found=0,
                items_stored=0,
            )
            for _ in range(3)
        ]
    )
    db.commit()

    result = run_data_quality_checks(db, source_id=source.id)

    assert any(
        finding.check_name == "recent_repeated_zero_item_rss_fetch_logs"
        for finding in result.findings
    )


def test_data_quality_flags_repeated_timeout_fetch_logs(db: Session) -> None:
    deactivate_existing_sources(db)
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    now = datetime.now(UTC)
    db.add_all(
        [
            SourceFetchLog(
                source_id=source.id,
                status=FetchLogStatus.FAILED,
                started_at=now,
                finished_at=now,
                error_message="timeout while fetching source",
                items_found=0,
                items_stored=0,
            )
            for _ in range(3)
        ]
    )
    db.commit()

    result = run_data_quality_checks(db, source_id=source.id)

    assert any(
        finding.check_name == "recent_repeated_timeout_fetch_logs"
        for finding in result.findings
    )


def test_data_quality_api_endpoints(api_client: TestClient, db: Session) -> None:
    deactivate_existing_sources(db)
    source = make_source(db, fetch_method=FetchMethod.RSS, rss_url=None)

    run_response = api_client.post(
        "/api/v1/data-quality/run",
        params={"source_id": str(source.id), "min_severity": "warning"},
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["run"]["id"]

    checks_response = api_client.get(
        "/api/v1/data-quality/checks",
        params={"run_id": run_id, "min_severity": "error"},
    )
    assert checks_response.status_code == 200
    checks = checks_response.json()
    assert checks["total"] >= 1
    assert all(item["severity"] in {"error", "critical"} for item in checks["items"])

    summary_response = api_client.get("/api/v1/data-quality/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["latest_run"]["id"] == run_id


def test_source_health_api_lists_results(
    api_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deactivate_existing_sources(db)
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    monkeypatch.setattr(
        data_quality_service,
        "fetch_source_health_url",
        lambda url: SourceHealthFetchResponse(
            status_code=200,
            content_size_bytes=512,
            text="<html><body>OK</body></html>",
            latency_ms=10,
            final_url=url,
        ),
    )

    run_response = api_client.post(
        "/api/v1/data-quality/source-health/run",
        params={"source_id": str(source.id)},
    )
    assert run_response.status_code == 200
    assert run_response.json()["results"][0]["status"] == "healthy"

    list_response = api_client.get(
        "/api/v1/data-quality/source-health",
        params={"source_id": str(source.id), "status": "healthy"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    stored = db.scalar(select(SourceHealthCheck).where(SourceHealthCheck.source_id == source.id))
    assert stored is not None
    assert stored.health_metadata["network_safety"]["max_response_bytes"] == 1_000_000


def test_data_quality_celery_tasks_are_registered() -> None:
    assert "app.workers.data_quality_tasks.run_data_quality_checks" in celery_app.tasks
    assert "app.workers.data_quality_tasks.check_source_health" in celery_app.tasks
