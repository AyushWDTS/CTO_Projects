from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.models.digest import DigestItem, DigestSection
from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis
from app.services.digest_ranking_service import (
    DigestCandidate,
    _is_low_value_fyi,
    _is_top_five_eligible,
    mark_top_five_candidates,
    pick_strategic_top_five_items,
    select_ranked_candidates,
    select_top_five_candidates,
)


def _candidate(
    *,
    title: str,
    tier: str = "monitor",
    relevance: float = 0.50,
    urgency: float = 0.30,
    wdts: float = 0.62,
    strategic: float = 0.72,
    signal_type: str | None = None,
    sales: bool = False,
    competitor: bool = False,
    urgency_label: str = "Monitor",
) -> DigestCandidate:
    event = NewsEvent(
        id=uuid4(),
        canonical_title=title,
        canonical_url="https://example.com/story",
        category="gaming",
        region="US",
    )
    analysis = EventAIAnalysis(
        event_id=None,
        short_summary=title,
        summary=title,
        why_it_matters="WDTS operating market signal.",
        relevance_score=Decimal(str(relevance)),
        urgency_score=Decimal(str(urgency)),
        importance_tier=tier,
        analysis_metadata={
            "briefing": {
                "signal_type": signal_type,
                "urgency": urgency_label,
            }
        },
    )
    return DigestCandidate(
        event=event,
        analysis=analysis,
        event_timestamp=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        final_score=0.65,
        relevance_score=relevance,
        urgency_score=urgency,
        confidence_score=0.7,
        source_authority_score=0.5,
        confirmation_score=0.3,
        recency_score=0.5,
        business_impact_score=0.55,
        wdts_relevance_score=wdts,
        signal_type_boost=0.8 if sales else 0.0,
        section=DigestSection.GAMING_AND_CASINO_MARKET,
        metadata={
            "strategic_score": strategic,
            "sales_opportunity_signal": sales,
            "is_competitor_signal": competitor,
            "signal_type": signal_type,
            "urgency": urgency_label,
            "briefing_section": "Competitors & Industry Watch"
            if competitor or sales
            else "Smart Tables & Casino Tech",
            "briefing": {
                "signal_type": signal_type,
                "urgency": urgency_label,
            },
        },
    )


def test_sigma_derby_is_low_value_fyi() -> None:
    candidate = _candidate(
        title="Golden Gate Hotel installs downtown Sigma Derby mechanical horse racing game",
        tier="low",
        relevance=0.05,
        urgency=0.03,
        wdts=0.45,
        strategic=0.46,
        urgency_label="FYI",
    )
    assert _is_low_value_fyi(candidate)


def test_strong_sales_story_remains_top_five_eligible() -> None:
    candidate = _candidate(
        title="Palasino FY2026 net profit falls as Czech Republic casino launch costs weigh",
        signal_type="sales_opportunity",
        sales=True,
        relevance=0.52,
        urgency=0.30,
        wdts=0.624,
        strategic=0.727,
    )
    assert _is_top_five_eligible(candidate)


def test_borderline_monitor_story_not_top_five_eligible() -> None:
    candidate = _candidate(
        title="Las Vegas ranked #1 U.S. city for meetings and conventions",
        relevance=0.42,
        urgency=0.20,
        wdts=0.484,
        strategic=0.58,
        signal_type="strategic_market_signal",
    )
    assert not _is_top_five_eligible(candidate)


def test_select_ranked_candidates_drop_low_value_fyi_when_stronger_exist() -> None:
    strong = _candidate(
        title="Palasino FY2026 net profit falls as Czech Republic casino launch costs weigh",
        signal_type="sales_opportunity",
        sales=True,
        relevance=0.52,
        urgency=0.30,
        wdts=0.624,
        strategic=0.727,
    )
    weak = _candidate(
        title="Golden Gate Hotel installs downtown Sigma Derby mechanical horse racing game",
        tier="low",
        relevance=0.05,
        urgency=0.03,
        wdts=0.45,
        strategic=0.46,
        urgency_label="FYI",
    )
    strong.final_score = 0.653
    weak.final_score = 0.393
    selected = select_ranked_candidates([strong, weak], limit=5, include_low=False)
    assert len(selected) == 1
    assert selected[0].event.canonical_title.startswith("Palasino")


def test_mark_top_five_only_flags_executive_grade_items() -> None:
    strong = _candidate(
        title="Palasino FY2026 net profit falls as Czech Republic casino launch costs weigh",
        signal_type="sales_opportunity",
        sales=True,
        relevance=0.52,
        urgency=0.30,
        wdts=0.624,
        strategic=0.727,
    )
    weak = _candidate(
        title="Las Vegas ranked #1 U.S. city for meetings and conventions",
        relevance=0.42,
        urgency=0.20,
        wdts=0.484,
        strategic=0.58,
        signal_type="strategic_market_signal",
    )
    marked = mark_top_five_candidates([strong, weak])
    by_title = {item.event.canonical_title: item.metadata.get("top_five_eligible") for item in marked}
    assert by_title[strong.event.canonical_title] is True
    assert by_title[weak.event.canonical_title] is False


def test_pick_strategic_top_five_items_does_not_pad_with_unflagged_items() -> None:
    item = DigestItem(
        digest_id=None,
        event_id=None,
        event_ai_analysis_id=None,
        rank=3,
        section=DigestSection.GAMING_AND_CASINO_MARKET.value,
        final_score=Decimal("0.393"),
        relevance_score=Decimal("0.050"),
        urgency_score=Decimal("0.030"),
        source_authority_score=Decimal("0.500"),
        recency_score=Decimal("0.500"),
        business_impact_score=Decimal("0.150"),
        importance_tier="low",
        headline="Sigma Derby install",
        item_metadata={"top_five_eligible": False},
    )
    assert pick_strategic_top_five_items([item]) == []


def test_select_top_five_candidates_prefers_stronger_story() -> None:
    strong = _candidate(
        title="Palasino FY2026 net profit falls as Czech Republic casino launch costs weigh",
        signal_type="sales_opportunity",
        sales=True,
        relevance=0.52,
        urgency=0.30,
        wdts=0.624,
        strategic=0.727,
    )
    weak = _candidate(
        title="Las Vegas ranked #1 U.S. city for meetings and conventions",
        relevance=0.42,
        urgency=0.20,
        wdts=0.484,
        strategic=0.58,
        signal_type="strategic_market_signal",
    )
    top_five = select_top_five_candidates([weak, strong])
    assert len(top_five) == 1
    assert top_five[0].event.canonical_title.startswith("Palasino")
