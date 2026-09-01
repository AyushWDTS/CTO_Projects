import argparse
import json
from collections import Counter
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.data.briefing_coverage import BRIEFING_COVERAGE_MATRIX
from app.data.briefing_sections import (
    CONTENT_SECTION_ORDER,
    BriefingSection,
    AI_ML_CV_KEYWORDS,
    AUTOMATION_KEYWORDS,
    COMPETITOR_KEYWORDS,
    REGULATION_KEYWORDS,
    SEMICONDUCTOR_KEYWORDS,
    SMART_TABLE_KEYWORDS,
    TOP_5_LIMIT,
    _contains,
    _mapping_text,
)
from app.db.session import SessionLocal
from app.models.digest import Digest, DigestItem
from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
TARGET_SECTIONS = {
    BriefingSection.AI_ML_CV.value,
    BriefingSection.SMART_TABLES.value,
    BriefingSection.SEMICONDUCTORS.value,
    BriefingSection.AUTOMATION.value,
    BriefingSection.COMPETITORS.value,
    BriefingSection.REGULATION.value,
}

KEYWORD_GROUPS = {
    BriefingSection.AI_ML_CV.value: AI_ML_CV_KEYWORDS,
    BriefingSection.SMART_TABLES.value: SMART_TABLE_KEYWORDS,
    BriefingSection.SEMICONDUCTORS.value: SEMICONDUCTOR_KEYWORDS,
    BriefingSection.AUTOMATION.value: AUTOMATION_KEYWORDS,
    BriefingSection.COMPETITORS.value: COMPETITOR_KEYWORDS,
    BriefingSection.REGULATION.value: REGULATION_KEYWORDS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose COO briefing section population.")
    parser.add_argument("--digest-id", type=UUID, default=None)
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    return parser.parse_args()


def _load_digest(db, *, digest_id: UUID | None, digest_date: date | None) -> Digest | None:
    if digest_id is not None:
        return db.scalar(
            select(Digest)
            .where(Digest.id == digest_id)
            .options(joinedload(Digest.items))
        )
    query = select(Digest).options(joinedload(Digest.items)).order_by(Digest.created_at.desc())
    if digest_date is not None:
        query = query.where(Digest.digest_date == digest_date)
    return db.scalar(query.limit(1))


def _section_counts(items: list[DigestItem]) -> dict[str, int]:
    counts = {section: 0 for section in CONTENT_SECTION_ORDER}
    for item in items:
        section = str(_briefing_metadata(item).get("briefing_section") or "")
        if section in counts:
            counts[section] += 1
    return counts


def _mapping_source_breakdown(items: list[DigestItem]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        source = str(_briefing_metadata(item).get("mapping_source") or "unknown")
        counter[source] += 1
    return dict(counter)


def _watchlist_diagnostics(items: list[DigestItem]) -> dict[str, object]:
    competitor_signals = 0
    supplier_signals = 0
    for item in items:
        metadata = _briefing_metadata(item)
        if metadata.get("is_competitor_signal") or metadata.get("signal_type") == "competitive_threat":
            competitor_signals += 1
        if metadata.get("briefing_category") == "Supplier":
            supplier_signals += 1
    return {
        "watchlist_items": sum(
            1
            for item in items
            if _briefing_metadata(item).get("briefing_section") == BriefingSection.COMPETITORS.value
        ),
        "competitor_signals": competitor_signals,
        "supplier_signals": supplier_signals,
    }


def _top_five_overlap(items: list[DigestItem]) -> dict[str, object]:
    sorted_items = sorted(items, key=lambda value: value.rank)
    top_ids = {item.id for item in sorted_items[:TOP_5_LIMIT]}
    overlap = []
    for item in sorted_items[:TOP_5_LIMIT]:
        section = str(_briefing_metadata(item).get("briefing_section") or "")
        if section in TARGET_SECTIONS:
            overlap.append(
                {
                    "rank": item.rank,
                    "headline": item.headline,
                    "briefing_section": section,
                }
            )
    return {
        "top_five_count": min(len(sorted_items), TOP_5_LIMIT),
        "target_section_items_in_top_five": overlap,
        "top_five_item_ids": [str(item_id) for item_id in top_ids],
    }


def _keyword_misses(db, digest: Digest) -> dict[str, list[dict[str, str]]]:
    misses: dict[str, list[dict[str, str]]] = {section: [] for section in TARGET_SECTIONS}
    for item in digest.items:
        metadata = _briefing_metadata(item)
        mapped_section = str(metadata.get("briefing_section") or "")
        if mapped_section in TARGET_SECTIONS:
            continue
        event = db.get(NewsEvent, item.event_id)
        analysis = (
            db.get(EventAIAnalysis, item.event_ai_analysis_id)
            if item.event_ai_analysis_id is not None
            else None
        )
        if event is None or analysis is None:
            continue
        text = _mapping_text(event, analysis)
        for section, keywords in KEYWORD_GROUPS.items():
            if _contains(text, keywords):
                misses[section].append(
                    {
                        "rank": str(item.rank),
                        "headline": item.headline or "",
                        "mapped_section": mapped_section or "unassigned",
                        "mapping_source": str(metadata.get("mapping_source") or ""),
                    }
                )
    return misses


def _briefing_metadata(item: DigestItem) -> dict:
    metadata = item.item_metadata or {}
    nested = metadata.get("briefing") or metadata.get("coo_briefing")
    if not isinstance(nested, dict):
        nested = {}
    return {
        **nested,
        "briefing_section": metadata.get("briefing_section")
        or metadata.get("coo_section")
        or nested.get("briefing_section"),
        "briefing_category": metadata.get("briefing_category")
        or metadata.get("coo_category")
        or nested.get("briefing_category")
        or nested.get("category"),
    }


def _window_event_yield(db, digest: Digest) -> dict[str, int]:
    rows = db.scalars(
        select(NewsEvent)
        .where(
            NewsEvent.published_at >= digest.window_start,
            NewsEvent.published_at < digest.window_end,
        )
        .options(joinedload(NewsEvent.primary_source))
    ).all()
    by_category: Counter[str] = Counter()
    by_source_type: Counter[str] = Counter()
    for event in rows:
        category = (event.category or (event.primary_source.category if event.primary_source else "") or "unknown")
        by_category[str(category).lower()] += 1
        if event.primary_source is not None:
            by_source_type[str(event.primary_source.source_type)] += 1
    return {
        "events_in_window": len(rows),
        "by_category": dict(by_category),
        "by_source_type": dict(by_source_type),
    }


def _successful_analyses_in_window(db, digest: Digest) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(EventAIAnalysis)
            .join(NewsEvent, EventAIAnalysis.event_id == NewsEvent.id)
            .where(
                NewsEvent.published_at >= digest.window_start,
                NewsEvent.published_at < digest.window_end,
                EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value,
            )
        )
        or 0
    )


def build_report(db, digest: Digest) -> dict:
    items = list(digest.items or [])
    section_counts = _section_counts(items)
    return {
        "digest_id": str(digest.id),
        "digest_date": digest.digest_date.isoformat(),
        "window_start": digest.window_start.isoformat(),
        "window_end": digest.window_end.isoformat(),
        "total_items": len(items),
        "section_counts": section_counts,
        "target_section_counts": {section: section_counts.get(section, 0) for section in TARGET_SECTIONS},
        "mapping_source_breakdown": _mapping_source_breakdown(items),
        "top_five_overlap": _top_five_overlap(items),
        "keyword_misses": _keyword_misses(db, digest),
        "watchlist_diagnostics": _watchlist_diagnostics(items),
        "window_event_yield": _window_event_yield(db, digest),
        "successful_analyses_in_window": _successful_analyses_in_window(db, digest),
        "coverage_status": {
            section: BRIEFING_COVERAGE_MATRIX.get(section, {}).get("status")
            for section in TARGET_SECTIONS
        },
    }


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        digest = _load_digest(db, digest_id=args.digest_id, digest_date=args.digest_date)
        if digest is None:
            print(json.dumps({"error": "digest_not_found"}, indent=2))
            return
        print(json.dumps(build_report(db, digest), indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
