import argparse
import json
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.event_analysis import EventAIAnalysisRead
from app.services.event_analysis_service import (
    DEFAULT_EVENT_ANALYSIS_LIMIT,
    analyze_by_category,
    analyze_by_region,
    analyze_by_source,
    analyze_event,
    analyze_pending_events,
    normalize_analysis_limit,
    reprocess_failed_ai_analyses,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 5 event AI analysis.")
    parser.add_argument("--event-id", type=UUID, default=None)
    parser.add_argument("--source-id", type=UUID, default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--region", default=None)
    parser.add_argument("--limit", type=int, default=DEFAULT_EVENT_ANALYSIS_LIMIT)
    parser.add_argument("--failed-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    limit = normalize_analysis_limit(args.limit)

    db = SessionLocal()
    try:
        if args.event_id is not None:
            result = analyze_event(db, args.event_id, force=args.force)
        elif args.source_id is not None:
            result = analyze_by_source(db, args.source_id, limit=limit, force=args.force)
        elif args.category is not None:
            result = analyze_by_category(db, args.category, limit=limit, force=args.force)
        elif args.region is not None:
            result = analyze_by_region(db, args.region, limit=limit, force=args.force)
        elif args.failed_only:
            result = reprocess_failed_ai_analyses(db, limit=limit)
        else:
            result = analyze_pending_events(db, limit=limit)
    finally:
        db.close()

    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="json")
    else:
        payload = EventAIAnalysisRead.model_validate(result).model_dump(mode="json")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
