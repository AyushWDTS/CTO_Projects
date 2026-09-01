from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.data.priority_pipeline_sources import PRIORITY_PIPELINE_SOURCE_NAMES
from app.models.article import Article, ArticleExtractionStatus
from app.models.event import EventArticle, EventArticleMatchType, NewsEvent
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod, Source, SourceType
from app.services.priority_pipeline_service import (
    _normalization_root_cause,
    _starvation_diagnosis,
    build_priority_funnel_report,
    cluster_priority_sources,
    normalize_priority_sources,
    resolve_priority_sources,
)
from app.tests.test_ingestion import make_source


def _priority_source(db: Session, name: str) -> Source:
    return make_source(
        db,
        name=name,
        url=f"https://example.com/{name.lower().replace(' ', '-')}",
        fetch_method=FetchMethod.RSS,
        source_type=SourceType.NEWS_SITE,
        category="technology",
    )


def test_resolve_priority_sources_returns_configured_names(db: Session) -> None:
    configured = _priority_source(db, "RFID Journal")
    _priority_source(db, "Unrelated Feed")
    db.commit()

    resolved = resolve_priority_sources(db)
    assert len(resolved) == 1
    assert resolved[0].id == configured.id


def test_starvation_diagnosis_detects_clustering_backlog() -> None:
    diagnosis = _starvation_diagnosis(
        raw_ingested=5,
        pending_normalization=0,
        normalization_success=5,
        normalization_failed=0,
        clustered=0,
        analyzed=0,
        all_time_unclustered_success=5,
        unclustered_global=350,
        global_batch_limit=200,
    )
    assert diagnosis == "likely_batch_starvation_at_clustering"


def test_build_priority_funnel_report_counts_pipeline_stages(db: Session) -> None:
    source = _priority_source(db, "Everi News")
    window_start = datetime(2026, 6, 24, tzinfo=UTC)
    window_end = window_start + timedelta(days=1)

    raw_document = RawDocument(
        source_id=source.id,
        url="https://example.com/everi/1",
        canonical_url="https://example.com/everi/1",
        content_type="text/html",
        raw_content="<p>Everi smart table release</p>",
        raw_hash="hash-everi-1",
        raw_size_bytes=32,
        fetched_at=window_start + timedelta(hours=1),
    )
    db.add(raw_document)
    db.flush()

    article = Article(
        raw_document_id=raw_document.id,
        source_id=source.id,
        title="Everi smart table release",
        canonical_url=raw_document.url,
        source_url=raw_document.url,
        clean_text="Everi smart table release",
        excerpt="Everi smart table release",
        content_hash="content-everi-1",
        extraction_status=ArticleExtractionStatus.SUCCESS,
    )
    db.add(article)
    db.flush()

    event = NewsEvent(
        canonical_title=article.title,
        primary_article_id=article.id,
        primary_source_id=source.id,
        event_key=f"everi-{uuid4()}",
        published_at=window_start + timedelta(hours=1),
        first_seen_at=window_start + timedelta(hours=1),
        article_count=1,
        source_count=1,
    )
    db.add(event)
    db.flush()
    db.add(
        EventArticle(
            event_id=event.id,
            article_id=article.id,
            source_id=source.id,
            match_type=EventArticleMatchType.MANUAL,
            similarity_score=Decimal("1.000"),
            confidence_score=Decimal("1.000"),
            is_primary=True,
        )
    )
    db.commit()

    report = build_priority_funnel_report(
        db,
        window_start=window_start,
        window_end=window_end,
        source_names=("Everi News", "Missing Source"),
        global_batch_limit=200,
    )

    everi = next(row for row in report["sources"] if row["source_name"] == "Everi News")
    missing = next(row for row in report["sources"] if row["source_name"] == "Missing Source")

    assert everi["raw_ingested"] == 1
    assert everi["normalization_success"] == 1
    assert everi["clustered"] == 1
    assert everi["analyzed"] == 0
    assert everi["starvation_diagnosis"] == "likely_batch_starvation_at_analysis"
    diagnostic = everi.get("analysis_diagnostic") or {}
    assert diagnostic.get("pending_analysis_events") == 1
    assert diagnostic.get("clustered_events_all_time") == 1
    assert diagnostic.get("analysis_drop_off") == "clustering_to_analysis_gap"
    assert missing["status"] == "not_configured"


def test_normalize_and_cluster_priority_sources_run_per_source(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _priority_source(db, "Tangam Systems")
    db.commit()

    calls: list[str] = []

    def fake_normalize(db, source_id, limit=50):
        calls.append(f"normalize:{source_id}")
        from app.schemas.normalization import NormalizationBatchResult

        return NormalizationBatchResult(total_raw_documents=0, results=[])

    def fake_cluster(db, source_id, limit=50, reprocess=False):
        calls.append(f"cluster:{source_id}")
        from app.schemas.clustering import ClusteringBatchResult

        return ClusteringBatchResult(total_articles=0, linked_articles=0)

    monkeypatch.setattr(
        "app.services.priority_pipeline_service.normalize_by_source",
        fake_normalize,
    )
    monkeypatch.setattr(
        "app.services.priority_pipeline_service.cluster_by_source",
        fake_cluster,
    )

    normalize_priority_sources(db, source_names=("Tangam Systems",))
    cluster_priority_sources(db, source_names=("Tangam Systems",))

    assert calls == [f"normalize:{source.id}", f"cluster:{source.id}"]


def test_normalization_root_cause_detects_global_backlog() -> None:
    cause = _normalization_root_cause(
        pending_normalization=0,
        all_time_pending_normalization=1096,
        normalization_success=0,
        normalization_failed=0,
        normalization_duplicate=0,
        clustered=0,
        analyzed=0,
        fetch_method="rss",
    )
    assert cause.startswith("global_normalization_backlog")


def test_normalization_root_cause_detects_static_html_duplicates() -> None:
    cause = _normalization_root_cause(
        pending_normalization=0,
        all_time_pending_normalization=0,
        normalization_success=0,
        normalization_failed=0,
        normalization_duplicate=3,
        clustered=0,
        analyzed=0,
        fetch_method="static_html",
    )
    assert "static_html_repeat_snapshots" in cause


def test_priority_source_names_cover_requested_competitors() -> None:
    expected = {
        "MIT Technology Review AI",
        "VentureBeat AI",
        "NVIDIA Newsroom",
        "TCSJOHNHUXLEY",
        "Tangam Systems",
        "Interblock",
        "Gaming Laboratories International (GLI)",
        "BMM Testlabs",
        "Light & Wonder Newsroom",
        "Semiconductor Engineering",
        "EE Times",
        "RFID Journal",
        "IPC",
        "SEMI",
        "Zebra Technologies Newsroom",
        "NXP Newsroom",
    }
    assert expected.issubset(set(PRIORITY_PIPELINE_SOURCE_NAMES))
    assert "Everi News" not in PRIORITY_PIPELINE_SOURCE_NAMES
    assert "Table Trac" not in PRIORITY_PIPELINE_SOURCE_NAMES
