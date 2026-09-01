from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.data.briefing_sections import COOBriefingSection, is_digest_action_item
from app.models.article import Article, ArticleExtractionStatus
from app.models.digest import Digest, DigestItem, DigestSection
from app.models.event import EventStatus, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod, Source, SourceType
from app.scripts.source_yield_report import build_report


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


def _seed_digest(db):
    source = Source(
        id=uuid4(),
        name="Gaming Wire",
        url="https://gaming.example.com",
        source_type=SourceType.NEWS_SITE,
        category="gaming",
        region="US",
        priority=2,
        fetch_method=FetchMethod.STATIC_HTML,
        reliability_score=Decimal("0.80"),
    )
    db.add(source)
    db.flush()
    fetched_at = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
    raw = RawDocument(
        source_id=source.id,
        url="https://gaming.example.com/raw",
        content_type="text/html",
        raw_content="raw",
        raw_hash="a" * 64,
        raw_size_bytes=3,
        fetched_at=fetched_at,
    )
    db.add(raw)
    db.flush()
    article = Article(
        raw_document_id=raw.id,
        source_id=source.id,
        title="Casino smart table rollout",
        canonical_url="https://gaming.example.com/story",
        source_url="https://gaming.example.com/story",
        content_type="text/html",
        clean_text="Casino smart table RFID rollout in Macau",
        excerpt="Casino smart table RFID rollout in Macau",
        published_at=fetched_at,
        content_hash="b" * 64,
        extraction_status=ArticleExtractionStatus.SUCCESS,
    )
    db.add(article)
    db.flush()
    event = NewsEvent(
        canonical_title="Casino smart table RFID rollout in Macau",
        canonical_url=article.canonical_url,
        normalized_canonical_url=article.canonical_url,
        primary_article_id=article.id,
        primary_source_id=source.id,
        event_key=f"yield-{uuid4()}",
        category="gaming",
        region="Macau",
        published_at=fetched_at,
        first_seen_at=fetched_at,
        last_seen_at=fetched_at,
        article_count=1,
        source_count=1,
        status=EventStatus.ACTIVE,
        confidence_score=Decimal("0.90"),
    )
    db.add(event)
    db.flush()
    analysis = EventAIAnalysis(
        event_id=event.id,
        summary="Casino smart table RFID rollout in Macau",
        short_summary="Casino smart table RFID rollout in Macau",
        why_it_matters="Impacts WDTS deployments.",
        relevance_score=Decimal("0.82"),
        urgency_score=Decimal("0.55"),
        confidence_score=Decimal("0.90"),
        importance_tier="important",
        status=EventAIAnalysisStatus.SUCCESS.value,
        source_urls=[article.source_url],
        context_article_count=1,
        analysis_metadata={
            "briefing": {
                "briefing_section": COOBriefingSection.SMART_TABLES.value,
                "category": "Smart Tables",
                "urgency": "Discuss",
                "action_bucket": "Discuss with team",
                "why_it_matters_to_wdts": "Direct smart table market signal.",
                "signal_type": "sales_opportunity",
            }
        },
    )
    db.add(analysis)
    db.flush()
    window_start = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    window_end = window_start + timedelta(days=1)
    digest = Digest(
        digest_date=window_start.date(),
        window_start=window_start,
        window_end=window_end,
        title="WDTS Daily News Digest",
        status="draft",
        digest_metadata={
            "selection_audit": {
                "summary": {
                    "reject_by_source": {str(source.id): 2},
                    "reject_by_reason": {"low_ai_relevance": 2},
                    "gate_rejected": 2,
                    "gate_eligible": 1,
                },
                "entries": [
                    {
                        "event_id": str(event.id),
                        "headline": "Rejected finance fluff",
                        "stage": "relevance_gate",
                        "decision": "rejected",
                        "reason": "low_ai_relevance",
                        "source_id": str(source.id),
                        "source_name": source.name,
                        "wdts_relevance_score": 0.31,
                        "ai_relevance_score": 0.22,
                    }
                ],
            }
        },
    )
    db.add(digest)
    db.flush()
    db.add(
        DigestItem(
            digest_id=digest.id,
            event_id=event.id,
            event_ai_analysis_id=analysis.id,
            rank=1,
            section=DigestSection.TECHNOLOGY_AND_OPERATIONS.value,
            final_score=Decimal("0.810"),
            relevance_score=Decimal("0.820"),
            urgency_score=Decimal("0.550"),
            source_authority_score=Decimal("0.700"),
            recency_score=Decimal("0.500"),
            business_impact_score=Decimal("0.750"),
            importance_tier="important",
            headline=analysis.short_summary,
            summary=analysis.summary,
            why_it_matters=analysis.why_it_matters,
            item_metadata={
                "top_five_eligible": True,
                "briefing_section": COOBriefingSection.SMART_TABLES.value,
                "signal_type": "sales_opportunity",
                "sales_opportunity_signal": True,
            },
        )
    )
    db.commit()
    db.refresh(digest)
    return digest, source


def test_source_yield_report_only_shows_active_sources(db) -> None:
    digest, source = _seed_digest(db)
    report = build_report(db, digest)
    assert report["active_source_count"] >= 1
    gaming_row = next(row for row in report["sources"] if row["source_id"] == str(source.id))
    assert gaming_row["source_name"] == "Gaming Wire"
    assert all(
        row["articles_ingested"]
        or row["events_analyzed"]
        or row["stories_selected"]
        or row["gate_rejected"]
        for row in report["sources"]
    )
    assert "rejected_examples_by_reason" in report
    assert report["rejected_examples_by_reason"].get("low_ai_relevance")
    assert "gate_recommendation" in report


def test_source_yield_report_counts_selected_and_rejected(db) -> None:
    digest, source = _seed_digest(db)
    report = build_report(db, digest)
    row = next(item for item in report["sources"] if item["source_id"] == str(source.id))
    assert row["articles_ingested"] == 1
    assert row["events_analyzed"] == 1
    assert row["stories_selected"] == 1
    assert row["gate_rejected"] == 2
    assert row["smart_table_appearances"] == 1


def test_is_digest_action_item_uses_signal_type() -> None:
    assert is_digest_action_item({"signal_type": "competitive_threat"}, None)
    assert is_digest_action_item({"sales_opportunity_signal": True}, None)
    assert not is_digest_action_item({"action_bucket": "No action", "urgency": "FYI"}, "No action")
