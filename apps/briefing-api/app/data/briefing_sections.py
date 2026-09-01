from enum import StrEnum
import re
from typing import Any

from app.data.competitor_watchlist import match_competitor
from app.data.wdts_signals import (
    FINANCE_IMPACT_KEYWORDS,
    FINANCE_REJECT_KEYWORDS,
    detect_sales_opportunity,
)
from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis


class BriefingSection(StrEnum):
    TOP_STORIES = "Top Stories"
    AI_ML_CV = "AI, ML & Computer Vision"
    SMART_TABLES = "Smart Tables & Casino Tech"
    SEMICONDUCTORS = "Semiconductors & Components"
    AUTOMATION = "Automation & Operations Tech"
    COMPETITORS = "Competitors & Industry Watch"
    REGULATION = "Regulation & Compliance"
    ACTION_ITEMS = "Action Items"


# Backward-compatible alias during migration of callers/tests.
COOBriefingSection = BriefingSection

CONTENT_SECTION_ORDER = [
    BriefingSection.AI_ML_CV.value,
    BriefingSection.SMART_TABLES.value,
    BriefingSection.SEMICONDUCTORS.value,
    BriefingSection.AUTOMATION.value,
    BriefingSection.COMPETITORS.value,
    BriefingSection.REGULATION.value,
]

DASHBOARD_SECTION_ORDER = [
    BriefingSection.TOP_STORIES.value,
    *CONTENT_SECTION_ORDER,
    BriefingSection.ACTION_ITEMS.value,
]

# Legacy name used by older digest/email-era helpers.
EMAIL_SECTION_ORDER = DASHBOARD_SECTION_ORDER

ALLOWED_BRIEFING_CATEGORIES = {
    "AI/ML",
    "Computer Vision",
    "Smart Tables",
    "Semiconductors",
    "Automation",
    "Casino Tech",
    "Competitor",
    "Customer",
    "Supplier",
    "Regulation",
    "Compliance",
    "Operations",
}
ALLOWED_COO_CATEGORIES = ALLOWED_BRIEFING_CATEGORIES
ALLOWED_URGENCY_VALUES = {"FYI", "Monitor", "Discuss", "Immediate"}
ALLOWED_SUGGESTED_OWNERS = {
    "Sales",
    "Product",
    "Engineering",
    "Operations",
    "Finance",
    "Legal",
    "Executive Team",
}
ALLOWED_ACTION_BUCKETS = {"No action", "Monitor", "Discuss with team", "Immediate attention"}

TOP_5_LIMIT = 5
TOP_STORIES_LIMIT = TOP_5_LIMIT
CONTENT_SECTION_LIMIT = 5
ACTION_ITEMS_LIMIT = 5

AI_ML_CV_KEYWORDS = {
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "computer vision",
    "generative ai",
    "large language model",
    "llm",
    "neural network",
    "object detection",
    "image recognition",
    "vision model",
    "opencv",
    "nvidia",
    "cuda",
    "edge ai",
    "inference",
    "foundation model",
}
SMART_TABLE_KEYWORDS = {
    "smart table",
    "smart tables",
    "table games",
    "table game",
    "table management",
    "casino technology",
    "casino tech",
    "rfid chip",
    "rfid chips",
    "automated bet recognition",
    "table game automation",
    "player rating",
    "player ratings",
    "chip tracking",
    "dealer assist",
    "dealer-assist",
    "walker digital",
    "gli",
    "bmm",
    "angel eye",
    "pragmatic play live",
    "lightning roulette",
    "electronic table",
    "cashless",
    "table automation",
    "tabletrac",
    "interblock",
}
SMART_TABLE_PRECEDENCE_KEYWORDS = {
    "table game",
    "table games",
    "rfid",
    "casino floor",
    "smart table",
    "chip tracking",
    "electronic table",
    "computer vision",
}
SEMICONDUCTOR_KEYWORDS = {
    "semiconductor",
    "semiconductors",
    "electronics",
    "rfid",
    "pcb",
    "chips",
    "chip shortage",
    "foundry",
    "wafer",
    "asic",
    "fpga",
    "logistics",
    "freight",
    "component availability",
    "supply chain",
}
AUTOMATION_KEYWORDS = {
    "automation",
    "robotics",
    "industrial automation",
    "process automation",
    "iot",
    "edge computing",
    "factory automation",
    "optical recognition",
    "sensor fusion",
}
REGULATION_KEYWORDS = {
    "gaming",
    "casino",
    "regulator",
    "licensing",
    "enforcement",
    "compliance",
    "aml",
    "land-based",
    "gambling commission",
}
COMPETITOR_KEYWORDS = {
    "competitor",
    "customer",
    "supplier",
    "earnings",
    "product launch",
    "investor relations",
}
TRADE_SUPPLY_KEYWORDS = {
    "tax",
    "tariff",
    "tariffs",
    "customs",
    "accounting",
    "fx",
    "import",
    "export",
    "import duty",
    "incentive",
    "incentives",
    "transfer pricing",
}

CATEGORY_TO_BRIEFING_CATEGORY = {
    "ai": "AI/ML",
    "ml": "AI/ML",
    "computer_vision": "Computer Vision",
    "aml": "Compliance",
    "casino_operations": "Casino Tech",
    "compliance": "Compliance",
    "electronics": "Semiconductors",
    "fintech": "Operations",
    "gaming": "Casino Tech",
    "hospitality": "Operations",
    "payments": "Operations",
    "regulation": "Regulation",
    "semiconductors": "Semiconductors",
    "technology": "Automation",
    "automation": "Automation",
}


def build_briefing_item_metadata(event: NewsEvent, analysis: EventAIAnalysis) -> dict[str, Any]:
    ai_metadata = _normalized_ai_metadata(analysis)
    if ai_metadata:
        return _enrich_signal_metadata(_with_source_context(ai_metadata, event), event, analysis)

    mapped = _deterministic_mapping(event, analysis)
    if mapped:
        return _enrich_signal_metadata(_with_source_context(mapped, event), event, analysis)

    return _enrich_signal_metadata(
        _with_source_context(
            _metadata_payload(
                section=(
                    BriefingSection.SMART_TABLES.value
                    if _contains(_mapping_text(event, analysis), SMART_TABLE_KEYWORDS)
                    else BriefingSection.AUTOMATION.value
                ),
                category=_category_from_source(event),
                country_or_region=_region_from_event(event),
                urgency="FYI",
                suggested_owner="Executive Team",
                action_bucket="No action",
                why_it_matters="Potential external development to monitor for WDTS relevance.",
                mapping_source="fallback",
            ),
            event,
        ),
        event,
        analysis,
    )


# Backward-compatible alias.
build_coo_item_metadata = build_briefing_item_metadata


def _enrich_signal_metadata(
    payload: dict[str, Any],
    event: NewsEvent,
    analysis: EventAIAnalysis,
) -> dict[str, Any]:
    text = _mapping_text(event, analysis)
    if detect_sales_opportunity(text):
        payload["sales_opportunity_signal"] = True
        if not payload.get("signal_type"):
            payload["signal_type"] = "sales_opportunity"
            if payload.get("briefing_category") == "Operations":
                payload["briefing_category"] = "Customer"
                payload["suggested_owner"] = "Sales"
    competitor = match_competitor(text)
    if competitor:
        payload["is_competitor_signal"] = True
        payload["competitor_name"] = competitor
        if not payload.get("signal_type"):
            payload["signal_type"] = "competitive_threat"
        if payload.get("briefing_section") != BriefingSection.COMPETITORS.value:
            payload["briefing_section"] = BriefingSection.COMPETITORS.value
            payload["briefing_category"] = "Competitor"
    return payload


def _normalized_ai_metadata(analysis: EventAIAnalysis) -> dict[str, Any] | None:
    raw = (analysis.analysis_metadata or {}).get("briefing")
    if not isinstance(raw, dict):
        # Accept legacy coo_briefing payloads from older analyses.
        raw = (analysis.analysis_metadata or {}).get("coo_briefing")
    if not isinstance(raw, dict):
        return None

    section = _allowed(
        raw.get("briefing_section") or raw.get("coo_section"),
        CONTENT_SECTION_ORDER,
    )
    if section is None:
        section = _legacy_section_map(raw.get("briefing_section") or raw.get("coo_section"))
    if section is None:
        return None

    urgency = _allowed(raw.get("urgency"), ALLOWED_URGENCY_VALUES) or _urgency_from_scores(analysis)
    score_urgency = _urgency_from_scores(analysis)
    if urgency == "FYI" and score_urgency != "FYI":
        urgency = score_urgency
    action_bucket = _action_bucket_from_urgency(urgency)
    signal_type = _clean_string(raw.get("signal_type"))
    if signal_type is None and raw.get("sales_opportunity_signal"):
        signal_type = "sales_opportunity"
    category = (
        _allowed(raw.get("category") or raw.get("coo_category"), ALLOWED_BRIEFING_CATEGORIES)
        or "Operations"
    )
    return _metadata_payload(
        section=section,
        category=category,
        country_or_region=str(raw.get("country_or_region") or raw.get("region") or "Unknown"),
        urgency=urgency,
        suggested_owner=(
            _allowed(raw.get("suggested_owner"), ALLOWED_SUGGESTED_OWNERS)
            or "Executive Team"
        ),
        action_bucket=action_bucket,
        why_it_matters=(
            _clean_string(raw.get("why_it_matters_to_wdts"))
            or _clean_string(raw.get("why_it_matters"))
            or analysis.why_it_matters
            or "Potential external signal for WDTS monitoring."
        ),
        mapping_source="ai_metadata",
        signal_type=signal_type,
        sales_opportunity_signal=bool(raw.get("sales_opportunity_signal")),
        is_competitor_signal=bool(raw.get("is_competitor_signal")),
    )


def _deterministic_mapping(event: NewsEvent, analysis: EventAIAnalysis) -> dict[str, Any] | None:
    text = _mapping_text(event, analysis)
    source = event.primary_source
    section = None
    category = _category_from_source(event)
    owner = "Executive Team"
    signal_type = None
    sales_signal = detect_sales_opportunity(text)
    competitor = match_competitor(text)

    if competitor is not None:
        section, category, owner = (
            BriefingSection.COMPETITORS.value,
            "Competitor",
            "Executive Team",
        )
        signal_type = "competitive_threat"
    elif sales_signal:
        section, category, owner = (
            BriefingSection.SMART_TABLES.value,
            "Customer",
            "Sales",
        )
        signal_type = "sales_opportunity"
    elif _contains(text, AI_ML_CV_KEYWORDS):
        section, category, owner = BriefingSection.AI_ML_CV.value, "AI/ML", "Engineering"
    elif _contains(text, SMART_TABLE_KEYWORDS):
        section, category, owner = BriefingSection.SMART_TABLES.value, "Smart Tables", "Product"
    elif _contains(text, SEMICONDUCTOR_KEYWORDS) or _contains_trade_supply_impact(text):
        section, category, owner = (
            BriefingSection.SEMICONDUCTORS.value,
            "Semiconductors",
            "Operations",
        )
    elif _contains(text, AUTOMATION_KEYWORDS):
        section, category, owner = BriefingSection.AUTOMATION.value, "Automation", "Engineering"
    elif source is not None and str(source.source_type) == "company_ir":
        section, category, owner = (
            BriefingSection.COMPETITORS.value,
            "Competitor",
            "Executive Team",
        )
    elif _contains(text, COMPETITOR_KEYWORDS):
        section, category, owner = BriefingSection.COMPETITORS.value, category, "Executive Team"
    elif _contains(text, REGULATION_KEYWORDS):
        section, category, owner = BriefingSection.REGULATION.value, "Regulation", "Legal"

    if section is None:
        return None

    if (
        section == BriefingSection.SEMICONDUCTORS.value
        and _contains(text, SMART_TABLE_KEYWORDS)
        and _contains(text, SMART_TABLE_PRECEDENCE_KEYWORDS)
    ):
        section, category, owner = BriefingSection.SMART_TABLES.value, "Smart Tables", "Product"

    urgency = "Monitor" if analysis.id is None else _urgency_from_scores(analysis)
    score_urgency = _urgency_from_scores(analysis)
    if urgency == "FYI" and score_urgency != "FYI":
        urgency = score_urgency
    return _metadata_payload(
        section=section,
        category=category,
        country_or_region=_region_from_event(event),
        urgency=urgency,
        suggested_owner=owner,
        action_bucket=_action_bucket_from_urgency(urgency),
        why_it_matters=analysis.why_it_matters or "Potential external signal for WDTS monitoring.",
        mapping_source="deterministic_mapping",
        signal_type=signal_type,
        sales_opportunity_signal=sales_signal,
        is_competitor_signal=competitor is not None,
    )


def _metadata_payload(
    *,
    section: str,
    category: str,
    country_or_region: str,
    urgency: str,
    suggested_owner: str,
    action_bucket: str,
    why_it_matters: str,
    mapping_source: str,
    signal_type: str | None = None,
    sales_opportunity_signal: bool = False,
    is_competitor_signal: bool = False,
) -> dict[str, Any]:
    payload = {
        "briefing_section": section,
        "briefing_category": category,
        # Legacy flattened keys still read by some ranking helpers/tests.
        "coo_section": section,
        "coo_category": category,
        "country_or_region": country_or_region,
        "urgency": urgency,
        "suggested_owner": suggested_owner,
        "action_bucket": action_bucket,
        "why_it_matters_to_wdts": why_it_matters,
        "mapping_source": mapping_source,
    }
    if signal_type:
        payload["signal_type"] = signal_type
    if sales_opportunity_signal:
        payload["sales_opportunity_signal"] = True
    if is_competitor_signal:
        payload["is_competitor_signal"] = True
    return payload


def _with_source_context(payload: dict[str, Any], event: NewsEvent) -> dict[str, Any]:
    source = event.primary_source
    return {
        **payload,
        "source_name": source.name if source is not None else "Unknown source",
        "event_date": (
            event.published_at or event.first_seen_at or event.created_at
        ).date().isoformat(),
    }


def _mapping_text(event: NewsEvent, analysis: EventAIAnalysis) -> str:
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
    if source is not None:
        values.extend(
            [source.name, source.url, source.category, source.region, str(source.source_type)]
        )
    return " ".join(str(value).lower() for value in values if value)


def _contains_trade_supply_impact(text: str) -> bool:
    if any(keyword in text for keyword in FINANCE_REJECT_KEYWORDS):
        if not any(keyword in text for keyword in FINANCE_IMPACT_KEYWORDS):
            return False
    return _contains(text, TRADE_SUPPLY_KEYWORDS) and any(
        keyword in text for keyword in FINANCE_IMPACT_KEYWORDS
    )


ACTIONABLE_SIGNAL_TYPES = {
    "sales_opportunity",
    "competitive_threat",
    "regulatory_development",
    "manufacturing_component_risk",
    "ai_product_signal",
    "technology_adoption_signal",
}


def is_digest_action_item(metadata: dict[str, Any], suggested_action: str | None = None) -> bool:
    action_bucket = metadata.get("action_bucket")
    urgency = metadata.get("urgency")
    signal_type = str(metadata.get("signal_type") or "")
    if action_bucket in {"Monitor", "Discuss with team", "Immediate attention"}:
        return True
    if urgency in {"Discuss", "Immediate"}:
        return True
    if signal_type in ACTIONABLE_SIGNAL_TYPES:
        return True
    if metadata.get("sales_opportunity_signal") or metadata.get("is_competitor_signal"):
        return True
    if suggested_action and suggested_action.strip().lower() not in {"", "no action"}:
        return True
    return False


def _contains(text: str, keywords: set[str]) -> bool:
    for keyword in keywords:
        if len(keyword) <= 4:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
            continue
        if keyword in text:
            return True
    return False


def _category_from_source(event: NewsEvent) -> str:
    source_category = event.primary_source.category if event.primary_source is not None else None
    return CATEGORY_TO_BRIEFING_CATEGORY.get(
        (event.category or source_category or "").lower(),
        "Operations",
    )


def _region_from_event(event: NewsEvent) -> str:
    source_region = event.primary_source.region if event.primary_source is not None else None
    return event.region or source_region or "Global"


def _urgency_from_scores(analysis: EventAIAnalysis) -> str:
    relevance = float(analysis.relevance_score or 0)
    urgency = float(analysis.urgency_score or 0)
    if urgency >= 0.80 or (relevance >= 0.85 and urgency >= 0.65):
        return "Immediate"
    if urgency >= 0.60 or relevance >= 0.70:
        return "Discuss"
    if urgency >= 0.35 or relevance >= 0.45:
        return "Monitor"
    return "FYI"


def _action_bucket_from_urgency(urgency: str) -> str:
    return {
        "Immediate": "Immediate attention",
        "Discuss": "Discuss with team",
        "Monitor": "Monitor",
        "FYI": "No action",
    }.get(urgency, "No action")


def _legacy_section_map(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    mapping = {
        "Brick-and-Mortar Gaming Markets": BriefingSection.SMART_TABLES.value,
        "Smart Table Games": BriefingSection.SMART_TABLES.value,
        "WDTS Operating Markets": BriefingSection.AUTOMATION.value,
        "Manufacturing and Component Supply": BriefingSection.SEMICONDUCTORS.value,
        "Finance, Tax, Tariffs, and Accounting": BriefingSection.SEMICONDUCTORS.value,
        "Customer / Competitor / Supplier Watchlist": BriefingSection.COMPETITORS.value,
        "Top 5 Things Mike Should Know Today": BriefingSection.TOP_STORIES.value,
    }
    return mapping.get(value.strip())


def _allowed(value: Any, allowed: set[str] | list[str]) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized in allowed else None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
