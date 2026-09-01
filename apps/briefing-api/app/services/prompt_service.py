import json

from app.services.event_context_service import EventContext

PROMPT_VERSION = "wdts_dashboard_v1"


def build_event_analysis_prompt(context: EventContext) -> str:
    event = context.event
    payload = {
        "instructions": [
            "Return JSON only.",
            "Use only the provided event, article, and source context.",
            (
                "Do not invent facts, companies, people, locations, figures, dates, "
                "or regulatory meaning."
            ),
            "Return null or unknown when context is insufficient.",
            (
                "Focus on WDTS business relevance: AI/ML, computer vision, smart tables, "
                "casino technology, semiconductors/chips, automation, competitors, and "
                "related commercial or regulatory signals."
            ),
            (
                "Score relevance_score for WDTS product and business impact only — not "
                "general news interest. Set relevance_score below 0.3 for human-interest, "
                "stock moves, and non-tech fluff."
            ),
            (
                "why_it_matters_to_wdts must explain why WDTS readers should care. "
                "Set null when there is no WDTS relevance."
            ),
            "Populate signal_type for every story with clear WDTS business impact.",
            (
                "short_summary must be a single headline-style sentence (about 20 words max) "
                "that states the core news."
            ),
            (
                "summary must be one or two sentences that add context beyond short_summary. "
                "Do not repeat short_summary verbatim."
            ),
            (
                "When multiple briefing_section values could apply, choose the most specific "
                "section for the WDTS daily news dashboard."
            ),
        ],
        "required_schema": {
            "summary": "string — 1-2 contextual sentences; must not duplicate short_summary",
            "short_summary": "string — single headline sentence; must not duplicate summary",
            "why_it_matters": "string",
            "key_points": ["string"],
            "entities": [{"name": "string", "type": "string"}],
            "topics": ["string"],
            "sentiment": "positive|neutral|negative|mixed|unknown",
            "relevance_score": "number from 0 to 1",
            "urgency_score": "number from 0 to 1",
            "importance_tier": "critical|important|monitor|low",
            "suggested_action": "string|null",
            "affected_business_area": "string|null",
            "confidence_score": "number from 0 to 1",
            "briefing_section": (
                "AI, ML & Computer Vision|Smart Tables & Casino Tech|"
                "Semiconductors & Components|Automation & Operations Tech|"
                "Competitors & Industry Watch|Regulation & Compliance|null"
            ),
            "category": (
                "AI/ML|Computer Vision|Smart Tables|Semiconductors|Automation|Casino Tech|"
                "Competitor|Customer|Supplier|Regulation|Compliance|Operations|null"
            ),
            "country_or_region": "string|null",
            "urgency": "FYI|Monitor|Discuss|Immediate|null",
            "suggested_owner": (
                "Sales|Product|Engineering|Operations|Finance|Legal|Executive Team|null"
            ),
            "action_bucket": "No action|Monitor|Discuss with team|Immediate attention|null",
            "why_it_matters_to_wdts": "string|null",
            "signal_type": (
                "sales_opportunity|competitive_threat|product_roadmap_implication|"
                "customer_adoption_signal|regulatory_development|manufacturing_component_risk|"
                "compliance_opportunity|strategic_market_signal|ai_product_signal|"
                "technology_adoption_signal|null"
            ),
        },
        "event": {
            "event_id": str(event.id),
            "canonical_title": event.canonical_title,
            "canonical_url": event.canonical_url,
            "category": event.category,
            "region": event.region,
            "published_at": event.published_at.isoformat() if event.published_at else None,
            "first_seen_at": event.first_seen_at.isoformat() if event.first_seen_at else None,
            "last_seen_at": event.last_seen_at.isoformat() if event.last_seen_at else None,
            "article_count": event.article_count,
            "source_count": event.source_count,
            "confidence_score": float(event.confidence_score),
            "primary_article_id": (
                str(event.primary_article_id) if event.primary_article_id else None
            ),
        },
        "articles": context.articles,
    }
    return json.dumps(payload, sort_keys=True, indent=2)
