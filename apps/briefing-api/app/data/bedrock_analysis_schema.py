from app.schemas.event_analysis import (
    ALLOWED_ACTION_BUCKETS,
    ALLOWED_BRIEFING_CATEGORIES,
    ALLOWED_BRIEFING_SECTIONS,
    ALLOWED_URGENCIES,
)

# Backward-compatible alias.
ALLOWED_COO_CATEGORIES = ALLOWED_BRIEFING_CATEGORIES

BEDROCK_ANALYSIS_REQUIRED_FIELDS = [
    "summary",
    "short_summary",
    "why_it_matters",
    "key_points",
    "relevance_score",
    "urgency_score",
    "briefing_section",
    "category",
    "signal_type",
    "action_bucket",
    "urgency",
    "why_it_matters_to_wdts",
    "suggested_action",
]

NON_ACTIONABLE_SUGGESTIONS = frozenset({"", "no action"})


def is_actionable_suggestion(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() not in NON_ACTIONABLE_SUGGESTIONS


def bedrock_event_analysis_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-2 contextual sentences; must not duplicate short_summary",
            },
            "short_summary": {
                "type": "string",
                "description": "Single headline sentence",
            },
            "why_it_matters": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "suggested_action": {
                "type": "string",
                "description": (
                    "Specific next step for WDTS product, engineering, or commercial teams. "
                    "Use null or omit when no action is needed."
                ),
            },
            "action_bucket": {
                "type": "string",
                "enum": sorted(ALLOWED_ACTION_BUCKETS),
            },
            "urgency": {
                "type": "string",
                "enum": sorted(ALLOWED_URGENCIES),
            },
            "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
            "urgency_score": {"type": "number", "minimum": 0, "maximum": 1},
            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
            "briefing_section": {
                "type": "string",
                "enum": sorted(ALLOWED_BRIEFING_SECTIONS),
            },
            "category": {
                "type": "string",
                "enum": sorted(ALLOWED_BRIEFING_CATEGORIES),
            },
            "country_or_region": {"type": "string"},
            "suggested_owner": {
                "type": "string",
                "enum": [
                    "Sales",
                    "Product",
                    "Engineering",
                    "Operations",
                    "Finance",
                    "Legal",
                    "Executive Team",
                ],
            },
            "why_it_matters_to_wdts": {"type": "string"},
            "signal_type": {
                "type": "string",
                "enum": [
                    "sales_opportunity",
                    "competitive_threat",
                    "product_roadmap_implication",
                    "customer_adoption_signal",
                    "regulatory_development",
                    "manufacturing_component_risk",
                    "compliance_opportunity",
                    "strategic_market_signal",
                    "ai_product_signal",
                    "technology_adoption_signal",
                ],
            },
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["name", "type"],
                },
            },
            "topics": {"type": "array", "items": {"type": "string"}},
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "negative", "mixed", "unknown"],
            },
            "importance_tier": {
                "type": "string",
                "enum": ["critical", "important", "monitor", "low"],
            },
            "affected_business_area": {"type": "string"},
        },
        "required": BEDROCK_ANALYSIS_REQUIRED_FIELDS,
    }
