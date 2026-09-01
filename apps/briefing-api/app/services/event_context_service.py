import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.models.event import EventArticle, NewsEvent

PER_ARTICLE_TEXT_BUDGET = 4000


class EventContextNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class EventContext:
    event: NewsEvent
    articles: list[dict]
    source_article_ids: list[str]
    source_urls: list[str]
    primary_article_id: UUID | None
    content_signature: str
    context_article_count: int
    metadata: dict


def build_event_context(
    db: Session,
    event_id: UUID,
    *,
    settings: Settings | None = None,
) -> EventContext:
    settings = settings or get_settings()
    event = db.get(NewsEvent, event_id)
    if event is None:
        raise EventContextNotFoundError("News event not found.")

    links = list(
        db.scalars(
            select(EventArticle)
            .options(
                joinedload(EventArticle.article),
                joinedload(EventArticle.source),
            )
            .where(EventArticle.event_id == event_id)
        )
    )
    selected_links = _select_context_links(links)
    articles: list[dict] = []
    used_chars = 0

    for link in selected_links:
        article = link.article
        source = link.source
        clean_text = _truncate_text(
            article.clean_text or article.excerpt or "",
            PER_ARTICLE_TEXT_BUDGET,
        )
        article_payload = {
            "article_id": str(article.id),
            "source_id": str(article.source_id),
            "source_name": source.name if source else None,
            "source_url": source.url if source else None,
            "source_reliability_score": float(source.reliability_score) if source else None,
            "source_priority": source.priority if source else None,
            "title": article.title,
            "canonical_url": article.canonical_url,
            "source_url_used": article.source_url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "excerpt": article.excerpt,
            "clean_text": clean_text,
            "content_hash": article.content_hash,
            "is_primary": link.is_primary,
        }
        projected = len(json.dumps(article_payload, default=str))
        if articles and used_chars + projected > settings.AI_MAX_INPUT_CHARS_PER_EVENT:
            break
        used_chars += projected
        articles.append(article_payload)

    article_ids = [article["article_id"] for article in articles]
    source_urls = sorted(
        {
            str(article.get("source_url_used"))
            for article in articles
            if article.get("source_url_used")
        }
    )
    signature_payload = {
        "event_id": str(event.id),
        "event_updated_at": event.updated_at.isoformat() if event.updated_at else None,
        "primary_article_id": str(event.primary_article_id) if event.primary_article_id else None,
        "article_hashes": [
            [article["article_id"], article.get("content_hash"), article.get("published_at")]
            for article in articles
        ],
    }

    return EventContext(
        event=event,
        articles=articles,
        source_article_ids=article_ids,
        source_urls=source_urls,
        primary_article_id=event.primary_article_id,
        content_signature=hashlib.sha256(
            json.dumps(signature_payload, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        context_article_count=len(articles),
        metadata={
            "context_selection_reason": (
                "primary_article_then_reliability_priority_newest_until_char_budget"
            ),
            "available_article_count": len(links),
            "selected_article_count": len(articles),
            "max_input_chars": settings.AI_MAX_INPUT_CHARS_PER_EVENT,
            "used_chars_estimate": used_chars,
        },
    )


def _select_context_links(links: list[EventArticle]) -> list[EventArticle]:
    return sorted(links, key=_link_sort_key)


def _link_sort_key(link: EventArticle) -> tuple:
    article = link.article
    source = link.source
    reliability = float(source.reliability_score) if source else 0
    priority = source.priority if source else 5
    article_time = article.published_at or article.created_at or datetime.min.replace(tzinfo=UTC)
    return (
        not link.is_primary,
        -reliability,
        priority,
        -article_time.timestamp(),
        str(article.id),
    )


def _truncate_text(value: str, max_chars: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rsplit(" ", 1)[0]
