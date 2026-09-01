"""Validate WDTS relevance gate on analyzed events in a digest window."""

import argparse
import json
from collections import Counter
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.models.event import EventStatus, NewsEvent
from app.models.event_analysis import EventAIAnalysis, EventAIAnalysisStatus
from app.scripts.source_yield_report import _load_digest
from app.services.wdts_relevance_service import assess_wdts_relevance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate WDTS relevance gate on digest window events.")
    parser.add_argument("--digest-id", type=UUID, default=None)
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    parser.add_argument("--limit", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        digest = _load_digest(db, digest_id=args.digest_id, digest_date=args.digest_date)
        if digest is None:
            print(json.dumps({"error": "digest_not_found"}, indent=2))
            return

        timestamp_expr = func.coalesce(
            NewsEvent.published_at,
            NewsEvent.first_seen_at,
            NewsEvent.created_at,
        )
        rows = db.execute(
            select(NewsEvent, EventAIAnalysis)
            .join(EventAIAnalysis, EventAIAnalysis.event_id == NewsEvent.id)
            .options(joinedload(NewsEvent.primary_source))
            .where(NewsEvent.status == EventStatus.ACTIVE)
            .where(EventAIAnalysis.status == EventAIAnalysisStatus.SUCCESS.value)
            .where(timestamp_expr >= digest.window_start)
            .where(timestamp_expr < digest.window_end)
            .order_by(timestamp_expr.desc())
            .limit(args.limit)
        ).all()

        eligible = []
        rejected = []
        borderline_rejected = []
        for event, analysis in rows:
            verdict = assess_wdts_relevance(event, analysis)
            entry = {
                "headline": analysis.short_summary or event.canonical_title,
                "source": event.primary_source.name if event.primary_source else None,
                "wdts_relevance_score": round(verdict.wdts_relevance_score, 4),
                "ai_relevance_score": (
                    float(analysis.relevance_score) if analysis.relevance_score is not None else None
                ),
                "reject_reason": verdict.reject_reason,
                "domain_hits": verdict.domain_hits[:6],
            }
            if verdict.is_eligible:
                eligible.append(entry)
            else:
                rejected.append(entry)
                if 0.40 <= verdict.wdts_relevance_score <= 0.50:
                    borderline_rejected.append(entry)

        payload = {
            "digest_id": str(digest.id),
            "digest_date": digest.digest_date.isoformat(),
            "events_evaluated": len(rows),
            "gate_eligible": len(eligible),
            "gate_rejected": len(rejected),
            "reject_by_reason": dict(Counter(item["reject_reason"] for item in rejected)),
            "borderline_rejected_0_40_to_0_50": borderline_rejected,
            "eligible_examples": eligible,
        }
        print(json.dumps(payload, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
