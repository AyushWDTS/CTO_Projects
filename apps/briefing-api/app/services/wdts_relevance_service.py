import re
from dataclasses import dataclass

from app.data.competitor_watchlist import match_competitor
from app.data.wdts_signals import (
    FINANCE_IMPACT_KEYWORDS,
    FINANCE_REJECT_KEYWORDS,
    detect_sales_opportunity,
)
from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis

MIN_WDTS_RELEVANCE_SCORE = 0.38
MIN_WDTS_RELEVANCE_WITH_SIGNAL = 0.30
MIN_WDTS_RELEVANCE_FOR_DIGEST = 0.38
MIN_WDTS_RELEVANCE_FOR_TOP_FIVE = 0.60
MIN_AI_RELEVANCE_SCORE = 0.35
MIN_AI_RELEVANCE_WITH_SIGNAL = 0.22

GAMING_SOURCE_CATEGORIES = {
    "gaming",
    "casino",
    "regulation",
    "compliance",
    "hospitality",
    "ai",
    "computer_vision",
    "semiconductors",
    "automation",
    "technology",
}
GAMING_DOMAIN_KEYWORDS = {
    "gaming",
    "casino",
    "smart table",
    "smart tables",
    "table games",
    "table game",
    "rfid",
    "chip tracking",
    "table automation",
    "land-based",
    "electronic table",
    "las vegas",
    "macau",
    "convention",
    "resort",
    "gaming floor",
}

WDTS_DOMAIN_KEYWORDS = {
    "gaming",
    "casino",
    "smart table",
    "smart tables",
    "table games",
    "table game",
    "rfid",
    "chip tracking",
    "table automation",
    "gli",
    "bmm",
    "ai",
    "artificial intelligence",
    "machine learning",
    "computer vision",
    "computer-vision",
    "automation",
    "semiconductor",
    "semiconductors",
    "pcb",
    "supply chain",
    "tariff",
    "tariffs",
    "tax",
    "customs",
    "competitor",
    "customer",
    "supplier",
    "macau",
    "australia",
    "india",
    "philippines",
    "israel",
    "regulator",
    "licensing",
    "compliance",
    "land-based",
    "electronic table",
    "cashless",
    "tabletrac",
    "interblock",
}

WDTS_REJECT_PATTERNS = [
    r"\bshares?\s+(surge|soar|jump|rise|fall|drop|plunge)\b",
    r"\bstock\s+price\b",
    r"\bmarket\s+cap\b",
    r"\b(analyst|investor)\s+(rating|sentiment)\b",
    r"\bzoo\b",
    r"\bcelebrity\b",
    r"\bwedding\b",
    r"\bhuman.interest\b",
    r"\bsalary\s+stunt\b",
]

SIGNAL_TYPE_BOOSTS = {
    "sales_opportunity": 1.0,
    "competitive_threat": 0.95,
    "regulatory_development": 0.90,
    "manufacturing_component_risk": 0.85,
    "compliance_opportunity": 0.80,
    "customer_adoption_signal": 0.75,
    "product_roadmap_implication": 0.70,
    "strategic_market_signal": 0.65,
}

NO_WDTS_RELEVANCE_PHRASES = [
    "no wdts relevance",
    "not relevant to wdts",
    "no direct wdts",
    "limited wdts impact",
    "minimal wdts impact",
]


@dataclass
class RelevanceVerdict:
    wdts_relevance_score: float
    is_eligible: bool
    reject_reason: str | None
    domain_hits: list[str]
    sales_opportunity_signal: bool = False
    is_competitor_signal: bool = False
    competitor_name: str | None = None
    finance_noise: bool = False


def assess_wdts_relevance(event: NewsEvent, analysis: EventAIAnalysis) -> RelevanceVerdict:
    text = _relevance_text(event, analysis)
    domain_text = _domain_match_text(event, analysis)
    domain_hits = _domain_hits(domain_text)
    reject_reason = _reject_reason(text, analysis, domain_hits, domain_text)
    score = _compute_wdts_score(
        text,
        domain_text,
        analysis,
        domain_hits,
        reject_reason,
    )
    sales_signal = detect_sales_opportunity(text)
    competitor = match_competitor(text)
    finance_noise = _is_finance_noise(text)
    if finance_noise and reject_reason is None:
        reject_reason = "finance_noise"

    strong_signal = _has_strong_wdts_signal(
        event,
        domain_hits=domain_hits,
        headline_text=_headline_text(event, analysis),
        competitor=competitor,
        sales_signal=sales_signal,
    )
    min_relevance = MIN_WDTS_RELEVANCE_WITH_SIGNAL if strong_signal else MIN_WDTS_RELEVANCE_SCORE

    is_eligible = reject_reason is None and score >= min_relevance
    if (
        reject_reason is None
        and not strong_signal
        and not domain_hits
        and score < MIN_WDTS_RELEVANCE_SCORE
    ):
        reject_reason = "no_domain_match"
        is_eligible = False
    if reject_reason is None and _has_low_ai_relevance(
        analysis,
        strong_signal=strong_signal,
        wdts_score=score,
    ):
        reject_reason = "low_ai_relevance"
        is_eligible = False
    if reject_reason is not None:
        is_eligible = False

    return RelevanceVerdict(
        wdts_relevance_score=score,
        is_eligible=is_eligible,
        reject_reason=reject_reason,
        domain_hits=domain_hits,
        sales_opportunity_signal=sales_signal,
        is_competitor_signal=competitor is not None,
        competitor_name=competitor,
        finance_noise=finance_noise,
    )


def signal_type_boost(signal_type: str | None) -> float:
    if not signal_type:
        return 0.0
    return SIGNAL_TYPE_BOOSTS.get(signal_type, 0.0)


def strategic_score(
    *,
    wdts_relevance_score: float,
    business_impact_score: float,
    signal_type: str | None,
) -> float:
    boost = signal_type_boost(signal_type)
    return min(
        1.0,
        wdts_relevance_score * 0.40 + business_impact_score * 0.35 + boost * 0.25,
    )


def _relevance_text(event: NewsEvent, analysis: EventAIAnalysis) -> str:
    source = event.primary_source
    values = [
        event.canonical_title,
        event.canonical_url,
        event.category,
        event.region,
        analysis.summary,
        analysis.short_summary,
        analysis.why_it_matters,
        analysis.suggested_action,
        analysis.affected_business_area,
        " ".join(str(topic) for topic in (analysis.topics or [])),
    ]
    metadata = analysis.analysis_metadata or {}
    raw = metadata.get("briefing") or metadata.get("coo_briefing")
    if isinstance(raw, dict):
        values.append(str(raw.get("why_it_matters_to_wdts") or ""))
        values.append(str(raw.get("signal_type") or ""))
    if source is not None:
        values.extend([source.name, source.category, source.region, str(source.source_type)])
    return " ".join(str(value).lower() for value in values if value)


def _domain_match_text(event: NewsEvent, analysis: EventAIAnalysis) -> str:
    """Headline + source context only — excludes long AI summaries that hallucinate domain keywords."""
    source = event.primary_source
    values = [
        event.canonical_title,
        analysis.short_summary,
        event.category,
        event.region,
    ]
    if source is not None:
        values.extend([source.name, source.category, source.region])
    return " ".join(str(value).lower() for value in values if value)


def _headline_text(event: NewsEvent, analysis: EventAIAnalysis) -> str:
    return " ".join(
        str(value).lower()
        for value in [event.canonical_title, analysis.short_summary]
        if value
    )


def _domain_hits(text: str) -> list[str]:
    hits = []
    for keyword in WDTS_DOMAIN_KEYWORDS:
        if len(keyword) <= 4:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(keyword)
        elif keyword in text:
            hits.append(keyword)
    return hits


def _reject_reason(
    text: str,
    analysis: EventAIAnalysis,
    domain_hits: list[str],
    domain_text: str,
) -> str | None:
    for pattern in WDTS_REJECT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "human_interest_or_stock_noise"
    if _is_finance_noise(text):
        return "finance_noise"
    if _states_no_wdts_relevance(text, analysis):
        return "no_wdts_relevance_stated"
    if not domain_hits and _compute_base_score(domain_text, analysis) < MIN_WDTS_RELEVANCE_SCORE:
        return "no_domain_match"
    return None


def _is_finance_noise(text: str) -> bool:
    if not any(keyword in text for keyword in FINANCE_REJECT_KEYWORDS):
        return False
    return not any(keyword in text for keyword in FINANCE_IMPACT_KEYWORDS)


def _states_no_wdts_relevance(text: str, analysis: EventAIAnalysis) -> bool:
    metadata = analysis.analysis_metadata or {}
    raw = metadata.get("briefing") or metadata.get("coo_briefing")
    why_wdts = ""
    if isinstance(raw, dict):
        why_wdts = str(raw.get("why_it_matters_to_wdts") or "").lower()
    combined = f"{text} {why_wdts} {str(analysis.why_it_matters or '').lower()}"
    return any(phrase in combined for phrase in NO_WDTS_RELEVANCE_PHRASES)


def _has_strong_wdts_signal(
    event: NewsEvent,
    *,
    domain_hits: list[str],
    headline_text: str,
    competitor: str | None,
    sales_signal: bool,
) -> bool:
    if competitor or sales_signal:
        return True
    headline_hits = _domain_hits(headline_text)
    if any(hit in GAMING_DOMAIN_KEYWORDS for hit in headline_hits):
        return True
    source = event.primary_source
    if source is not None:
        category = (source.category or "").lower()
        if category in GAMING_SOURCE_CATEGORIES:
            return True
    event_category = (event.category or "").lower()
    if event_category in GAMING_SOURCE_CATEGORIES:
        return True
    return False


def _has_low_ai_relevance(
    analysis: EventAIAnalysis,
    *,
    strong_signal: bool = False,
    wdts_score: float = 0.0,
) -> bool:
    if analysis.relevance_score is None:
        return False
    if strong_signal and wdts_score >= MIN_WDTS_RELEVANCE_WITH_SIGNAL:
        return False
    threshold = MIN_AI_RELEVANCE_WITH_SIGNAL if strong_signal else MIN_AI_RELEVANCE_SCORE
    return float(analysis.relevance_score) < threshold


def _compute_wdts_score(
    text: str,
    domain_text: str,
    analysis: EventAIAnalysis,
    domain_hits: list[str],
    reject_reason: str | None,
) -> float:
    if reject_reason in {"human_interest_or_stock_noise", "finance_noise", "no_wdts_relevance_stated"}:
        return 0.0
    score = _compute_base_score(domain_text, analysis)
    score += min(0.25, len(domain_hits) * 0.05)
    if match_competitor(text):
        score += 0.10
    if detect_sales_opportunity(text):
        score += 0.10
    ai_relevance = float(analysis.relevance_score) if analysis.relevance_score is not None else None
    strong_gaming = any(hit in GAMING_DOMAIN_KEYWORDS for hit in domain_hits)
    if ai_relevance is not None:
        if strong_gaming:
            score = score * 0.80 + ai_relevance * 0.20
        else:
            score = score * 0.60 + ai_relevance * 0.40
    return min(1.0, max(0.0, score))


def _compute_base_score(text: str, analysis: EventAIAnalysis) -> float:
    score = 0.20
    if any(keyword in text for keyword in {"gaming", "casino", "smart table", "rfid"}):
        score += 0.25
    if any(keyword in text for keyword in {"regulator", "compliance", "tariff", "semiconductor"}):
        score += 0.15
    ai_relevance = float(analysis.relevance_score) if analysis.relevance_score is not None else 0.0
    if ai_relevance >= 0.55:
        score += 0.15
    return min(1.0, score)
