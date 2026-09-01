from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import engine
from app.data.briefing_coverage import validate_coverage_matrix
from app.data.briefing_sections import (
    CONTENT_SECTION_ORDER,
    DASHBOARD_SECTION_ORDER,
    BriefingSection,
)
from app.db.session import get_db
from app.main import app
from app.models.article import Article, ArticleExtractionStatus
from app.models.digest import Digest, DigestItem, DigestSection
from app.models.event import EventArticle, EventArticleMatchType, EventStatus, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.digest import DigestDetailRead
from app.schemas.source import SourceCreate
from app.services.digest_ranking_service import RANKING_VERSION
from app.services.digest_service import (
    build_digest,
    preview_digest,
    refresh_digest,
    resolve_digest_window,
    select_digest_candidates,
)
from app.services.source_service import create_source
from app.workers.celery_app import celery_app

BASE_DATE = date(2026, 6, 1)
WINDOW_START = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 6, 2, 0, 0, tzinfo=UTC)


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


def clean_digest_data(db: Session) -> None:
    db.execute(delete(DigestItem))
    db.execute(delete(Digest))
    db.execute(delete(EventAIAnalysis))
    db.execute(delete(NewsEvent))
    db.execute(delete(Article))
    db.execute(delete(RawDocument))
    db.commit()


def make_source(db: Session, **overrides: object) -> Source:
    suffix = uuid4()
    payload: dict[str, object] = {
        "name": f"Digest Source {suffix}",
        "url": f"https://digest-source.example.com/{suffix}",
        "source_type": SourceType.NEWS_SITE,
        "category": "gaming",
        "region": "US",
        "priority": 2,
        "fetch_method": FetchMethod.STATIC_HTML,
        "reliability_score": 0.80,
    }
    payload.update(overrides)
    return create_source(db, SourceCreate(**payload))


def make_article(db: Session, source: Source, *, published_at: datetime) -> Article:
    raw_document = RawDocument(
        source_id=source.id,
        url=f"https://raw.example.com/{uuid4()}",
        content_type="text/html",
        raw_content="raw",
        raw_hash=f"{uuid4()}".replace("-", "")[:64],
        raw_size_bytes=3,
        http_status=200,
        fetched_at=published_at,
    )
    db.add(raw_document)
    db.flush()
    article = Article(
        raw_document_id=raw_document.id,
        source_id=source.id,
        title="Digest article",
        canonical_url=f"https://article.example.com/{uuid4()}",
        source_url=f"https://article.example.com/{uuid4()}",
        content_type="text/html",
        clean_text="Useful digest text",
        excerpt="Useful digest text",
        published_at=published_at,
        content_hash=f"{uuid4()}".replace("-", "")[:64],
        extraction_status=ArticleExtractionStatus.SUCCESS,
    )
    db.add(article)
    db.flush()
    return article


def make_event_analysis(
    db: Session,
    *,
    importance_tier: str,
    published_at: datetime,
    category: str = "gaming",
    region: str = "US",
    relevance_score: Decimal = Decimal("0.800"),
    urgency_score: Decimal = Decimal("0.600"),
    confidence_score: Decimal = Decimal("0.900"),
    affected_business_area: str | None = "Operations",
    source_count: int = 2,
) -> EventAIAnalysis:
    source = make_source(db, category=category, region=region)
    article = make_article(db, source, published_at=published_at)
    event = NewsEvent(
        canonical_title=f"{importance_tier.title()} event {uuid4()}",
        canonical_url=f"https://event.example.com/{uuid4()}",
        normalized_canonical_url=f"https://event.example.com/{uuid4()}",
        primary_article_id=article.id,
        primary_source_id=source.id,
        event_key=f"digest-{uuid4()}",
        category=category,
        region=region,
        published_at=published_at,
        first_seen_at=published_at,
        last_seen_at=published_at,
        article_count=2,
        source_count=source_count,
        status=EventStatus.ACTIVE,
        confidence_score=Decimal("0.850"),
    )
    db.add(event)
    db.flush()
    analysis = EventAIAnalysis(
        event_id=event.id,
        summary=f"{importance_tier.title()} casino gaming market summary",
        short_summary=f"{importance_tier.title()} casino regulator update",
        why_it_matters="It matters for daily operations.",
        key_points=["Point"],
        entities=[],
        topics=[category],
        relevance_score=relevance_score,
        urgency_score=urgency_score,
        confidence_score=confidence_score,
        importance_tier=importance_tier,
        suggested_action="Monitor",
        affected_business_area=affected_business_area,
        status=EventAIAnalysisStatus.SUCCESS.value,
        source_urls=[article.source_url],
        context_article_count=1,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def make_clustered_event_without_ai(
    db: Session,
    *,
    published_at: datetime,
    title: str,
    text: str,
    category: str = "technology",
    region: str = "Macau",
    source_category: str = "technology",
    source_region: str = "Macau",
    source_priority: int = 2,
    reliability_score: float = 0.80,
) -> NewsEvent:
    source = make_source(
        db,
        category=source_category,
        region=source_region,
        priority=source_priority,
        reliability_score=reliability_score,
    )
    article = make_article(db, source, published_at=published_at)
    article.title = title
    article.clean_text = text
    article.excerpt = text[:300]
    event = NewsEvent(
        canonical_title=title,
        canonical_url=article.canonical_url,
        normalized_canonical_url=article.canonical_url,
        primary_article_id=article.id,
        primary_source_id=source.id,
        event_key=f"fallback-digest-{uuid4()}",
        category=category,
        region=region,
        published_at=published_at,
        first_seen_at=published_at,
        last_seen_at=published_at,
        article_count=1,
        source_count=1,
        status=EventStatus.ACTIVE,
        confidence_score=Decimal("0.900"),
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
    db.refresh(event)
    return event


def assert_top_level_briefing_metadata(metadata: dict) -> None:
    for field in [
        "briefing_section",
        "briefing_category",
        "coo_section",
        "coo_category",
        "country_or_region",
        "urgency",
        "suggested_owner",
        "action_bucket",
        "why_it_matters_to_wdts",
        "mapping_source",
    ]:
        assert metadata[field]


def test_build_digest_creates_ranked_items_and_metadata(db: Session) -> None:
    clean_digest_data(db)
    make_event_analysis(
        db,
        importance_tier="critical",
        published_at=WINDOW_START + timedelta(hours=2),
        category="regulatory",
    )
    make_event_analysis(
        db,
        importance_tier="monitor",
        published_at=WINDOW_START + timedelta(hours=3),
        category="gaming",
        affected_business_area="Casino operations",
    )

    digest = build_digest(db, digest_date=BASE_DATE)

    assert digest.total_candidates == 2
    assert digest.total_selected == 2
    assert digest.critical_count == 1
    assert digest.monitor_count == 1
    assert digest.digest_metadata["ranking_version"] == RANKING_VERSION
    assert "selection_audit" in digest.digest_metadata
    assert digest.digest_metadata["window_start"] == WINDOW_START.isoformat()
    assert digest.items[0].rank == 1
    assert digest.items[0].section == DigestSection.CRITICAL_ALERTS
    assert digest.items[0].item_metadata["ranking_version"] == RANKING_VERSION
    assert digest.items[0].item_metadata["briefing"]["briefing_section"] in CONTENT_SECTION_ORDER
    assert digest.items[0].item_metadata["briefing"]["mapping_source"] in {
        "ai_metadata",
        "deterministic_mapping",
        "fallback",
    }
    assert_top_level_briefing_metadata(digest.items[0].item_metadata)
    assert Decimal("0.000") <= digest.items[0].final_score <= Decimal("1.000")
    assert digest.items[1].section == DigestSection.MONITOR_LIST


def test_briefing_section_constants_match_required_order() -> None:
    assert DASHBOARD_SECTION_ORDER == [
        BriefingSection.TOP_STORIES.value,
        BriefingSection.AI_ML_CV.value,
        BriefingSection.SMART_TABLES.value,
        BriefingSection.SEMICONDUCTORS.value,
        BriefingSection.AUTOMATION.value,
        BriefingSection.COMPETITORS.value,
        BriefingSection.REGULATION.value,
        BriefingSection.ACTION_ITEMS.value,
    ]


def test_briefing_coverage_matrix_is_valid() -> None:
    validate_coverage_matrix()


def test_ai_metadata_drives_coo_section_when_valid(db: Session) -> None:
    clean_digest_data(db)
    analysis = make_event_analysis(
        db,
        importance_tier="important",
        published_at=WINDOW_START + timedelta(hours=5),
        category="technology",
        affected_business_area="Product",
    )
    analysis.summary = "Smart table RFID automation update for casino operators."
    analysis.short_summary = "Smart table RFID automation update"
    analysis.affected_business_area = "Smart table RFID product roadmap"
    analysis.analysis_metadata = {
        "briefing": {
            "briefing_section": BriefingSection.SMART_TABLES.value,
            "category": "Smart Tables",
            "country_or_region": "Macau",
            "urgency": "Discuss",
            "suggested_owner": "Product",
            "action_bucket": "Discuss with team",
            "why_it_matters_to_wdts": "Signals product roadmap implications for WDTS.",
        }
    }
    db.commit()

    digest = build_digest(db, digest_date=BASE_DATE, refresh=True)

    coo = digest.items[0].item_metadata["briefing"]
    assert coo["coo_section"] == BriefingSection.SMART_TABLES.value
    assert coo["coo_category"] == "Smart Tables"
    assert coo["mapping_source"] == "ai_metadata"
    assert digest.items[0].item_metadata["coo_section"] == BriefingSection.SMART_TABLES.value
    assert digest.items[0].item_metadata["mapping_source"] == "ai_metadata"


def test_invalid_ai_metadata_falls_back_to_deterministic_mapping(db: Session) -> None:
    clean_digest_data(db)
    analysis = make_event_analysis(
        db,
        importance_tier="important",
        published_at=WINDOW_START + timedelta(hours=6),
        category="technology",
        affected_business_area="RFID chip tracking and smart table automation",
    )
    analysis.analysis_metadata = {
        "coo_briefing": {
            "briefing_section": "Unsupported Section",
            "urgency": "Panic",
            "suggested_owner": "Someone",
        }
    }
    db.commit()

    digest = build_digest(db, digest_date=BASE_DATE, refresh=True)

    coo = digest.items[0].item_metadata.get("briefing") or digest.items[0].item_metadata["coo_briefing"]
    assert coo["coo_section"] == BriefingSection.SMART_TABLES.value
    assert coo["mapping_source"] == "deterministic_mapping"


def test_fallback_digest_candidates_are_created_without_ai(db: Session) -> None:
    clean_digest_data(db)
    make_clustered_event_without_ai(
        db,
        published_at=WINDOW_START + timedelta(hours=7),
        title="RFID chip tracking approved for smart table game automation",
        text="RFID chip tracking and smart table automation can affect casino operations.",
    )

    candidates = select_digest_candidates(
        db,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )
    digest = build_digest(db, digest_date=BASE_DATE)

    assert len(candidates) == 1
    assert candidates[0].metadata["candidate_source"] == "fallback_event"
    assert digest.total_candidates == 1
    assert digest.total_selected == 1
    assert digest.items[0].event_ai_analysis_id is None
    coo = digest.items[0].item_metadata.get("briefing") or digest.items[0].item_metadata["coo_briefing"]
    assert coo["coo_section"] == BriefingSection.SMART_TABLES.value
    assert coo["coo_category"] == "Smart Tables"
    assert coo["country_or_region"] == "Macau"
    assert coo["urgency"] == "Monitor"
    assert coo["suggested_owner"] == "Product"
    assert coo["action_bucket"] == "Monitor"
    assert coo["why_it_matters_to_wdts"]
    assert coo["mapping_source"] == "deterministic_mapping"
    item = db.scalar(select(DigestItem).where(DigestItem.id == digest.items[0].id))
    assert item is not None
    assert_top_level_briefing_metadata(item.item_metadata)
    assert item.item_metadata["coo_section"] == BriefingSection.SMART_TABLES.value
    assert item.item_metadata["mapping_source"] == "deterministic_mapping"


def test_fallback_digest_metadata_has_no_blank_values(db: Session) -> None:
    clean_digest_data(db)
    make_clustered_event_without_ai(
        db,
        published_at=WINDOW_START + timedelta(hours=8),
        title="Casino market monitor update",
        text="Casino operator external development to monitor for gaming relevance.",
        category="gaming",
        region="Global",
        source_category="gaming",
        source_region="Global",
    )

    digest = build_digest(db, digest_date=BASE_DATE)

    coo = digest.items[0].item_metadata.get("briefing") or digest.items[0].item_metadata["coo_briefing"]
    for field in [
        "coo_section",
        "coo_category",
        "country_or_region",
        "urgency",
        "suggested_owner",
        "action_bucket",
        "why_it_matters_to_wdts",
        "mapping_source",
    ]:
        assert coo[field]
    assert coo["country_or_region"] == "Global"
    assert coo["urgency"] == "Monitor"
    assert coo["action_bucket"] == "Monitor"
    assert coo["suggested_owner"] in {"Sales", "Legal", "Product", "Executive Team"}
    assert coo["why_it_matters_to_wdts"] == (
        "Potential external development to monitor for WDTS relevance."
    )
    assert coo["coo_section"] in {
        BriefingSection.REGULATION.value,
        BriefingSection.SMART_TABLES.value,
        BriefingSection.AUTOMATION.value,
    }
    assert coo["mapping_source"] == "deterministic_mapping"
    item = db.scalar(select(DigestItem).where(DigestItem.id == digest.items[0].id))
    assert item is not None
    assert_top_level_briefing_metadata(item.item_metadata)
    assert item.item_metadata["mapping_source"] == "deterministic_mapping"


def test_empty_draft_digest_rebuilds_when_fallback_candidates_arrive(db: Session) -> None:
    clean_digest_data(db)
    empty_digest = build_digest(db, digest_date=BASE_DATE)
    assert empty_digest.total_candidates == 0
    assert empty_digest.total_selected == 0

    make_clustered_event_without_ai(
        db,
        published_at=WINDOW_START + timedelta(hours=9),
        title="Casino regulator compliance bulletin",
        text="Casino regulator compliance update for land-based gaming operators.",
        category="gaming",
        region="US",
        source_category="gaming",
        source_region="US",
    )

    rebuilt = build_digest(db, digest_date=BASE_DATE)

    assert rebuilt.id == empty_digest.id
    assert rebuilt.total_candidates == 1
    assert rebuilt.total_selected == 1
    assert rebuilt.items[0].item_metadata["candidate_source"] == "fallback_event"


def test_existing_digest_backfills_top_level_coo_metadata(db: Session) -> None:
    clean_digest_data(db)
    make_clustered_event_without_ai(
        db,
        published_at=WINDOW_START + timedelta(hours=10),
        title="Casino operator technology update",
        text="Casino operator technology update for land-based gaming operations.",
        category="gaming",
        region="US",
        source_category="gaming",
        source_region="US",
    )
    digest = build_digest(db, digest_date=BASE_DATE)
    item = digest.items[0]
    nested_only = {
        key: value
        for key, value in item.item_metadata.items()
        if key
        not in {
            "briefing_section",
            "briefing_category",
            "coo_section",
            "coo_category",
            "country_or_region",
            "urgency",
            "suggested_owner",
            "action_bucket",
            "why_it_matters_to_wdts",
            "mapping_source",
        }
    }
    item.item_metadata = nested_only
    db.commit()

    reused = build_digest(db, digest_date=BASE_DATE)

    assert reused.id == digest.id
    assert_top_level_briefing_metadata(reused.items[0].item_metadata)
    assert reused.items[0].item_metadata["mapping_source"] == "deterministic_mapping"


def test_half_open_window_and_min_score_filter(db: Session) -> None:
    clean_digest_data(db)
    included = make_event_analysis(
        db,
        importance_tier="important",
        published_at=WINDOW_START,
        relevance_score=Decimal("0.900"),
    )
    make_event_analysis(db, importance_tier="critical", published_at=WINDOW_END)

    candidates = select_digest_candidates(
        db,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        min_score=0.70,
    )

    assert [candidate.analysis.id for candidate in candidates] == [included.id]
    assert candidates[0].final_score >= 0.70


def test_default_window_is_current_utc_day() -> None:
    now = datetime(2026, 6, 1, 12, 30, 45, tzinfo=UTC)

    digest_date, start, end = resolve_digest_window(now=now)

    assert digest_date == BASE_DATE
    assert start == WINDOW_START
    assert end == WINDOW_END


def test_resolve_digest_window_prefers_explicit_digest_date() -> None:
    watermark = datetime(2026, 6, 24, 4, 37, 21, tzinfo=UTC)
    window_end = datetime(2026, 6, 26, 3, 25, 48, tzinfo=UTC)
    target = date(2026, 6, 25)

    digest_date, start, end = resolve_digest_window(
        digest_date=target,
        window_start=watermark,
        window_end=window_end,
    )

    assert digest_date == target
    assert start == watermark
    assert end == window_end


def test_resolve_digest_window_derives_date_from_window_when_omitted() -> None:
    watermark = datetime(2026, 6, 24, 4, 37, 21, tzinfo=UTC)
    window_end = datetime(2026, 6, 26, 3, 25, 48, tzinfo=UTC)

    digest_date, start, end = resolve_digest_window(
        window_start=watermark,
        window_end=window_end,
    )

    assert digest_date == watermark.date()
    assert start == watermark
    assert end == window_end


def test_zero_candidate_build_and_preview_are_clean(db: Session) -> None:
    clean_digest_data(db)

    digest = build_digest(db, digest_date=BASE_DATE)
    preview = preview_digest(db, digest_date=BASE_DATE)

    assert digest.total_candidates == 0
    assert digest.total_selected == 0
    assert digest.items == []
    assert preview.total_candidates == 0
    assert preview.total_selected == 0
    assert preview.items == []


def test_existing_digest_is_reused_and_refresh_recomputes(db: Session) -> None:
    clean_digest_data(db)
    make_event_analysis(
        db,
        importance_tier="important",
        published_at=WINDOW_START + timedelta(hours=4),
    )

    first = build_digest(db, digest_date=BASE_DATE)
    second = build_digest(db, digest_date=BASE_DATE)
    first_selected_count = first.total_selected
    make_event_analysis(
        db,
        importance_tier="critical",
        published_at=WINDOW_START + timedelta(hours=5),
    )
    refreshed = refresh_digest(db, first.id)

    assert second.id == first.id
    assert first_selected_count == 1
    assert refreshed.id == first.id
    assert refreshed.total_selected == 2
    assert [item.rank for item in refreshed.items] == [1, 2]


def test_api_exposes_metadata_and_digest_endpoints(
    db: Session,
    api_client: TestClient,
) -> None:
    clean_digest_data(db)
    make_event_analysis(
        db,
        importance_tier="critical",
        published_at=WINDOW_START + timedelta(hours=6),
    )

    build_response = api_client.post(f"/api/v1/digests/build?digest_date={BASE_DATE.isoformat()}")
    assert build_response.status_code == 200
    payload = build_response.json()
    assert payload["metadata"]["ranking_version"] == RANKING_VERSION
    assert payload["items"][0]["metadata"]["ranking_version"] == RANKING_VERSION

    digest_id = payload["id"]
    assert api_client.get("/api/v1/digests").status_code == 200
    assert api_client.get(f"/api/v1/digests/{digest_id}").status_code == 200
    items_response = api_client.get(f"/api/v1/digests/{digest_id}/items")
    assert items_response.status_code == 200
    assert items_response.json()["total"] == 1
    assert api_client.post(f"/api/v1/digests/{digest_id}/refresh").status_code == 200
    preview_response = api_client.post(
        f"/api/v1/digests/preview?digest_date={BASE_DATE.isoformat()}"
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["total_selected"] == 1


def test_cli_path_and_celery_task_discovery(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    clean_digest_data(db)
    make_event_analysis(
        db,
        importance_tier="important",
        published_at=WINDOW_START + timedelta(hours=7),
    )

    from app.scripts import build_digest as build_digest_script

    class SessionProxy:
        def __getattr__(self, name: str):
            return getattr(db, name)

        def close(self) -> None:
            return None

    class SessionFactory:
        def __call__(self) -> SessionProxy:
            return SessionProxy()

    monkeypatch.setattr(build_digest_script, "SessionLocal", SessionFactory())
    monkeypatch.setattr(
        "sys.argv",
        ["build_digest", "--date", BASE_DATE.isoformat(), "--preview"],
    )
    build_digest_script.main()

    output = capsys.readouterr().out
    assert '"total_selected": 1' in output
    assert "app.workers.digest_tasks.build_daily_digest" in celery_app.tasks
    assert "app.workers.digest_tasks.build_digest_for_window" in celery_app.tasks
    assert "app.workers.digest_tasks.refresh_digest" in celery_app.tasks


def test_schema_aliases_expose_metadata(db: Session) -> None:
    clean_digest_data(db)
    make_event_analysis(
        db,
        importance_tier="critical",
        published_at=WINDOW_START + timedelta(hours=8),
    )
    digest = build_digest(db, digest_date=BASE_DATE)

    payload = DigestDetailRead.model_validate(digest).model_dump(mode="json", by_alias=True)

    assert "metadata" in payload
    assert "digest_metadata" not in payload
    assert "metadata" in payload["items"][0]
    assert "item_metadata" not in payload["items"][0]
