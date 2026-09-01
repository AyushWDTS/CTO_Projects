import re

from app.data.bedrock_analysis_schema import is_actionable_suggestion
from app.models.digest import DigestItem

SUMMARY_MAX_SENTENCES = 2
WHY_IT_MATTERS_MAX_SENTENCES = 2
SUGGESTED_ACTION_MAX_SENTENCES = 1


def normalize_text_for_compare(value: str | None) -> str:
    if not value:
        return ""
    normalized = " ".join(str(value).replace("\n", " ").split()).strip().lower()
    return re.sub(r"[^\w\s]", "", normalized)


def summaries_match(headline: str | None, summary: str | None) -> bool:
    headline_norm = normalize_text_for_compare(headline)
    summary_norm = normalize_text_for_compare(summary)
    if not headline_norm or not summary_norm:
        return False
    return headline_norm == summary_norm


def distinct_summary(
    headline: str | None,
    summary: str | None,
    *,
    fallback: str | None = None,
    max_sentences: int = SUMMARY_MAX_SENTENCES,
) -> str:
    if summaries_match(headline, summary):
        candidate = (fallback or "").strip()
    else:
        candidate = (summary or "").strip()
    if not candidate:
        return ""
    return limit_sentences(candidate, max_sentences)


def limit_sentences(value: str | None, max_sentences: int) -> str:
    if not value or max_sentences <= 0:
        return ""
    normalized = " ".join(str(value).replace("\n", " ").split()).strip()
    if not normalized:
        return ""
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    if not parts:
        return normalized
    if len(parts) <= max_sentences:
        return _join_sentences(parts)
    return _join_sentences(parts[:max_sentences])


def _summary_fallback_from_metadata(metadata: dict) -> str | None:
    key_points = metadata.get("key_points")
    if isinstance(key_points, list):
        for point in key_points:
            if isinstance(point, str) and point.strip():
                return point.strip()
    excerpt = metadata.get("article_excerpt")
    if isinstance(excerpt, str) and excerpt.strip():
        return excerpt.strip()
    return None


def resolve_suggested_action(
    suggested_action: str | None,
    action_bucket: str | None,
    *,
    max_sentences: int = SUGGESTED_ACTION_MAX_SENTENCES,
) -> str:
    for candidate in (suggested_action, action_bucket):
        if not candidate:
            continue
        text = limit_sentences(candidate, max_sentences)
        if is_actionable_suggestion(text):
            return text
    return ""


def dashboard_text_for_item(item: DigestItem, metadata: dict) -> dict[str, str]:
    why_source = metadata.get("why_it_matters_to_wdts") or item.why_it_matters or ""
    return {
        "summary": distinct_summary(
            item.headline,
            item.summary,
            fallback=_summary_fallback_from_metadata(metadata),
        ),
        "why_it_matters": limit_sentences(why_source, WHY_IT_MATTERS_MAX_SENTENCES),
        "suggested_action": resolve_suggested_action(
            item.suggested_action,
            metadata.get("action_bucket"),
        ),
    }


# Backward-compatible alias for callers still using the executive-era name.
executive_text_for_item = dashboard_text_for_item


def _join_sentences(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part.strip()).strip()
