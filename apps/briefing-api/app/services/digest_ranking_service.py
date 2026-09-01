from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.data.briefing_sections import build_coo_item_metadata
from app.models.article import Article
from app.models.digest import DigestItem, DigestSection
from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis, ImportanceTier
from app.services.digest_selection_audit import DigestSelectionAudit
from app.services.wdts_relevance_service import (
    GAMING_SOURCE_CATEGORIES,
    MIN_WDTS_RELEVANCE_FOR_DIGEST,
    MIN_WDTS_RELEVANCE_FOR_TOP_FIVE,
    MIN_WDTS_RELEVANCE_WITH_SIGNAL,
    assess_wdts_relevance,
    strategic_score,
)

RANKING_VERSION = "phase6_v3"
DEFAULT_MIN_SCORE = 0.40
MONITOR_TIER_CAP = 2
TOP_FIVE_LIMIT = 5
MIN_STRATEGIC_SCORE_FOR_TOP_FIVE = 0.58
MIN_AI_RELEVANCE_FOR_TOP_FIVE_MONITOR = 0.45
MIN_URGENCY_FOR_TOP_FIVE_MONITOR = 0.35
ENTERTAINMENT_NOISE_KEYWORDS = (
    "sigma derby",
    "horse racing",
    "mechanical game",
    "mechanical horse",
    "slot machine install",
    "celebrity",
    "zoo",
    "wedding",
    "entertainment attraction",
    "tourist attraction",
)
SMART_TABLE_SECTION = "Smart Tables & Casino Tech"
WATCHLIST_SECTION = "Competitors & Industry Watch"
STRONG_EXECUTIVE_SIGNAL_TYPES = {
    "sales_opportunity",
    "competitive_threat",
    "regulatory_development",
    "manufacturing_component_risk",
    "compliance_opportunity",
}
FALLBACK_WHY_IT_MATTERS = "Potential external development to monitor for WDTS relevance."
COO_METADATA_FIELDS = {
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

PRIORITY_SCORES = {
    1: 1.0,
    2: 0.8,
    3: 0.6,
    4: 0.4,
    5: 0.2,
}
TIER_ORDER = {
    ImportanceTier.CRITICAL.value: 0,
    ImportanceTier.IMPORTANT.value: 1,
    ImportanceTier.MONITOR.value: 2,
    ImportanceTier.LOW.value: 3,
}
BUSINESS_IMPACT_BASE = {
    ImportanceTier.CRITICAL.value: 1.0,
    ImportanceTier.IMPORTANT.value: 0.75,
    ImportanceTier.MONITOR.value: 0.45,
    ImportanceTier.LOW.value: 0.15,
}
BOOST_KEYWORDS = {"regulatory", "compliance", "gaming", "casino", "technology", "operations"}
BOOST_REGIONS = {"us", "asia", "eu", "global"}


@dataclass
class DigestCandidate:
    event: NewsEvent
    analysis: EventAIAnalysis
    event_timestamp: datetime
    final_score: float
    relevance_score: float
    urgency_score: float
    confidence_score: float
    source_authority_score: float
    confirmation_score: float
    recency_score: float
    business_impact_score: float
    wdts_relevance_score: float
    signal_type_boost: float
    section: DigestSection
    metadata: dict


def score_digest_candidate(
    event: NewsEvent,
    analysis: EventAIAnalysis,
    *,
    event_timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
) -> DigestCandidate:
    relevance = _score_value(analysis.relevance_score)
    urgency = _score_value(analysis.urgency_score)
    confidence = _score_value(analysis.confidence_score)
    source_authority = _source_authority_score(event)
    confirmation = clamp_score((event.source_count or 0) / 3)
    recency = _recency_score(event_timestamp, window_start, window_end)
    business_impact = _business_impact_score(event, analysis)
    verdict = assess_wdts_relevance(event, analysis)
    wdts_relevance = verdict.wdts_relevance_score
    section = assign_digest_section(event, analysis)
    coo_metadata = build_coo_item_metadata(event, analysis)
    signal_boost = _signal_boost_from_metadata(coo_metadata)

    final_score = clamp_score(
        wdts_relevance * 0.28
        + relevance * 0.20
        + urgency * 0.14
        + business_impact * 0.17
        + signal_boost * 0.11
        + source_authority * 0.05
        + recency * 0.03
        + confirmation * 0.05
        + confidence * 0.05
    )
    metadata = flatten_coo_metadata(
        {
            "ranking_version": RANKING_VERSION,
            "wdts_relevance_score": round(wdts_relevance, 6),
            "signal_type_boost": round(signal_boost, 6),
            "strategic_score": round(
                strategic_score(
                    wdts_relevance_score=wdts_relevance,
                    business_impact_score=business_impact,
                    signal_type=str(coo_metadata.get("signal_type") or ""),
                ),
                6,
            ),
            "sales_opportunity_signal": verdict.sales_opportunity_signal,
            "is_competitor_signal": verdict.is_competitor_signal,
            "competitor_name": verdict.competitor_name,
            "score_components": {
                "wdts_relevance": round(wdts_relevance, 6),
                "relevance": round(relevance, 6),
                "urgency": round(urgency, 6),
                "confidence": round(confidence, 6),
                "source_authority": round(source_authority, 6),
                "confirmation": round(confirmation, 6),
                "recency": round(recency, 6),
                "business_impact": round(business_impact, 6),
                "signal_type_boost": round(signal_boost, 6),
            },
            "event_timestamp": _isoformat_utc(event_timestamp),
            "source_count": event.source_count,
            "article_count": event.article_count,
            "category": event.category,
            "region": event.region,
            "affected_business_area": analysis.affected_business_area,
            "briefing": coo_metadata,
            "coo_briefing": coo_metadata,
        }
    )

    return DigestCandidate(
        event=event,
        analysis=analysis,
        event_timestamp=event_timestamp,
        final_score=final_score,
        relevance_score=relevance,
        urgency_score=urgency,
        confidence_score=confidence,
        source_authority_score=source_authority,
        confirmation_score=confirmation,
        recency_score=recency,
        business_impact_score=business_impact,
        wdts_relevance_score=wdts_relevance,
        signal_type_boost=signal_boost,
        section=section,
        metadata=metadata,
    )


def score_fallback_digest_candidate(
    event: NewsEvent,
    *,
    event_timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
) -> DigestCandidate:
    article = _primary_or_first_article(event)
    relevance = _fallback_relevance_score(event, article)
    urgency = 0.20
    confidence = clamp_score(event.confidence_score)
    source_authority = _source_authority_score(event)
    confirmation = clamp_score((event.source_count or 0) / 3)
    recency = _recency_score(event_timestamp, window_start, window_end)
    business_impact = _fallback_business_impact_score(event, article)
    analysis = _fallback_analysis(event, article, relevance)
    verdict = assess_wdts_relevance(event, analysis)
    wdts_relevance = verdict.wdts_relevance_score
    section = assign_digest_section(event, analysis)
    coo_metadata = build_coo_item_metadata(event, analysis)
    signal_boost = _signal_boost_from_metadata(coo_metadata)
    final_score = clamp_score(
        wdts_relevance * 0.28
        + relevance * 0.20
        + urgency * 0.14
        + business_impact * 0.17
        + signal_boost * 0.11
        + source_authority * 0.05
        + recency * 0.03
        + confirmation * 0.05
        + confidence * 0.05
    )
    metadata = flatten_coo_metadata(
        {
            "ranking_version": RANKING_VERSION,
            "candidate_source": "fallback_event",
            "wdts_relevance_score": round(wdts_relevance, 6),
            "signal_type_boost": round(signal_boost, 6),
            "sales_opportunity_signal": verdict.sales_opportunity_signal,
            "is_competitor_signal": verdict.is_competitor_signal,
            "competitor_name": verdict.competitor_name,
            "score_components": {
                "wdts_relevance": round(wdts_relevance, 6),
                "relevance": round(relevance, 6),
                "urgency": round(urgency, 6),
                "confidence": round(confidence, 6),
                "source_authority": round(source_authority, 6),
                "confirmation": round(confirmation, 6),
                "recency": round(recency, 6),
                "business_impact": round(business_impact, 6),
                "signal_type_boost": round(signal_boost, 6),
            },
            "event_timestamp": _isoformat_utc(event_timestamp),
            "source_count": event.source_count,
            "article_count": event.article_count,
            "category": event.category,
            "region": event.region,
            "affected_business_area": analysis.affected_business_area,
            "briefing": coo_metadata,
            "coo_briefing": coo_metadata,
        }
    )
    return DigestCandidate(
        event=event,
        analysis=analysis,
        event_timestamp=event_timestamp,
        final_score=final_score,
        relevance_score=relevance,
        urgency_score=urgency,
        confidence_score=confidence,
        source_authority_score=source_authority,
        confirmation_score=confirmation,
        recency_score=recency,
        business_impact_score=business_impact,
        wdts_relevance_score=wdts_relevance,
        signal_type_boost=signal_boost,
        section=section,
        metadata=metadata,
    )


def select_ranked_candidates(
    candidates: list[DigestCandidate],
    *,
    limit: int,
    include_low: bool,
    monitor_limit: int = MONITOR_TIER_CAP,
    audit: DigestSelectionAudit | None = None,
) -> list[DigestCandidate]:
    eligible = _apply_low_value_fyi_filter(
        [
            item
            for item in candidates
            if item.wdts_relevance_score >= MIN_WDTS_RELEVANCE_FOR_DIGEST
            and (
                item.analysis.importance_tier in {"critical", "important", "monitor"}
                or (include_low and item.analysis.importance_tier == "low")
                or _gaming_borderline_candidate(item)
            )
        ]
    )
    sorted_candidates = sorted(eligible, key=_candidate_sort_key)
    critical = [
        item for item in sorted_candidates if _effective_importance_tier(item) == "critical"
    ]
    important = [
        item for item in sorted_candidates if _effective_importance_tier(item) == "important"
    ][:8]
    monitor = [
        item for item in sorted_candidates if _effective_importance_tier(item) == "monitor"
    ][:monitor_limit]
    low = [
        item for item in sorted_candidates if _effective_importance_tier(item) == "low"
    ]

    selected: list[DigestCandidate] = []
    for group in (critical, important, monitor, low if include_low else []):
        for item in group:
            if item not in selected:
                selected.append(item)

    selected = sorted(selected, key=_candidate_sort_key)[:limit]
    selected = _apply_signal_coverage_reservations(selected, eligible, limit=limit)
    selected_ids = {item.event.id for item in selected}

    if audit is not None:
        for item in candidates:
            headline = item.analysis.short_summary or item.event.canonical_title or ""
            source = item.event.primary_source
            if item.event.id in selected_ids:
                audit.record_ranking(
                    event_id=item.event.id,
                    headline=headline,
                    selected=True,
                    reason="within_limit",
                    final_score=item.final_score,
                    importance_tier=item.analysis.importance_tier,
                    source_id=source.id if source else None,
                    source_name=source.name if source else None,
                )
            elif item not in eligible:
                audit.record_ranking(
                    event_id=item.event.id,
                    headline=headline,
                    selected=False,
                    reason="below_wdts_or_tier_floor",
                    final_score=item.final_score,
                    importance_tier=item.analysis.importance_tier,
                    source_id=source.id if source else None,
                    source_name=source.name if source else None,
                )
            elif not include_low and item.analysis.importance_tier == "low":
                audit.record_ranking(
                    event_id=item.event.id,
                    headline=headline,
                    selected=False,
                    reason="include_low_false",
                    final_score=item.final_score,
                    importance_tier=item.analysis.importance_tier,
                    source_id=source.id if source else None,
                    source_name=source.name if source else None,
                )
            else:
                audit.record_ranking(
                    event_id=item.event.id,
                    headline=headline,
                    selected=False,
                    reason="tier_cap",
                    final_score=item.final_score,
                    importance_tier=item.analysis.importance_tier,
                    source_id=source.id if source else None,
                    source_name=source.name if source else None,
                )

    return selected


def select_top_five_candidates(candidates: list[DigestCandidate]) -> list[DigestCandidate]:
    pool = [item for item in candidates if _is_top_five_eligible(item)]
    preferred = [item for item in pool if item.analysis.importance_tier in {"critical", "important"}]
    ordered = sorted(preferred or pool, key=_strategic_sort_key)
    return ordered[:TOP_FIVE_LIMIT]


def pick_strategic_top_five_items(items: list[DigestItem]) -> list[DigestItem]:
    sorted_items = sorted(items, key=lambda value: value.rank)
    flagged = [
        item
        for item in sorted_items
        if isinstance(item.item_metadata, dict) and item.item_metadata.get("top_five_eligible")
    ]
    if flagged:
        return sorted(flagged, key=_digest_item_strategic_sort_key)[:TOP_FIVE_LIMIT]
    return []


def mark_top_five_candidates(
    selected: list[DigestCandidate],
) -> list[DigestCandidate]:
    top_five = select_top_five_candidates(selected)
    top_five_ids = {item.event.id for item in top_five}
    rank_by_id = {item.event.id: index + 1 for index, item in enumerate(top_five)}
    for candidate in selected:
        candidate.metadata["top_five_eligible"] = candidate.event.id in top_five_ids
        if candidate.event.id in top_five_ids:
            candidate.metadata["strategic_rank"] = rank_by_id[candidate.event.id]
    return selected


def assign_digest_section(event: NewsEvent, analysis: EventAIAnalysis) -> DigestSection:
    tier = analysis.importance_tier
    if tier == ImportanceTier.CRITICAL.value:
        return DigestSection.CRITICAL_ALERTS
    if tier == ImportanceTier.MONITOR.value:
        return DigestSection.MONITOR_LIST

    category = (event.category or "").lower()
    affected_area = (analysis.affected_business_area or "").lower()
    text = f"{category} {affected_area}"
    if "regulatory" in text or "compliance" in text:
        return DigestSection.REGULATORY_AND_COMPLIANCE
    if "technology" in text or "operations" in text:
        return DigestSection.TECHNOLOGY_AND_OPERATIONS
    if "gaming" in category or "casino" in category:
        return DigestSection.GAMING_AND_CASINO_MARKET
    return DigestSection.MARKET_COMPETITOR_INTELLIGENCE


def decimal_score(value: float, *, places: str = "0.001") -> Decimal:
    return Decimal(str(clamp_score(value))).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def flatten_coo_metadata(metadata: dict | None) -> dict:
    flattened = dict(metadata or {})
    briefing_metadata = flattened.get("briefing")
    coo_metadata = flattened.get("coo_briefing")
    if not isinstance(briefing_metadata, dict) and not isinstance(coo_metadata, dict):
        return flattened
    for nested_metadata in (coo_metadata, briefing_metadata):
        if not isinstance(nested_metadata, dict):
            continue
        for field in COO_METADATA_FIELDS:
            value = nested_metadata.get(field)
            if value not in (None, ""):
                flattened[field] = value
    return flattened


def clamp_score(value: float | int | Decimal | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _score_value(value: Decimal | None) -> float:
    return clamp_score(value)


def _source_authority_score(event: NewsEvent) -> float:
    source = event.primary_source
    reliability = clamp_score(source.reliability_score if source is not None else Decimal("0.50"))
    priority = source.priority if source is not None else 3
    priority_score = PRIORITY_SCORES.get(priority, 0.6)
    return clamp_score(reliability * 0.75 + priority_score * 0.25)


def _recency_score(
    event_timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
) -> float:
    total_seconds = (window_end - window_start).total_seconds()
    if total_seconds <= 0:
        return 0.0
    elapsed_seconds = (event_timestamp - window_start).total_seconds()
    return clamp_score(elapsed_seconds / total_seconds)


def _business_impact_score(event: NewsEvent, analysis: EventAIAnalysis) -> float:
    tier = analysis.importance_tier or ImportanceTier.LOW.value
    score = BUSINESS_IMPACT_BASE.get(tier, BUSINESS_IMPACT_BASE[ImportanceTier.LOW.value])
    if analysis.affected_business_area:
        score += 0.10

    category = (event.category or "").lower()
    if any(keyword in category for keyword in BOOST_KEYWORDS):
        score += 0.05

    region = (event.region or "").lower()
    if region in BOOST_REGIONS:
        score += 0.05
    return clamp_score(score)


def _fallback_analysis(
    event: NewsEvent,
    article: Article | None,
    final_score: float,
) -> EventAIAnalysis:
    title = _fallback_title(event, article)
    summary = _fallback_summary(event, article)
    return EventAIAnalysis(
        event_id=event.id,
        summary=summary,
        short_summary=title[:500],
        why_it_matters=FALLBACK_WHY_IT_MATTERS,
        key_points=[],
        entities=[],
        topics=[value for value in [event.category, event.region] if value],
        relevance_score=Decimal(str(clamp_score(final_score))),
        urgency_score=Decimal("0.200"),
        confidence_score=event.confidence_score,
        importance_tier=_fallback_importance_tier(final_score),
        suggested_action="Monitor for relevance to WDTS.",
        affected_business_area=_fallback_affected_area(event, article),
        status="success",
        source_urls=_fallback_source_urls(event, article),
        context_article_count=event.article_count or 1,
        analysis_metadata={"briefing": {}},
    )


def _fallback_importance_tier(final_score: float) -> str:
    if final_score >= 0.72:
        return ImportanceTier.IMPORTANT.value
    return ImportanceTier.MONITOR.value


def _primary_or_first_article(event: NewsEvent) -> Article | None:
    if event.primary_article is not None:
        return event.primary_article
    for event_article in event.event_articles:
        if event_article.article is not None:
            return event_article.article
    return None


def _fallback_title(event: NewsEvent, article: Article | None) -> str:
    return (
        (event.canonical_title or "").strip()
        or (article.title if article is not None and article.title else "")
        or "External development"
    )


def _fallback_summary(event: NewsEvent, article: Article | None) -> str:
    values = [
        article.excerpt if article is not None else None,
        article.clean_text if article is not None else None,
        event.canonical_title,
    ]
    for value in values:
        if value:
            return str(value).strip()[:1000]
    return "External development captured from a monitored source."


def _fallback_source_urls(event: NewsEvent, article: Article | None) -> list[str]:
    urls = []
    if article is not None:
        urls.extend([article.canonical_url, article.source_url])
    urls.extend([event.canonical_url, event.primary_source.url if event.primary_source else None])
    return list(dict.fromkeys(str(url).strip() for url in urls if str(url or "").strip()))


def _fallback_affected_area(event: NewsEvent, article: Article | None) -> str:
    text = _fallback_text(event, article)
    if any(keyword in text for keyword in {"smart table", "rfid", "table automation"}):
        return "Product"
    if any(keyword in text for keyword in {"regulator", "compliance", "licensing"}):
        return "Compliance"
    if any(keyword in text for keyword in {"semiconductor", "pcb", "supply chain"}):
        return "Operations"
    if any(keyword in text for keyword in {"tax", "tariff", "customs", "fx"}):
        return "Finance"
    return "Operations"


def _fallback_relevance_score(event: NewsEvent, article: Article | None) -> float:
    text = _fallback_text(event, article)
    score = 0.35
    if event.primary_source is not None:
        category = (event.primary_source.category or "").lower()
        region = (event.primary_source.region or "").lower()
        if category in {
            "gaming",
            "regulation",
            "compliance",
            "technology",
            "ai",
            "computer_vision",
            "semiconductors",
            "automation",
        }:
            score += 0.20
        if region in {"us", "macau", "australia", "india", "philippines", "global"}:
            score += 0.10
    if any(keyword in text for keyword in BOOST_KEYWORDS):
        score += 0.10
    if any(keyword in text for keyword in {"smart table", "rfid", "chip tracking"}):
        score += 0.20
    if any(
        keyword in text
        for keyword in {"artificial intelligence", "machine learning", "computer vision", "ai", "ml"}
    ):
        score += 0.15
    return clamp_score(score)


def _fallback_business_impact_score(event: NewsEvent, article: Article | None) -> float:
    text = _fallback_text(event, article)
    score = 0.35
    if any(keyword in text for keyword in {"gaming", "casino", "regulator", "compliance"}):
        score += 0.20
    if any(keyword in text for keyword in {"smart table", "rfid", "table automation"}):
        score += 0.25
    if any(
        keyword in text
        for keyword in {"artificial intelligence", "machine learning", "computer vision", "automation"}
    ):
        score += 0.15
    if any(keyword in text for keyword in {"semiconductor", "supply chain", "tariff"}):
        score += 0.15
    if (event.region or "").lower() in BOOST_REGIONS:
        score += 0.05
    return clamp_score(score)


def _fallback_text(event: NewsEvent, article: Article | None) -> str:
    source = event.primary_source
    values = [
        event.canonical_title,
        event.canonical_url,
        event.category,
        event.region,
        article.title if article is not None else None,
        article.excerpt if article is not None else None,
        article.clean_text if article is not None else None,
    ]
    if source is not None:
        values.extend([source.name, source.category, source.region, str(source.source_type)])
    return " ".join(str(value).lower() for value in values if value)


def _gaming_borderline_candidate(candidate: DigestCandidate) -> bool:
    if _is_entertainment_noise(candidate) or _is_low_value_fyi(candidate):
        return False
    if candidate.wdts_relevance_score < MIN_WDTS_RELEVANCE_WITH_SIGNAL:
        return False
    event = candidate.event
    source = event.primary_source
    if source is not None and (source.category or "").lower() in GAMING_SOURCE_CATEGORIES:
        return True
    return (event.category or "").lower() in GAMING_SOURCE_CATEGORIES


def _effective_importance_tier(candidate: DigestCandidate) -> str:
    tier = candidate.analysis.importance_tier or "low"
    if tier == "low" and _gaming_borderline_candidate(candidate):
        return "monitor"
    return tier


def _candidate_sort_key(candidate: DigestCandidate) -> tuple:
    tier_rank = TIER_ORDER.get(candidate.analysis.importance_tier or ImportanceTier.LOW.value, 99)
    return (
        -candidate.final_score,
        tier_rank,
        -candidate.wdts_relevance_score,
        -candidate.urgency_score,
        -candidate.relevance_score,
        -candidate.event_timestamp.timestamp(),
        str(candidate.event.id),
    )


def _strategic_sort_key(candidate: DigestCandidate) -> tuple:
    metadata = candidate.metadata or {}
    strategic = float(metadata.get("strategic_score") or 0.0)
    tier_rank = TIER_ORDER.get(candidate.analysis.importance_tier or ImportanceTier.LOW.value, 99)
    return (
        -strategic,
        tier_rank,
        -candidate.wdts_relevance_score,
        -candidate.business_impact_score,
        -candidate.final_score,
        str(candidate.event.id),
    )


def _digest_item_strategic_sort_key(item: DigestItem) -> tuple:
    metadata = item.item_metadata or {}
    strategic = float(metadata.get("strategic_score") or 0.0)
    strategic_rank = int(metadata.get("strategic_rank") or item.rank)
    return (-strategic, strategic_rank, item.rank)


def _signal_boost_from_metadata(coo_metadata: dict) -> float:
    from app.services.wdts_relevance_service import signal_type_boost

    signal_type = str(coo_metadata.get("signal_type") or "")
    boost = signal_type_boost(signal_type or None)
    if coo_metadata.get("sales_opportunity_signal"):
        boost = max(boost, signal_type_boost("sales_opportunity"))
    if coo_metadata.get("is_competitor_signal"):
        boost = max(boost, signal_type_boost("competitive_threat"))
    return boost


def _candidate_text(candidate: DigestCandidate) -> str:
    analysis = candidate.analysis
    event = candidate.event
    values = [
        event.canonical_title,
        analysis.short_summary,
        analysis.summary,
        analysis.why_it_matters,
    ]
    return " ".join(str(value).lower() for value in values if value)


def _is_entertainment_noise(candidate: DigestCandidate) -> bool:
    text = _candidate_text(candidate)
    return any(keyword in text for keyword in ENTERTAINMENT_NOISE_KEYWORDS)


def _is_low_value_fyi(candidate: DigestCandidate) -> bool:
    if _is_entertainment_noise(candidate):
        return True
    analysis = candidate.analysis
    relevance = float(analysis.relevance_score or 0)
    urgency = float(analysis.urgency_score or 0)
    tier = analysis.importance_tier or "low"
    if tier == "low" and relevance < 0.30 and urgency < 0.35:
        return True
    if tier == "monitor" and relevance < 0.25 and urgency < 0.30:
        return True
    metadata = candidate.metadata or {}
    if metadata.get("urgency") == "FYI" and relevance < 0.30 and urgency < 0.35:
        return True
    return False


def _apply_low_value_fyi_filter(eligible: list[DigestCandidate]) -> list[DigestCandidate]:
    low_value_ids = {item.event.id for item in eligible if _is_low_value_fyi(item)}
    if not low_value_ids:
        return eligible
    strong = [item for item in eligible if item.event.id not in low_value_ids]
    return strong if strong else eligible


def _coo_section_from_candidate(candidate: DigestCandidate) -> str:
    metadata = candidate.metadata or {}
    briefing = metadata.get("briefing")
    coo = metadata.get("coo_briefing")
    if not isinstance(briefing, dict):
        briefing = {}
    if not isinstance(coo, dict):
        coo = {}
    return str(
        metadata.get("briefing_section")
        or metadata.get("coo_section")
        or briefing.get("briefing_section")
        or coo.get("briefing_section")
        or ""
    )


def _signal_type_from_candidate(candidate: DigestCandidate) -> str:
    metadata = candidate.metadata or {}
    briefing = metadata.get("briefing")
    coo = metadata.get("coo_briefing")
    if not isinstance(briefing, dict):
        briefing = {}
    if not isinstance(coo, dict):
        coo = {}
    return str(
        metadata.get("signal_type")
        or briefing.get("signal_type")
        or coo.get("signal_type")
        or ""
    )


def _is_competitor_coverage_candidate(candidate: DigestCandidate) -> bool:
    metadata = candidate.metadata or {}
    if metadata.get("is_competitor_signal"):
        return True
    signal_type = _signal_type_from_candidate(candidate)
    if signal_type == "competitive_threat":
        return True
    section = _coo_section_from_candidate(candidate)
    return WATCHLIST_SECTION in section and signal_type in {
        "competitive_threat",
        "sales_opportunity",
        "",
    }


def _is_smart_table_coverage_candidate(candidate: DigestCandidate) -> bool:
    return SMART_TABLE_SECTION in _coo_section_from_candidate(candidate)


def _apply_signal_coverage_reservations(
    selected: list[DigestCandidate],
    eligible: list[DigestCandidate],
    *,
    limit: int,
) -> list[DigestCandidate]:
    if not eligible:
        return selected
    reserved = list(selected)
    selected_ids = {item.event.id for item in reserved}
    for predicate in (_is_competitor_coverage_candidate, _is_smart_table_coverage_candidate):
        pool = [
            item
            for item in eligible
            if predicate(item) and item.event.id not in selected_ids
        ]
        if not pool:
            continue
        best = sorted(pool, key=_candidate_sort_key)[0]
        if best.event.id in selected_ids:
            continue
        if len(reserved) < limit:
            reserved.append(best)
            selected_ids.add(best.event.id)
            continue
        droppable = [
            item
            for item in reserved
            if not _is_competitor_coverage_candidate(item)
            and not _is_smart_table_coverage_candidate(item)
        ]
        if not droppable:
            continue
        weakest = sorted(droppable, key=_candidate_sort_key)[-1]
        if _candidate_sort_key(best) < _candidate_sort_key(weakest):
            reserved = [item for item in reserved if item.event.id != weakest.event.id]
            reserved.append(best)
            selected_ids.add(best.event.id)
            selected_ids.discard(weakest.event.id)
    return sorted(reserved, key=_candidate_sort_key)[:limit]


def _has_strong_executive_signal(candidate: DigestCandidate) -> bool:
    metadata = candidate.metadata or {}
    signal_type = _signal_type_from_candidate(candidate)
    if signal_type in STRONG_EXECUTIVE_SIGNAL_TYPES:
        return True
    if metadata.get("is_competitor_signal") or metadata.get("sales_opportunity_signal"):
        return True
    if metadata.get("urgency") in {"Discuss", "Immediate"}:
        return True
    tier = candidate.analysis.importance_tier or "low"
    return tier in {"critical", "important"}


def _is_top_five_eligible(candidate: DigestCandidate) -> bool:
    if candidate.wdts_relevance_score < MIN_WDTS_RELEVANCE_FOR_TOP_FIVE:
        return False
    if _is_low_value_fyi(candidate):
        return False
    tier = candidate.analysis.importance_tier or "low"
    if tier == "low":
        return False
    metadata = candidate.metadata or {}
    strategic = float(metadata.get("strategic_score") or 0.0)
    if strategic < MIN_STRATEGIC_SCORE_FOR_TOP_FIVE:
        return False
    if tier in {"critical", "important"}:
        return True
    if _has_strong_executive_signal(candidate):
        return True
    relevance = float(candidate.analysis.relevance_score or 0)
    urgency = float(candidate.analysis.urgency_score or 0)
    return (
        relevance >= MIN_AI_RELEVANCE_FOR_TOP_FIVE_MONITOR
        or urgency >= MIN_URGENCY_FOR_TOP_FIVE_MONITOR
    )


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
