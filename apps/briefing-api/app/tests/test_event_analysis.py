from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import engine
from app.db.session import get_db
from app.main import app
from app.models.article import Article, ArticleExtractionStatus
from app.models.event import EventArticle, EventArticleMatchType, EventStatus, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus, ImportanceTier
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.ai_provider import AIProviderResponse, AIProviderUsage
from app.schemas.source import SourceCreate
from app.services.event_analysis_service import (
    analyze_by_category,
    analyze_by_region,
    analyze_by_source,
    analyze_pending_by_source,
    count_pending_analysis_for_source,
    analyze_event,
    analyze_pending_events,
    reprocess_failed_ai_analyses,
)
from app.services.event_context_service import build_event_context
from app.services.prompt_service import build_event_analysis_prompt
from app.services.source_service import create_source
from app.workers.celery_app import celery_app

VALID_AI_JSON = """
{
  "summary": "Casino regulation changed and may affect operators.",
  "short_summary": "Casino regulation changed.",
  "why_it_matters": "The change may affect compliance planning.",
  "key_points": ["Regulator approved a change", "Operators may need to monitor compliance"],
  "entities": [{"name": "Nevada Gaming Control Board", "type": "regulator"}],
  "topics": ["gaming", "regulation"],
  "sentiment": "neutral",
  "relevance_score": 0.72,
  "urgency_score": 0.44,
  "importance_tier": "important",
  "suggested_action": "Monitor follow-up guidance",
  "affected_business_area": "Compliance",
  "confidence_score": 0.81,
  "briefing_section": "Smart Tables & Casino Tech",
  "category": "Regulation",
  "country_or_region": "US",
  "urgency": "Monitor",
  "suggested_owner": "Legal",
  "action_bucket": "Monitor",
  "why_it_matters_to_wdts": "Regulatory changes can affect WDTS customer planning.",
  "signal_type": "regulatory_development"
}
"""


class FakeProvider:
    def __init__(self, content: str = VALID_AI_JSON, *, fail: bool = False) -> None:
        self.content = content
        self.fail = fail
        self.calls = 0

    def analyze(self, prompt: str) -> AIProviderResponse:
        self.calls += 1
        if self.fail:
            from app.services.ai_provider import AIProviderError

            raise AIProviderError("provider_down")
        return AIProviderResponse(
            content=self.content,
            model_name="fake-model",
            usage=AIProviderUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )


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


def clean_phase5_data(db: Session) -> None:
    db.execute(delete(EventAIAnalysis))
    db.execute(delete(EventArticle))
    db.execute(delete(NewsEvent))
    db.execute(delete(Article))
    db.execute(delete(RawDocument))
    db.commit()


def make_source(db: Session, **overrides: object) -> Source:
    suffix = uuid4()
    payload: dict[str, object] = {
        "name": f"AI Source {suffix}",
        "url": f"https://source.example.com/{suffix}",
        "source_type": SourceType.NEWS_SITE,
        "category": "gaming",
        "region": "US",
        "priority": 3,
        "fetch_method": FetchMethod.STATIC_HTML,
        "reliability_score": 0.75,
    }
    payload.update(overrides)
    return create_source(db, SourceCreate(**payload))


def make_article(db: Session, source: Source, *, title: str, text: str) -> Article:
    raw_document = RawDocument(
        source_id=source.id,
        url=f"https://raw.example.com/{uuid4()}",
        content_type="text/html",
        raw_content="raw html should not be used",
        raw_hash=f"{uuid4()}".replace("-", "")[:64],
        raw_size_bytes=27,
        http_status=200,
        fetched_at=datetime.now(UTC),
    )
    db.add(raw_document)
    db.flush()
    article = Article(
        raw_document_id=raw_document.id,
        source_id=source.id,
        title=title,
        canonical_url=f"https://article.example.com/{uuid4()}",
        source_url=f"https://article.example.com/{uuid4()}",
        content_type="text/html",
        clean_text=text,
        excerpt=text[:300],
        published_at=datetime.now(UTC),
        content_hash=f"{uuid4()}".replace("-", "")[:64],
        extraction_status=ArticleExtractionStatus.SUCCESS,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def make_event(db: Session, *, article_count: int = 1) -> NewsEvent:
    source = make_source(db)
    articles = [
        make_article(
            db,
            source,
            title=f"Gaming regulation update {index}",
            text=f"Important gaming regulation update text {index}. " * 40,
        )
        for index in range(article_count)
    ]
    event = NewsEvent(
        canonical_title="Gaming regulation update",
        canonical_url=articles[0].canonical_url,
        normalized_canonical_url=articles[0].canonical_url,
        primary_article_id=articles[0].id,
        primary_source_id=source.id,
        event_key=f"test:{uuid4()}",
        category="gaming",
        region="US",
        published_at=articles[0].published_at,
        first_seen_at=articles[0].published_at,
        last_seen_at=articles[-1].published_at,
        article_count=article_count,
        source_count=1,
        status=EventStatus.ACTIVE,
        confidence_score=0.9,
    )
    db.add(event)
    db.flush()
    for index, article in enumerate(articles):
        db.add(
            EventArticle(
                event_id=event.id,
                article_id=article.id,
                source_id=source.id,
                match_type=EventArticleMatchType.MANUAL,
                similarity_score=1,
                confidence_score=1,
                is_primary=index == 0,
            )
        )
    db.commit()
    db.refresh(event)
    return event


def test_context_prompt_traceability_and_no_raw_documents(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db, article_count=2)

    context = build_event_context(
        db,
        event.id,
        settings=Settings(AI_MAX_INPUT_CHARS_PER_EVENT=2000),
    )
    prompt = build_event_analysis_prompt(context)

    assert context.context_article_count >= 1
    assert str(event.primary_article_id) in context.source_article_ids
    assert "raw html should not be used" not in prompt
    assert "Do not invent facts" in prompt
    assert "briefing_section" in prompt
    assert "why_it_matters_to_wdts" in prompt
    assert "Do not repeat short_summary verbatim" in prompt


def test_successful_analysis_stores_output_traceability_tokens_and_cost(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db)
    provider = FakeProvider()
    settings = Settings(
        AI_API_KEY="test",
        AI_ESTIMATED_INPUT_COST_PER_1K_TOKENS=0.001,
        AI_ESTIMATED_OUTPUT_COST_PER_1K_TOKENS=0.002,
    )

    analysis = analyze_event(db, event.id, provider=provider, settings=settings)

    assert analysis.status == EventAIAnalysisStatus.SUCCESS
    assert analysis.importance_tier == ImportanceTier.IMPORTANT
    assert analysis.prompt_tokens == 100
    assert analysis.completion_tokens == 50
    assert analysis.estimated_cost is not None
    assert analysis.source_article_ids == [str(event.primary_article_id)]
    assert analysis.primary_article_id == event.primary_article_id
    assert analysis.context_article_count == 1
    assert analysis.analysis_metadata["briefing"]["briefing_section"] == (
        "Smart Tables & Casino Tech"
    )
    assert analysis.analysis_metadata["briefing"]["suggested_owner"] == "Legal"


def test_missing_api_key_creates_failed_analysis(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db)

    analysis = analyze_event(
        db,
        event.id,
        settings=Settings(AI_PROVIDER="openai_compatible", AI_API_KEY=""),
    )

    assert analysis.status == EventAIAnalysisStatus.FAILED
    assert analysis.error_message == "missing_ai_api_key"


@pytest.mark.parametrize(
    "content",
    [
        "{not-json",
        '{"summary":"ok","short_summary":"ok","why_it_matters":"ok","key_points":"bad"}',
        (
            '{"summary":"ok","short_summary":"ok","why_it_matters":"ok",'
            '"key_points":["ok"],"entities":[{"name":"Only name"}]}'
        ),
    ],
)
def test_invalid_model_output_fails_cleanly(db: Session, content: str) -> None:
    clean_phase5_data(db)
    event = make_event(db)

    analysis = analyze_event(
        db,
        event.id,
        provider=FakeProvider(content),
        settings=Settings(AI_API_KEY="test"),
    )

    assert analysis.status == EventAIAnalysisStatus.FAILED
    assert analysis.error_message == "invalid_ai_json"


def test_provider_error_finalizes_pending_row_as_failed(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db)

    analysis = analyze_event(
        db,
        event.id,
        provider=FakeProvider(fail=True),
        settings=Settings(AI_API_KEY="test"),
    )

    assert analysis.status == EventAIAnalysisStatus.FAILED
    assert analysis.error_message == "ai_provider_error"


def test_idempotency_skips_provider_and_force_reuses_row(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db)
    first_provider = FakeProvider()
    settings = Settings(AI_API_KEY="test")

    first = analyze_event(db, event.id, provider=first_provider, settings=settings)
    second_provider = FakeProvider()
    second = analyze_event(db, event.id, provider=second_provider, settings=settings)
    forced_provider = FakeProvider()
    forced = analyze_event(db, event.id, force=True, provider=forced_provider, settings=settings)

    assert first.id == second.id == forced.id
    assert first_provider.calls == 1
    assert second_provider.calls == 0
    assert forced_provider.calls == 1


def test_batch_filters_api_and_celery_discovery(
    api_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean_phase5_data(db)
    event = make_event(db)
    monkeypatch.setattr(
        "app.services.event_analysis_service.get_settings",
        lambda: Settings(AI_PROVIDER="openai_compatible", AI_API_KEY=""),
    )

    failed_response = api_client.post(f"/api/v1/event-analysis/events/{event.id}/run")
    assert failed_response.status_code == 200
    assert failed_response.json()["status"] == EventAIAnalysisStatus.FAILED.value

    list_response = api_client.get(
        "/api/v1/event-analysis",
        params={
            "status": EventAIAnalysisStatus.FAILED.value,
            "category": "gaming",
            "region": "US",
        },
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_response = api_client.get(f"/api/v1/event-analysis/events/{event.id}")
    assert get_response.status_code == 200

    assert "app.workers.event_analysis_tasks.analyze_event" in celery_app.tasks
    assert "app.workers.event_analysis_tasks.analyze_pending_events" in celery_app.tasks
    assert "app.workers.event_analysis_tasks.analyze_by_source" in celery_app.tasks
    assert "app.workers.event_analysis_tasks.reprocess_failed_ai_analyses" in celery_app.tasks


def test_service_batch_paths(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db)
    provider = FakeProvider()
    settings = Settings(AI_API_KEY="test")

    pending = analyze_pending_events(db, provider=provider, settings=settings)
    by_source = analyze_by_source(
        db,
        event.primary_source_id,
        provider=FakeProvider(),
        settings=settings,
    )
    by_category = analyze_by_category(
        db,
        "gaming",
        force=True,
        provider=FakeProvider(),
        settings=settings,
    )
    by_region = analyze_by_region(db, "US", force=True, provider=FakeProvider(), settings=settings)

    failed = db.get(EventAIAnalysis, pending.results[0].id)
    failed.status = EventAIAnalysisStatus.FAILED.value
    db.commit()
    reprocessed = reprocess_failed_ai_analyses(db, provider=FakeProvider(), settings=settings)

    assert pending.total_events == 1
    assert by_source.total_events == 1
    assert by_category.total_events == 1
    assert by_region.total_events == 1
    assert reprocessed.total_events == 1


def test_one_analysis_row_per_event_after_repeated_runs(db: Session) -> None:
    clean_phase5_data(db)
    event = make_event(db)
    settings = Settings(AI_API_KEY="test")

    analyze_event(db, event.id, provider=FakeProvider(), settings=settings)
    analyze_event(db, event.id, force=True, provider=FakeProvider(), settings=settings)

    count = db.query(EventAIAnalysis).filter(EventAIAnalysis.event_id == event.id).count()
    assert count == 1


def test_analyze_pending_by_source_skips_already_analyzed_events(db: Session) -> None:
    clean_phase5_data(db)
    analyzed_event = make_event(db)
    settings = Settings(AI_API_KEY="test")
    provider = FakeProvider()

    analyze_event(db, analyzed_event.id, provider=provider, settings=settings)
    assert count_pending_analysis_for_source(db, analyzed_event.primary_source_id) == 0

    pending = analyze_pending_by_source(
        db,
        analyzed_event.primary_source_id,
        provider=provider,
        settings=settings,
    )
    assert pending.total_events == 0
    assert pending.analyzed == 0
