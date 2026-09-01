from decimal import Decimal

from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis
from app.services.wdts_relevance_service import (
    assess_wdts_relevance,
    detect_sales_opportunity,
)


def _event(title: str, category: str = "gaming") -> NewsEvent:
    return NewsEvent(
        canonical_title=title,
        canonical_url="https://example.com/story",
        category=category,
        region="US",
    )


def _analysis(
    *,
    relevance: str | None = "0.80",
    why: str = "Relevant for WDTS casino operations.",
) -> EventAIAnalysis:
    return EventAIAnalysis(
        event_id=None,
        summary="Casino regulator updates table game compliance requirements.",
        short_summary="Casino regulator updates table game rules",
        why_it_matters=why,
        relevance_score=Decimal(relevance) if relevance else None,
        urgency_score=Decimal("0.60"),
        importance_tier="important",
        analysis_metadata={
            "briefing": {
                "why_it_matters_to_wdts": "WDTS smart table deployments may need compliance review.",
            }
        },
    )


def test_rejects_stock_noise() -> None:
    event = _event("Casino operator shares surge 20% after earnings beat")
    verdict = assess_wdts_relevance(event, _analysis())
    assert verdict.is_eligible is False
    assert verdict.reject_reason == "human_interest_or_stock_noise"


def test_rejects_finance_noise_without_business_impact() -> None:
    event = _event("Fintech payments stock price hits record market cap", category="fintech")
    verdict = assess_wdts_relevance(event, _analysis())
    assert verdict.is_eligible is False
    assert verdict.reject_reason in {"finance_noise", "human_interest_or_stock_noise"}


def test_accepts_gaming_domain_story() -> None:
    event = _event("Macau casino regulator updates smart table compliance")
    verdict = assess_wdts_relevance(event, _analysis())
    assert verdict.is_eligible is True
    assert verdict.wdts_relevance_score >= 0.40
    assert "casino" in verdict.domain_hits or "smart table" in verdict.domain_hits


def test_detect_sales_opportunity_keywords() -> None:
    assert detect_sales_opportunity("New resort announces casino opening and table games expansion")
    assert not detect_sales_opportunity("Generic business update with no expansion signal")


def test_accepts_gaming_domain_story_with_borderline_ai_score() -> None:
    event = _event("Golden Gate Hotel and Casino installs downtown Sigma Derby game")
    verdict = assess_wdts_relevance(
        event,
        _analysis(relevance="0.30", why="Casino floor entertainment update in Las Vegas."),
    )
    assert verdict.is_eligible is True
    assert "casino" in verdict.domain_hits


def test_gaming_borderline_low_tier_can_rank() -> None:
    from app.services.digest_ranking_service import (
        DigestCandidate,
        _gaming_borderline_candidate,
        select_ranked_candidates,
    )
    from app.models.digest import DigestSection
    from app.models.event import NewsEvent
    from app.models.event_analysis import EventAIAnalysis

    source = type("Source", (), {"category": "gaming", "name": "Gaming Wire", "id": None})()
    event = NewsEvent(
        canonical_title="Casino floor update",
        canonical_url="https://example.com",
        category="gaming",
        primary_source=source,
    )
    analysis = EventAIAnalysis(
        event_id=None,
        short_summary="Casino floor update",
        relevance_score=Decimal("0.35"),
        urgency_score=Decimal("0.35"),
        importance_tier="low",
    )
    candidate = DigestCandidate(
        event=event,
        analysis=analysis,
        event_timestamp=__import__("datetime").datetime.now(__import__("datetime").UTC),
        final_score=0.39,
        relevance_score=0.3,
        urgency_score=0.2,
        confidence_score=0.5,
        source_authority_score=0.5,
        confirmation_score=0.3,
        recency_score=0.5,
        business_impact_score=0.2,
        wdts_relevance_score=0.45,
        signal_type_boost=0.0,
        section=DigestSection.MONITOR_LIST,
        metadata={},
    )
    assert _gaming_borderline_candidate(candidate)
    selected = select_ranked_candidates([candidate], limit=5, include_low=False)
    assert len(selected) == 1


def test_rejects_low_ai_relevance_without_domain_signal() -> None:
    event = _event("Random zoo wedding tragedy unrelated to gaming")
    verdict = assess_wdts_relevance(
        event,
        _analysis(relevance="0.20", why="No WDTS relevance for this human interest story."),
    )
    assert verdict.is_eligible is False
