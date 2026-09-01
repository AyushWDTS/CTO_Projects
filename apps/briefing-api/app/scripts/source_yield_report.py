import argparse
import json
from collections import defaultdict
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.data.briefing_sections import BriefingSection, TOP_5_LIMIT
from app.db.session import SessionLocal
from app.models.article import Article
from app.models.digest import Digest, DigestItem
from app.models.event import NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.models.ingestion import RawDocument
from app.models.source import Source

DEFAULT_EXAMPLES_PER_REASON = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Per-source ingest, analyze, select, and reject yield.")
    parser.add_argument("--digest-id", type=UUID, default=None)
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    parser.add_argument(
        "--examples-per-reason",
        type=int,
        default=DEFAULT_EXAMPLES_PER_REASON,
        help="Max rejected examples to show per reject_reason.",
    )
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


def _load_source_names(db, source_ids: set[str]) -> dict[str, str]:
    if not source_ids:
        return {}
    uuid_ids = []
    for source_id in source_ids:
        try:
            uuid_ids.append(UUID(source_id))
        except ValueError:
            continue
    if not uuid_ids:
        return {}
    rows = db.execute(select(Source.id, Source.name).where(Source.id.in_(uuid_ids))).all()
    return {str(source_id): name for source_id, name in rows}


def _ingested_by_source(db, digest: Digest) -> dict[str, int]:
    rows = db.execute(
        select(Source.id, func.count(Article.id))
        .join(RawDocument, RawDocument.source_id == Source.id)
        .join(Article, Article.raw_document_id == RawDocument.id)
        .where(RawDocument.fetched_at >= digest.window_start)
        .where(RawDocument.fetched_at < digest.window_end)
        .group_by(Source.id)
    ).all()
    return {str(source_id): int(count) for source_id, count in rows if count}


def _analyzed_by_source(db, digest: Digest) -> dict[str, int]:
    timestamp_expr = func.coalesce(
        NewsEvent.published_at,
        NewsEvent.first_seen_at,
        NewsEvent.created_at,
    )
    rows = db.execute(
        select(NewsEvent.primary_source_id, func.count(EventAIAnalysis.id))
        .join(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
        .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value)
        .where(timestamp_expr >= digest.window_start)
        .where(timestamp_expr < digest.window_end)
        .where(NewsEvent.primary_source_id.is_not(None))
        .group_by(NewsEvent.primary_source_id)
    ).all()
    return {str(source_id): int(count) for source_id, count in rows}


def _selected_by_source(items: list[DigestItem], db) -> dict[str, dict[str, int]]:
    metrics: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in items:
        event = db.get(NewsEvent, item.event_id)
        if event is None or event.primary_source_id is None:
            continue
        source_id = str(event.primary_source_id)
        metrics[source_id]["selected"] += 1
        metadata = _briefing_metadata(item)
        section = str(metadata.get("briefing_section") or "")
        if section == BriefingSection.SMART_TABLES.value:
            metrics[source_id]["smart_table"] += 1
        if section == BriefingSection.COMPETITORS.value:
            metrics[source_id]["watchlist"] += 1
        if item.rank <= TOP_5_LIMIT or (item.item_metadata or {}).get("top_five_eligible"):
            metrics[source_id]["top_five"] += 1
        if metadata.get("signal_type") == "sales_opportunity" or metadata.get(
            "sales_opportunity_signal"
        ):
            metrics[source_id]["sales"] += 1
        if metadata.get("signal_type") == "competitive_threat" or metadata.get(
            "is_competitor_signal"
        ):
            metrics[source_id]["competitor"] += 1
    return {key: dict(value) for key, value in metrics.items()}


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
    }


def _rejects_by_source(digest: Digest) -> dict[str, int]:
    audit = (digest.digest_metadata or {}).get("selection_audit") or {}
    summary = audit.get("summary") or {}
    return {str(key): int(value) for key, value in (summary.get("reject_by_source") or {}).items()}


def _audit_entries(digest: Digest) -> list[dict]:
    audit = (digest.digest_metadata or {}).get("selection_audit") or {}
    entries = audit.get("entries")
    return entries if isinstance(entries, list) else []


def _enrich_ai_relevance(db, entries: list[dict]) -> None:
    event_ids: list[UUID] = []
    for entry in entries:
        if entry.get("ai_relevance_score") is not None:
            continue
        try:
            event_ids.append(UUID(str(entry.get("event_id"))))
        except (TypeError, ValueError):
            continue
    if not event_ids:
        return
    rows = db.execute(
        select(EventAIAnalysis.event_id, EventAIAnalysis.relevance_score)
        .where(EventAIAnalysis.event_id.in_(event_ids))
        .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value)
    ).all()
    scores = {
        str(event_id): float(relevance_score) if relevance_score is not None else None
        for event_id, relevance_score in rows
    }
    for entry in entries:
        if entry.get("ai_relevance_score") is not None:
            continue
        event_id = str(entry.get("event_id") or "")
        if event_id in scores and scores[event_id] is not None:
            entry["ai_relevance_score"] = round(scores[event_id], 4)


def _rejected_examples_by_reason(
    db,
    digest: Digest,
    *,
    limit_per_reason: int,
) -> dict[str, list[dict]]:
    entries = [
        entry
        for entry in _audit_entries(digest)
        if entry.get("stage") == "relevance_gate" and entry.get("decision") == "rejected"
    ]
    _enrich_ai_relevance(db, entries)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in sorted(
        entries,
        key=lambda value: float(value.get("wdts_relevance_score") or 0),
        reverse=True,
    ):
        reason = str(entry.get("reason") or "unknown")
        if len(grouped[reason]) >= limit_per_reason:
            continue
        grouped[reason].append(
            {
                "headline": entry.get("headline"),
                "source_name": entry.get("source_name"),
                "source_id": entry.get("source_id"),
                "reject_reason": reason,
                "wdts_relevance_score": entry.get("wdts_relevance_score"),
                "ai_relevance_score": entry.get("ai_relevance_score"),
                "domain_hits": entry.get("domain_hits") or [],
                "importance_tier": entry.get("importance_tier"),
            }
        )
    return dict(grouped)


def _gate_recommendation(audit_summary: dict, rejected_examples: dict[str, list[dict]]) -> dict:
    reject_by_reason = audit_summary.get("reject_by_reason") or {}
    gate_rejected = int(audit_summary.get("gate_rejected") or 0)
    gate_eligible = int(audit_summary.get("gate_eligible") or 0)
    total = gate_rejected + gate_eligible
    reject_rate = round(gate_rejected / total, 3) if total else 0.0

    borderline_gaming = []
    for reason, examples in rejected_examples.items():
        for example in examples:
            hits = example.get("domain_hits") or []
            wdts = float(example.get("wdts_relevance_score") or 0)
            headline = str(example.get("headline") or "").lower()
            if reason != "low_ai_relevance":
                continue
            if hits or any(token in headline for token in ("casino", "gaming", "table game")):
                borderline_gaming.append(example)

    if borderline_gaming:
        tuning = (
            "Gate may be slightly strict for gaming-domain stories with low AI relevance scores. "
            "Recent tuning lowers the WDTS threshold when domain/competitor/sales signals are present."
        )
    elif int(reject_by_reason.get("low_ai_relevance", 0)) >= gate_rejected * 0.6:
        tuning = (
            "Most rejections are low_ai_relevance from non-gaming fintech/general news feeds. "
            "This looks like correct noise filtering rather than over-blocking WDTS content."
        )
    else:
        tuning = "Rejection mix looks balanced; no immediate threshold change recommended."

    return {
        "gate_reject_rate": reject_rate,
        "borderline_gaming_rejects": len(borderline_gaming),
        "recommendation": tuning,
    }


def _is_active_source_row(row: dict) -> bool:
    return any(
        int(row.get(key) or 0) > 0
        for key in (
            "articles_ingested",
            "events_analyzed",
            "stories_selected",
            "gate_rejected",
        )
    )


def build_report(db, digest: Digest, *, examples_per_reason: int = DEFAULT_EXAMPLES_PER_REASON) -> dict:
    ingested = _ingested_by_source(db, digest)
    analyzed = _analyzed_by_source(db, digest)
    selected = _selected_by_source(list(digest.items or []), db)
    rejects = _rejects_by_source(digest)

    active_ids = {
        source_id
        for source_id, count in ingested.items()
        if count > 0
    }
    active_ids |= {source_id for source_id, count in analyzed.items() if count > 0}
    active_ids |= set(selected)
    active_ids |= {source_id for source_id, count in rejects.items() if count > 0}

    source_names = _load_source_names(db, active_ids)
    rows = []
    for source_id in sorted(active_ids, key=lambda value: source_names.get(value, value)):
        selection = selected.get(source_id, {})
        row = {
            "source_id": source_id,
            "source_name": source_names.get(source_id, "Unresolved source"),
            "articles_ingested": ingested.get(source_id, 0),
            "events_analyzed": analyzed.get(source_id, 0),
            "stories_selected": selection.get("selected", 0),
            "top_five_appearances": selection.get("top_five", 0),
            "competitor_appearances": selection.get("competitor", 0),
            "sales_appearances": selection.get("sales", 0),
            "smart_table_appearances": selection.get("smart_table", 0),
            "watchlist_appearances": selection.get("watchlist", 0),
            "gate_rejected": rejects.get(source_id, 0),
        }
        if _is_active_source_row(row):
            rows.append(row)

    rows.sort(
        key=lambda value: (
            -(value["stories_selected"] + value["gate_rejected"]),
            -value["events_analyzed"],
            -value["articles_ingested"],
            value["source_name"],
        )
    )

    audit_summary = ((digest.digest_metadata or {}).get("selection_audit") or {}).get("summary") or {}
    rejected_examples = _rejected_examples_by_reason(
        db,
        digest,
        limit_per_reason=examples_per_reason,
    )
    return {
        "digest_id": str(digest.id),
        "digest_date": digest.digest_date.isoformat(),
        "window_start": digest.window_start.isoformat(),
        "window_end": digest.window_end.isoformat(),
        "selection_audit_summary": audit_summary,
        "gate_recommendation": _gate_recommendation(audit_summary, rejected_examples),
        "rejected_examples_by_reason": rejected_examples,
        "active_source_count": len(rows),
        "sources": rows,
    }


def _print_table(report: dict) -> None:
    print(f"Digest {report['digest_date']} | active sources: {report['active_source_count']}")
    rec = report.get("gate_recommendation") or {}
    if rec.get("recommendation"):
        print(f"Gate recommendation: {rec['recommendation']}")
    print()
    headers = ["source", "ingested", "analyzed", "selected", "rejected", "top5"]
    print(" | ".join(headers))
    print("-" * 80)
    for row in report["sources"]:
        print(
            " | ".join(
                [
                    str(row["source_name"])[:28],
                    str(row["articles_ingested"]),
                    str(row["events_analyzed"]),
                    str(row["stories_selected"]),
                    str(row["gate_rejected"]),
                    str(row["top_five_appearances"]),
                ]
            )
        )
    examples = report.get("rejected_examples_by_reason") or {}
    if examples:
        print()
        print("Rejected examples by reason:")
        for reason, items in sorted(examples.items()):
            print(f"  [{reason}]")
            for item in items:
                wdts = item.get("wdts_relevance_score")
                ai = item.get("ai_relevance_score")
                source = item.get("source_name") or "unknown"
                print(
                    f"    - ({source}) wdts={wdts} ai={ai} | "
                    f"{str(item.get('headline') or '')[:90]}"
                )


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        digest = _load_digest(db, digest_id=args.digest_id, digest_date=args.digest_date)
        if digest is None:
            print(json.dumps({"error": "digest_not_found"}, indent=2))
            return
        report = build_report(db, digest, examples_per_reason=args.examples_per_reason)
        _print_table(report)
        print()
        print(json.dumps(report, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
