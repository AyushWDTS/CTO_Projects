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
from app.models.event import EventArticle, EventArticleMatchType, NewsEvent
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.source import SourceCreate
from app.services.clustering_service import (
    cluster_article,
    cluster_by_source,
    cluster_pending_articles,
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


def clean_phase4_data(db: Session) -> None:
    db.execute(delete(EventArticle))
    db.execute(delete(NewsEvent))
    db.execute(delete(Article))
    db.execute(delete(RawDocument))
    db.commit()


def make_source(db: Session, **overrides: object) -> Source:
    suffix = uuid4()
    payload: dict[str, object] = {
        "name": f"Clustering Source {suffix}",
        "url": f"https://source.example.com/{suffix}",
        "source_type": SourceType.NEWS_SITE,
        "category": "gaming",
        "region": "US",
        "priority": 3,
        "fetch_method": FetchMethod.STATIC_HTML,
        "reliability_score": 0.50,
    }
    payload.update(overrides)
    return create_source(db, SourceCreate(**payload))


def make_article(
    db: Session,
    source: Source,
    *,
    title: str = "Casino operator announces new resort expansion",
    clean_text: str = "Casino operator announces a new resort expansion with hotel rooms.",
    canonical_url: str | None = None,
    source_url: str | None = None,
    content_hash: str | None = None,
    published_at: datetime | None = None,
    status: ArticleExtractionStatus = ArticleExtractionStatus.SUCCESS,
) -> Article:
    suffix = uuid4()
    raw_content = clean_text or title
    raw_document = RawDocument(
        source_id=source.id,
        url=source_url or f"https://raw.example.com/{suffix}",
        canonical_url=canonical_url,
        content_type="text/html",
        raw_content=raw_content,
        raw_hash=f"{suffix}".replace("-", "")[:64],
        raw_size_bytes=len(raw_content.encode("utf-8")),
        http_status=200,
        fetched_at=published_at or datetime.now(UTC),
    )
    db.add(raw_document)
    db.flush()

    article = Article(
        raw_document_id=raw_document.id,
        source_id=source.id,
        title=title,
        canonical_url=canonical_url,
        source_url=source_url or raw_document.url,
        content_type="text/html",
        clean_text=clean_text,
        excerpt=clean_text[:300] if clean_text else None,
        published_at=published_at or datetime.now(UTC),
        content_hash=content_hash or f"{suffix}".replace("-", "")[:64],
        extraction_status=status,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def event_link_for_article(db: Session, article: Article) -> EventArticle:
    return db.query(EventArticle).filter(EventArticle.article_id == article.id).one()


def test_exact_canonical_url_grouping_and_match_details(db: Session) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    first = make_article(
        db,
        source,
        canonical_url="https://example.com/story?utm_source=email#section",
        source_url="https://example.com/story?utm_source=email#section",
    )
    second = make_article(
        db,
        source,
        canonical_url="https://example.com/story",
        source_url="https://example.com/story",
    )

    first_result = cluster_article(db, first.id)
    second_result = cluster_article(db, second.id)
    second_link = event_link_for_article(db, second)
    event = db.get(NewsEvent, first_result.event_id)

    assert first_result.created_event is True
    assert second_result.event_id == first_result.event_id
    assert second_result.match_type == EventArticleMatchType.EXACT_URL
    assert event.normalized_canonical_url == "https://example.com/story"
    assert second_link.match_details["normalized_article_canonical_url"] == "https://example.com/story"


def test_exact_source_url_fallback_grouping(db: Session) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    first = make_article(db, source, canonical_url=None, source_url="https://example.com/fallback/")
    second = make_article(
        db,
        source,
        canonical_url=None,
        source_url="https://example.com/fallback?utm_campaign=ignored",
    )

    first_result = cluster_article(db, first.id)
    second_result = cluster_article(db, second.id)

    assert second_result.event_id == first_result.event_id
    assert second_result.match_type == EventArticleMatchType.EXACT_SOURCE_URL


def test_exact_hash_uses_time_and_category_safeguards(db: Session) -> None:
    clean_phase4_data(db)
    first_source = make_source(db, category="gaming", region="US")
    conflicting_source = make_source(db, category="semiconductors", region="US")
    shared_hash = "a" * 64
    first = make_article(
        db,
        first_source,
        canonical_url=None,
        content_hash=shared_hash,
        published_at=datetime(2026, 5, 1, tzinfo=UTC),
    )
    conflicting = make_article(
        db,
        conflicting_source,
        title="Semiconductor fab announces supply chain update",
        clean_text="Semiconductor fab announces a supply chain update for chip materials.",
        canonical_url=None,
        content_hash=shared_hash,
        published_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    first_result = cluster_article(db, first.id)
    conflicting_result = cluster_article(db, conflicting.id)

    assert conflicting_result.event_id != first_result.event_id
    assert conflicting_result.created_event is True


def test_title_and_text_similarity_grouping(db: Session) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    first = make_article(
        db,
        source,
        title="Nevada regulator approves casino license",
        clean_text="Nevada regulator approves casino license after a public hearing in Las Vegas.",
    )
    title_match = make_article(
        db,
        source,
        title="Nevada regulator approves casino license!",
        clean_text="Short different body.",
    )
    text_match = make_article(
        db,
        source,
        title="Different title",
        clean_text="Nevada regulator approves casino license after a public hearing in Las Vegas.",
    )

    first_result = cluster_article(db, first.id)
    title_result = cluster_article(db, title_match.id)
    text_result = cluster_article(db, text_match.id)

    assert title_result.event_id == first_result.event_id
    assert title_result.match_type == EventArticleMatchType.TITLE_SIMILARITY
    assert text_result.event_id == first_result.event_id
    assert text_result.match_type == EventArticleMatchType.TEXT_SIMILARITY


def test_non_duplicate_articles_remain_separate(db: Session) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    first = make_article(
        db,
        source,
        title="Casino revenue rises",
        clean_text="Casino revenue rises.",
    )
    second = make_article(db, source, title="Chip factory opens", clean_text="Chip factory opens.")

    first_result = cluster_article(db, first.id)
    second_result = cluster_article(db, second.id)

    assert first_result.event_id != second_result.event_id
    assert second_result.created_event is True


def test_primary_article_switches_safely_by_source_quality(db: Session) -> None:
    clean_phase4_data(db)
    weak_source = make_source(db, reliability_score=0.20, priority=5)
    strong_source = make_source(db, reliability_score=0.95, priority=1)
    weak = make_article(db, weak_source, canonical_url="https://example.com/primary")
    strong = make_article(db, strong_source, canonical_url="https://example.com/primary")

    weak_result = cluster_article(db, weak.id)
    strong_result = cluster_article(db, strong.id)
    event = db.get(NewsEvent, weak_result.event_id)
    primary_links = db.query(EventArticle).filter_by(event_id=event.id, is_primary=True).all()

    assert strong_result.event_id == weak_result.event_id
    assert event.primary_article_id == strong.id
    assert event.primary_source_id == strong_source.id
    assert len(primary_links) == 1
    assert primary_links[0].article_id == strong.id


def test_idempotency_and_reprocess_zero_article_event_cleanup(db: Session) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    article = make_article(db, source, canonical_url="https://example.com/reprocess")

    first_result = cluster_article(db, article.id)
    second_result = cluster_article(db, article.id)
    old_event_id = first_result.event_id

    assert second_result.status == "already_clustered"
    assert db.get(NewsEvent, old_event_id) is not None

    article.canonical_url = "https://example.com/reprocess-new"
    db.commit()
    reprocess_result = cluster_article(db, article.id, reprocess=True)

    assert reprocess_result.event_id != old_event_id
    assert db.get(NewsEvent, old_event_id) is None


def test_batch_api_filters_and_celery_task_discovery(
    api_client: TestClient,
    db: Session,
) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    make_article(db, source, canonical_url="https://example.com/api-one")
    make_article(db, source, canonical_url="https://example.com/api-one")

    run_response = api_client.post("/api/v1/clustering/run", params={"limit": 10})
    assert run_response.status_code == 200
    assert run_response.json()["total_articles"] == 2

    list_response = api_client.get(
        "/api/v1/events",
        params={"source_id": str(source.id), "category": "gaming", "min_confidence": 0.5},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    event_id = list_response.json()["items"][0]["id"]

    get_response = api_client.get(f"/api/v1/events/{event_id}")
    assert get_response.status_code == 200

    articles_response = api_client.get(f"/api/v1/events/{event_id}/articles")
    assert articles_response.status_code == 200
    assert articles_response.json()["total"] == 2

    source_result = cluster_by_source(db, source.id, limit=10)
    pending_result = cluster_pending_articles(db, limit=10)
    assert source_result.total_articles == 0
    assert pending_result.total_articles == 0
    assert "app.workers.clustering_tasks.cluster_article" in celery_app.tasks
    assert "app.workers.clustering_tasks.cluster_pending_articles" in celery_app.tasks
    assert "app.workers.clustering_tasks.cluster_by_source" in celery_app.tasks


def test_non_success_article_is_skipped(db: Session) -> None:
    clean_phase4_data(db)
    source = make_source(db)
    failed = make_article(db, source, status=ArticleExtractionStatus.FAILED)

    result = cluster_article(db, failed.id)

    assert result.status == "skipped"
    assert result.reason == "article_not_successful"
