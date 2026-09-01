from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.database import engine
from app.db.session import get_db
from app.main import app
from app.models.article import Article, ArticleExtractionStatus
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.source import SourceCreate
from app.services.normalization_service import (
    normalize_by_source,
    normalize_pending_raw_documents,
    normalize_raw_document,
    reprocess_failed_normalizations,
)
from app.services.source_service import create_source
from app.workers.celery_app import celery_app

HTML_DOCUMENT = """
<html lang="en">
  <head>
    <link rel="canonical" href="https://example.com/canonical-article" />
    <meta property="og:title" content="Canonical HTML Title" />
    <meta name="author" content="Jane Editor" />
    <meta property="article:published_time" content="2026-05-30T10:00:00+00:00" />
  </head>
  <body>
    <header>Navigation</header>
    <article>
      <h1>Fallback Heading</h1>
      <p>First paragraph of useful article text.</p>
      <p>Second paragraph with more deterministic content.</p>
    </article>
    <script>window.noise = true;</script>
  </body>
</html>
"""


def db_fixture() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def api_client_fixture(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    yield from db_fixture()


@pytest.fixture
def api_client(db: Session) -> Generator[TestClient, None, None]:
    yield from api_client_fixture(db)


def make_source(db: Session, **overrides: object) -> Source:
    suffix = uuid4()
    payload: dict[str, object] = {
        "name": f"Normalization Test Source {suffix}",
        "url": f"https://source.example.com/{suffix}",
        "source_type": SourceType.NEWS_SITE,
        "category": "normalization-test",
        "region": "Test",
        "priority": 3,
        "fetch_method": FetchMethod.STATIC_HTML,
    }
    payload.update(overrides)
    return create_source(db, SourceCreate(**payload))


def make_raw_document(
    db: Session,
    source: Source,
    *,
    raw_content: str | None = HTML_DOCUMENT,
    content_type: str | None = "text/html",
    url: str | None = None,
    canonical_url: str | None = None,
    metadata: dict | None = None,
) -> RawDocument:
    document = RawDocument(
        source_id=source.id,
        url=url or f"https://raw.example.com/{uuid4()}",
        canonical_url=canonical_url,
        content_type=content_type,
        raw_content=raw_content,
        raw_hash="test-raw-hash",
        raw_size_bytes=len((raw_content or "").encode("utf-8")),
        http_status=200,
        fetched_at=datetime.now(UTC),
        document_metadata=metadata,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def test_static_html_normalization_extracts_article_fields(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    document = make_raw_document(db, source)

    result = normalize_raw_document(db, document.id)
    article = db.get(Article, result.article_id)

    assert result.status == ArticleExtractionStatus.SUCCESS
    assert article.title == "Canonical HTML Title"
    assert article.canonical_url == "https://example.com/canonical-article"
    assert article.author == "Jane Editor"
    assert article.published_at is not None
    assert article.language == "en"
    assert "First paragraph of useful article text." in article.clean_text
    assert "window.noise" not in article.clean_text
    assert article.excerpt == article.clean_text[:300]
    assert len(article.content_hash) == 64
    assert article.article_metadata["extraction_path"] == "static_html"


def test_rss_normalization_uses_source_fetch_method_not_content_type(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.RSS, rss_url="https://feeds.example.com/rss")
    document = make_raw_document(
        db,
        source,
        raw_content="<p>RSS summary body</p>",
        content_type="text/html",
        canonical_url="https://news.example.com/story",
        metadata={"entry_title": "RSS Entry Title", "published": "Sat, 30 May 2026 10:00:00 GMT"},
    )

    result = normalize_raw_document(db, document.id)
    article = db.get(Article, result.article_id)

    assert result.status == ArticleExtractionStatus.SUCCESS
    assert article.title == "RSS Entry Title"
    assert article.canonical_url == "https://news.example.com/story"
    assert article.clean_text == "RSS summary body"
    assert article.published_at is not None
    assert article.article_metadata["extraction_path"] == "rss"


def test_unsupported_fetch_method_creates_skipped_article(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.MANUAL)
    document = make_raw_document(db, source, content_type="text/html")

    result = normalize_raw_document(db, document.id)
    article = db.get(Article, result.article_id)

    assert result.status == ArticleExtractionStatus.SKIPPED
    assert result.reason == "unsupported_fetch_method"
    assert article.extraction_status == ArticleExtractionStatus.SKIPPED
    assert article.extraction_error == "unsupported_fetch_method"
    assert article.article_metadata["source_fetch_method"] == FetchMethod.MANUAL.value


def test_empty_raw_content_fails_cleanly(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    document = make_raw_document(db, source, raw_content=None)

    result = normalize_raw_document(db, document.id)
    article = db.get(Article, result.article_id)

    assert result.status == ArticleExtractionStatus.FAILED
    assert result.reason == "empty_raw_content"
    assert article.extraction_status == ArticleExtractionStatus.FAILED


def test_bad_html_is_tolerated(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    document = make_raw_document(db, source, raw_content="<html><title>Broken<title><p>Useful")

    result = normalize_raw_document(db, document.id)
    article = db.get(Article, result.article_id)

    assert result.status == ArticleExtractionStatus.SUCCESS
    assert "Useful" in article.clean_text


def test_normalization_is_idempotent_per_raw_document(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    document = make_raw_document(db, source)

    first_result = normalize_raw_document(db, document.id)
    second_result = normalize_raw_document(db, document.id)

    assert first_result.article_id == second_result.article_id


def test_exact_duplicate_is_marked_without_semantic_deduplication(db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    first_document = make_raw_document(db, source, url="https://raw.example.com/first")
    second_document = make_raw_document(db, source, url="https://raw.example.com/second")

    first_result = normalize_raw_document(db, first_document.id)
    second_result = normalize_raw_document(db, second_document.id)
    second_article = db.get(Article, second_result.article_id)

    assert first_result.status == ArticleExtractionStatus.SUCCESS
    assert second_result.status == ArticleExtractionStatus.EXACT_DUPLICATE
    assert second_article.duplicate_of_article_id == first_result.article_id


def test_batch_and_reprocess_paths(db: Session) -> None:
    db.execute(delete(Article))
    db.execute(delete(RawDocument))
    db.commit()

    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    make_raw_document(db, source)
    failed_document = make_raw_document(db, source, raw_content=None)

    pending_result = normalize_pending_raw_documents(db, limit=100)
    reprocess_result = reprocess_failed_normalizations(db, limit=100)
    source_result = normalize_by_source(db, source.id, limit=100)

    assert pending_result.total_raw_documents == 2
    assert {result.status for result in pending_result.results} == {
        ArticleExtractionStatus.SUCCESS,
        ArticleExtractionStatus.FAILED,
    }
    assert reprocess_result.total_raw_documents == 1
    assert reprocess_result.results[0].raw_document_id == failed_document.id
    assert source_result.total_raw_documents == 0


def test_normalization_api_and_article_filters(api_client: TestClient, db: Session) -> None:
    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    document = make_raw_document(db, source, content_type="text/html")

    run_response = api_client.post(f"/api/v1/normalization/raw-documents/{document.id}/run")
    assert run_response.status_code == 200
    article_id = run_response.json()["article_id"]

    list_response = api_client.get(
        "/api/v1/articles",
        params={
            "source_id": str(source.id),
            "status": ArticleExtractionStatus.SUCCESS.value,
            "category": "normalization-test",
            "region": "Test",
            "content_type": "text/html",
        },
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["metadata"]["extraction_path"] == "static_html"

    get_response = api_client.get(f"/api/v1/articles/{article_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == article_id


def test_normalization_batch_api(api_client: TestClient, db: Session) -> None:
    db.execute(delete(Article))
    db.execute(delete(RawDocument))
    db.commit()

    source = make_source(db, fetch_method=FetchMethod.STATIC_HTML)
    make_raw_document(db, source)

    run_response = api_client.post("/api/v1/normalization/run", params={"limit": 100})
    source_response = api_client.post(
        f"/api/v1/normalization/sources/{source.id}/run",
        params={"limit": 100},
    )
    failed_response = api_client.post(
        "/api/v1/normalization/reprocess-failed",
        params={"limit": 100},
    )

    assert run_response.status_code == 200
    assert run_response.json()["total_raw_documents"] == 1
    assert source_response.status_code == 200
    assert source_response.json()["total_raw_documents"] == 0
    assert failed_response.status_code == 200
    assert failed_response.json()["total_raw_documents"] == 0


def test_celery_normalization_tasks_are_registered() -> None:
    assert "app.workers.normalization_tasks.normalize_raw_document" in celery_app.tasks
    assert "app.workers.normalization_tasks.normalize_pending_raw_documents" in celery_app.tasks
    assert "app.workers.normalization_tasks.normalize_by_source" in celery_app.tasks
    assert "app.workers.normalization_tasks.reprocess_failed_normalizations" in celery_app.tasks
