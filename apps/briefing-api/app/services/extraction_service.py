import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.models.article import ArticleExtractionStatus
from app.models.ingestion import RawDocument
from app.models.source import FetchMethod

EXCERPT_LENGTH = 300


@dataclass(frozen=True)
class ExtractionResult:
    status: ArticleExtractionStatus
    title: str | None = None
    canonical_url: str | None = None
    source_url: str | None = None
    content_type: str | None = None
    clean_text: str | None = None
    excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    content_hash: str | None = None
    extraction_error: str | None = None
    metadata: dict = field(default_factory=dict)


def extract_raw_document(raw_document: RawDocument) -> ExtractionResult:
    source = raw_document.source

    if source.fetch_method == FetchMethod.RSS:
        return extract_rss_document(raw_document)

    if source.fetch_method == FetchMethod.STATIC_HTML:
        return extract_static_html_document(raw_document)

    return _skipped_result(raw_document, "unsupported_fetch_method")


def extract_rss_document(raw_document: RawDocument) -> ExtractionResult:
    if not raw_document.raw_content:
        return _failed_result(raw_document, "empty_raw_content", "rss")

    metadata = raw_document.document_metadata or {}
    clean_text = _clean_text_from_html(raw_document.raw_content)
    published_value = _first_present(metadata, "published", "published_at")
    published_at, date_error = _parse_datetime(published_value)
    canonical_url = raw_document.canonical_url or raw_document.url
    title = _normalize_whitespace(str(metadata.get("entry_title") or "")) or None

    extraction_metadata = {
        "extraction_path": "rss",
        "raw_document_metadata": metadata,
        "original_published": published_value,
    }
    if date_error:
        extraction_metadata["published_parse_error"] = date_error

    return _success_result(
        raw_document=raw_document,
        clean_text=clean_text,
        canonical_url=canonical_url,
        title=title,
        author=_string_or_none(metadata.get("author")),
        published_at=published_at,
        language=_language_from_metadata_or_html(metadata, None),
        metadata=extraction_metadata,
    )


def extract_static_html_document(raw_document: RawDocument) -> ExtractionResult:
    if not raw_document.raw_content:
        return _failed_result(raw_document, "empty_raw_content", "static_html")

    soup = BeautifulSoup(raw_document.raw_content, "lxml")
    metadata = raw_document.document_metadata or {}
    canonical_url = _canonical_url_from_html(soup) or raw_document.canonical_url or raw_document.url
    title = _title_from_html(soup)
    author = _author_from_html(soup)
    published_value = _published_value_from_html(soup)
    published_at, date_error = _parse_datetime(published_value)
    language = _language_from_metadata_or_html(metadata, soup)
    clean_text = _visible_text_from_html(soup)

    extraction_metadata = {
        "extraction_path": "static_html",
        "raw_document_metadata": metadata,
        "original_published": published_value,
    }
    if date_error:
        extraction_metadata["published_parse_error"] = date_error

    return _success_result(
        raw_document=raw_document,
        clean_text=clean_text,
        canonical_url=canonical_url,
        title=title,
        author=author,
        published_at=published_at,
        language=language,
        metadata=extraction_metadata,
    )


def _success_result(
    *,
    raw_document: RawDocument,
    clean_text: str,
    canonical_url: str | None,
    title: str | None,
    author: str | None,
    published_at: datetime | None,
    language: str | None,
    metadata: dict,
) -> ExtractionResult:
    normalized_text = _normalize_whitespace(clean_text)
    if not normalized_text:
        return _failed_result(
            raw_document,
            "empty_clean_text",
            metadata.get("extraction_path", "unknown"),
        )

    return ExtractionResult(
        status=ArticleExtractionStatus.SUCCESS,
        title=title[:500] if title else None,
        canonical_url=canonical_url,
        source_url=raw_document.url,
        content_type=raw_document.content_type,
        clean_text=normalized_text,
        excerpt=_excerpt(normalized_text),
        author=author[:255] if author else None,
        published_at=published_at,
        language=language[:20] if language else None,
        content_hash=_content_hash(normalized_text),
        metadata=metadata,
    )


def _failed_result(
    raw_document: RawDocument,
    error: str,
    extraction_path: str,
) -> ExtractionResult:
    return ExtractionResult(
        status=ArticleExtractionStatus.FAILED,
        source_url=raw_document.url,
        content_type=raw_document.content_type,
        extraction_error=error,
        metadata={
            "extraction_path": extraction_path,
            "raw_document_metadata": raw_document.document_metadata or {},
        },
    )


def _skipped_result(raw_document: RawDocument, error: str) -> ExtractionResult:
    return ExtractionResult(
        status=ArticleExtractionStatus.SKIPPED,
        source_url=raw_document.url,
        content_type=raw_document.content_type,
        extraction_error=error,
        metadata={
            "extraction_path": "unsupported",
            "source_fetch_method": raw_document.source.fetch_method.value,
            "raw_document_metadata": raw_document.document_metadata or {},
        },
    )


def _clean_text_from_html(value: str) -> str:
    soup = BeautifulSoup(value, "lxml")
    return _visible_text_from_html(soup)


def _visible_text_from_html(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    return _normalize_whitespace(soup.get_text(" "))


def _canonical_url_from_html(soup: BeautifulSoup) -> str | None:
    tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    if tag and tag.get("href"):
        return str(tag["href"]).strip()
    return _meta_content(soup, "og:url") or _meta_content(soup, "twitter:url")


def _title_from_html(soup: BeautifulSoup) -> str | None:
    for candidate in (
        _meta_content(soup, "og:title"),
        _meta_content(soup, "twitter:title"),
        soup.title.string if soup.title and soup.title.string else None,
        _first_tag_text(soup, "h1"),
    ):
        value = _string_or_none(candidate)
        if value:
            return value
    return None


def _author_from_html(soup: BeautifulSoup) -> str | None:
    for name in ("author", "article:author", "byline", "dc.creator"):
        value = _meta_content(soup, name)
        if value:
            return value
    return None


def _published_value_from_html(soup: BeautifulSoup) -> str | None:
    for name in (
        "article:published_time",
        "datePublished",
        "date",
        "pubdate",
        "publishdate",
        "dc.date",
    ):
        value = _meta_content(soup, name)
        if value:
            return value
    time_tag = soup.find("time")
    if time_tag:
        return _string_or_none(time_tag.get("datetime")) or _string_or_none(time_tag.get_text())
    return None


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    selectors = [
        {"property": name},
        {"name": name},
        {"itemprop": name},
    ]
    for selector in selectors:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return None


def _first_tag_text(soup: BeautifulSoup, tag_name: str) -> str | None:
    tag = soup.find(tag_name)
    if tag:
        return _string_or_none(tag.get_text(" "))
    return None


def _parse_datetime(value: str | None) -> tuple[datetime | None, str | None]:
    if not value:
        return None, None
    try:
        parsed = date_parser.parse(value)
    except (TypeError, ValueError, OverflowError) as exc:
        return None, str(exc)
    return parsed, None


def _language_from_metadata_or_html(metadata: dict, soup: BeautifulSoup | None) -> str | None:
    for key in ("language", "lang"):
        value = _string_or_none(metadata.get(key))
        if value:
            return value
    if soup and soup.html and soup.html.get("lang"):
        return str(soup.html["lang"]).strip()
    return None


def _first_present(metadata: dict, *keys: str) -> str | None:
    for key in keys:
        value = _string_or_none(metadata.get(key))
        if value:
            return value
    return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    normalized = _normalize_whitespace(str(value))
    return normalized or None


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _excerpt(clean_text: str) -> str:
    return clean_text[:EXCERPT_LENGTH]


def _content_hash(clean_text: str) -> str:
    return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
