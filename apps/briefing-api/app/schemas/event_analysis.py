from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.event_analysis import AnalysisSentiment, EventAIAnalysisStatus, ImportanceTier

ALLOWED_BRIEFING_SECTIONS = {
    "AI, ML & Computer Vision",
    "Smart Tables & Casino Tech",
    "Semiconductors & Components",
    "Automation & Operations Tech",
    "Competitors & Industry Watch",
    "Regulation & Compliance",
}
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
ALLOWED_URGENCIES = {"FYI", "Monitor", "Discuss", "Immediate"}
ALLOWED_OWNERS = {
    "Sales",
    "Product",
    "Engineering",
    "Operations",
    "Finance",
    "Legal",
    "Executive Team",
}
ALLOWED_ACTION_BUCKETS = {"No action", "Monitor", "Discuss with team", "Immediate attention"}


def clamp_score(value: float | int | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


class AIEntity(BaseModel):
    name: str
    type: str

    @field_validator("name", "type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Entity name and type must be non-empty strings")
        return stripped


class EventAIModelOutput(BaseModel):
    summary: str
    short_summary: str
    why_it_matters: str
    key_points: list[str]
    entities: list[AIEntity] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    sentiment: AnalysisSentiment = AnalysisSentiment.UNKNOWN
    relevance_score: float | None = None
    urgency_score: float | None = None
    importance_tier: ImportanceTier | None = None
    suggested_action: str | None = None
    affected_business_area: str | None = None
    confidence_score: float | None = None
    briefing_section: str | None = None
    category: str | None = None
    country_or_region: str | None = None
    urgency: str | None = None
    suggested_owner: str | None = None
    action_bucket: str | None = None
    why_it_matters_to_wdts: str | None = None
    signal_type: str | None = None

    @field_validator("sentiment", mode="before")
    @classmethod
    def coerce_unknown_sentiment(cls, value: Any) -> Any:
        if isinstance(value, str) and value not in {item.value for item in AnalysisSentiment}:
            return AnalysisSentiment.UNKNOWN
        return value

    @field_validator("summary", "short_summary", "why_it_matters")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Required text fields must not be empty")
        return stripped

    @field_validator("key_points", "topics")
    @classmethod
    def validate_string_list(cls, value: list[Any]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Value must be a list")
        sanitized = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("List items must be strings")
            stripped = item.strip()
            if stripped:
                sanitized.append(stripped)
        return sanitized

    @field_validator("suggested_action", "affected_business_area", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Optional text fields must be strings or null")
        stripped = value.strip()
        return stripped or None

    @field_validator(
        "briefing_section",
        "category",
        "country_or_region",
        "urgency",
        "suggested_owner",
        "action_bucket",
        "why_it_matters_to_wdts",
        "signal_type",
        mode="before",
    )
    @classmethod
    def strip_optional_briefing_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Briefing fields must be strings or null")
        stripped = value.strip()
        return stripped or None

    @field_validator("briefing_section")
    @classmethod
    def validate_briefing_section(cls, value: str | None) -> str | None:
        return value if value in ALLOWED_BRIEFING_SECTIONS else None

    @field_validator("category")
    @classmethod
    def validate_briefing_category(cls, value: str | None) -> str | None:
        return value if value in ALLOWED_BRIEFING_CATEGORIES else None

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, value: str | None) -> str | None:
        return value if value in ALLOWED_URGENCIES else None

    @field_validator("suggested_owner")
    @classmethod
    def validate_owner(cls, value: str | None) -> str | None:
        return value if value in ALLOWED_OWNERS else None

    @field_validator("action_bucket")
    @classmethod
    def validate_action_bucket(cls, value: str | None) -> str | None:
        return value if value in ALLOWED_ACTION_BUCKETS else None

    @field_validator("relevance_score", "urgency_score", "confidence_score", mode="before")
    @classmethod
    def parse_scores(cls, value: Any) -> float | None:
        if value is None:
            return None
        if not isinstance(value, int | float):
            raise ValueError("Scores must be numeric")
        return clamp_score(value)

    @model_validator(mode="after")
    def derive_importance_tier(self) -> "EventAIModelOutput":
        if self.importance_tier is None:
            relevance = self.relevance_score or 0
            urgency = self.urgency_score or 0
            if relevance >= 0.85 and urgency >= 0.75:
                self.importance_tier = ImportanceTier.CRITICAL
            elif relevance >= 0.65:
                self.importance_tier = ImportanceTier.IMPORTANT
            elif relevance >= 0.35:
                self.importance_tier = ImportanceTier.MONITOR
            else:
                self.importance_tier = ImportanceTier.LOW
        return self


class EventAIAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    summary: str | None = None
    short_summary: str | None = None
    why_it_matters: str | None = None
    key_points: list | None = None
    entities: list | None = None
    topics: list | None = None
    sentiment: str | None = None
    relevance_score: Decimal | None = None
    urgency_score: Decimal | None = None
    importance_tier: str | None = None
    suggested_action: str | None = None
    affected_business_area: str | None = None
    confidence_score: Decimal | None = None
    model_name: str | None = None
    prompt_version: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: Decimal | None = None
    status: EventAIAnalysisStatus
    error_message: str | None = None
    content_signature: str | None = None
    source_article_ids: list | None = None
    source_urls: list | None = None
    primary_article_id: UUID | None = None
    context_article_count: int
    metadata: dict | None = Field(
        default=None,
        validation_alias="analysis_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class EventAIAnalysisList(BaseModel):
    items: list[EventAIAnalysisRead]
    total: int
    limit: int
    offset: int


class EventAIAnalysisBatchResult(BaseModel):
    total_events: int
    analyzed: int = 0
    skipped: int = 0
    failed: int = 0
    results: list[EventAIAnalysisRead] = Field(default_factory=list)
