from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import engine
from app.db.session import get_db
from app.main import app
from app.models.ingestion import FetchLogStatus, RawDocument, SourceFetchLog
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.source import SourceCreate
from app.services import ingestion_service
from app.services.http_client import HttpFetchError, HttpFetchResponse
from app.services.ingestion_service import MAX_RSS_ENTRIES_PER_SOURCE, ingest_source
from app.services.source_service import create_source
from app.workers.celery_app import celery_app

SAMPLE_HTML = "<html><head><title>Sample</title></head><body>Phase 2 HTML</body></html>"


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
        "name": f"Ingestion Test Source {suffix}",
        "url": f"https://source.example.com/{suffix}",
        "source_type": SourceType.NEWS_SITE,
        "category": "ingestion-test",
        "region": "Test",
        "priority": 3,
        "fetch_method": FetchMethod.STATIC_HTML,
    }
    payload.update(overrides)
    return create_source(db, SourceCreate(**payload))


def rss_feed(entry_count: int) -> str:
    entries = "\n".join(
        f"""
        <item>
          <title>Entry {index}</title>
          <link>https://news.example.com/articles/{index}</link>
          <description>Summary {index}</description>
          <pubDate>Sat, 30 May 2026 10:{index % 60:02d}:00 GMT</pubDate>
        </item>
        """
        for index in range(entry_count)
    )
    return f"""
    <rss version="2.0">
      <channel>
        <title>Sample Feed</title>
        {entries}
      </channel>
    </rss>
    """


def fake_response(
    url: str,
    text: str,
    *,
    status_code: int = 200,
    content_type: str = "text/html; charset=utf-8",
) -> HttpFetchResponse:
    return HttpFetchResponse(
        url=url,
        status_code=status_code,
        content_type=content_type,
        text=text,
    )


def test_rss_ingestion_stores_raw_documents_and_respects_entry_limit(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(
        db,
        fetch_method=FetchMethod.RSS,
        rss_url="https://feeds.example.com/rss.xml",
    )
    source.failure_count = 2
    db.commit()

    def mock_fetch_url(url: str) -> HttpFetchResponse:
        assert url == "https://feeds.example.com/rss.xml"
        return fake_response(url, rss_feed(55), content_type="application/rss+xml")

    monkeypatch.setattr(ingestion_service, "fetch_url", mock_fetch_url)

    result = ingest_source(db, source.id)

    documents = list(db.scalars(select(RawDocument).where(RawDocument.source_id == source.id)))
    fetch_log = db.get(SourceFetchLog, result.fetch_log_id)
    db.refresh(source)

    assert result.status == FetchLogStatus.SUCCESS
    assert result.items_found == MAX_RSS_ENTRIES_PER_SOURCE
    assert result.items_stored == MAX_RSS_ENTRIES_PER_SOURCE
    assert len(documents) == MAX_RSS_ENTRIES_PER_SOURCE
    assert documents[0].raw_size_bytes == len((documents[0].raw_content or "").encode("utf-8"))
    assert len(documents[0].raw_hash) == 64
    assert documents[0].document_metadata["feed_title"] == "Sample Feed"
    assert fetch_log.status == FetchLogStatus.SUCCESS
    assert source.failure_count == 0
    assert source.last_fetched_at is not None
    assert source.last_success_at is not None


def test_static_html_ingestion_stores_one_raw_document(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)

    monkeypatch.setattr(
        ingestion_service,
        "fetch_url",
        lambda url: fake_response(url, SAMPLE_HTML, content_type="text/html; charset=utf-8"),
    )

    result = ingest_source(db, source.id)
    document = db.scalar(select(RawDocument).where(RawDocument.source_id == source.id))

    assert result.status == FetchLogStatus.SUCCESS
    assert result.items_found == 1
    assert result.items_stored == 1
    assert document is not None
    assert document.raw_content == SAMPLE_HTML
    assert document.content_type == "text/html"
    assert document.raw_size_bytes == len(SAMPLE_HTML.encode("utf-8"))


def test_static_html_unchanged_content_is_not_restored(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)

    monkeypatch.setattr(
        ingestion_service,
        "fetch_url",
        lambda url: fake_response(url, SAMPLE_HTML, content_type="text/html; charset=utf-8"),
    )

    first = ingest_source(db, source.id)
    second = ingest_source(db, source.id)
    documents = list(db.scalars(select(RawDocument).where(RawDocument.source_id == source.id)))

    assert first.items_stored == 1
    assert second.items_stored == 0
    assert second.reason == "unchanged_content"
    assert len(documents) == 1


def test_rss_ingestion_skips_duplicate_url_and_hash(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db, fetch_method=FetchMethod.RSS, rss_url="https://feeds.example.com/rss")
    feed_xml = """<?xml version="1.0"?>
    <rss><channel><title>Feed</title>
    <item><title>Story</title><link>https://news.example.com/story</link>
    <description>Body</description></item>
    </channel></rss>"""

    monkeypatch.setattr(
        ingestion_service,
        "fetch_url",
        lambda url: fake_response(url, feed_xml, content_type="application/rss+xml"),
    )

    first = ingest_source(db, source.id)
    second = ingest_source(db, source.id)
    documents = list(db.scalars(select(RawDocument).where(RawDocument.source_id == source.id)))

    assert first.items_stored == 1
    assert second.items_stored == 0
    assert len(documents) == 1


def test_unsupported_fetch_method_is_skipped_without_network(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db, fetch_method=FetchMethod.MANUAL)

    def fail_if_called(url: str) -> HttpFetchResponse:
        raise AssertionError(f"Unexpected network call to {url}")

    monkeypatch.setattr(ingestion_service, "fetch_url", fail_if_called)

    result = ingest_source(db, source.id)
    documents = list(db.scalars(select(RawDocument).where(RawDocument.source_id == source.id)))
    fetch_log = db.get(SourceFetchLog, result.fetch_log_id)
    db.refresh(source)

    assert result.status == FetchLogStatus.SKIPPED
    assert result.reason == "unsupported_fetch_method"
    assert documents == []
    assert fetch_log.status == FetchLogStatus.SKIPPED
    assert source.last_fetched_at is None
    assert source.last_success_at is None
    assert source.failure_count == 0


def test_failed_ingestion_updates_failure_status(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    previous_success_at = datetime(2026, 5, 30, tzinfo=UTC)
    source.last_success_at = previous_success_at
    db.commit()

    def mock_fetch_url(url: str) -> HttpFetchResponse:
        raise HttpFetchError("connection failed")

    monkeypatch.setattr(ingestion_service, "fetch_url", mock_fetch_url)

    result = ingest_source(db, source.id)
    fetch_log = db.get(SourceFetchLog, result.fetch_log_id)
    db.refresh(source)

    assert result.status == FetchLogStatus.FAILED
    assert result.error_message == "connection failed"
    assert fetch_log.status == FetchLogStatus.FAILED
    assert source.failure_count == 1
    assert source.last_fetched_at is not None
    assert source.last_success_at == previous_success_at


def test_ingestion_api_triggers_and_lists_results(
    api_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    monkeypatch.setattr(
        ingestion_service,
        "fetch_url",
        lambda url: fake_response(url, SAMPLE_HTML, content_type="text/html"),
    )

    run_response = api_client.post(f"/api/v1/ingestion/sources/{source.id}/run")
    assert run_response.status_code == 200
    assert run_response.json()["status"] == FetchLogStatus.SUCCESS

    documents_response = api_client.get(
        "/api/v1/ingestion/raw-documents",
        params={"source_id": str(source.id)},
    )
    assert documents_response.status_code == 200
    assert documents_response.json()["total"] == 1
    assert documents_response.json()["items"][0]["metadata"]["source_url"] == source.url

    logs_response = api_client.get(
        "/api/v1/ingestion/logs",
        params={"source_id": str(source.id), "status": FetchLogStatus.SUCCESS},
    )
    assert logs_response.status_code == 200
    assert logs_response.json()["total"] == 1


def test_ingest_all_sources_skips_unsupported_sources(
    api_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db.execute(update(Source).values(is_active=False))
    db.commit()

    make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    make_source(db, fetch_method=FetchMethod.MANUAL)
    monkeypatch.setattr(
        ingestion_service,
        "fetch_url",
        lambda url: fake_response(url, SAMPLE_HTML, content_type="text/html"),
    )

    response = api_client.post("/api/v1/ingestion/run")

    assert response.status_code == 200
    body = response.json()
    assert body["total_sources"] == 1
    assert body["results"][0]["status"] == FetchLogStatus.SUCCESS


def test_celery_ingestion_tasks_are_registered() -> None:
    assert "app.workers.ingestion_tasks.ingest_source" in celery_app.tasks
    assert "app.workers.ingestion_tasks.ingest_all_sources" in celery_app.tasks
