import argparse
import json
from uuid import UUID

from app.db.session import SessionLocal
from app.services.normalization_service import (
    DEFAULT_NORMALIZATION_LIMIT,
    MAX_NORMALIZATION_LIMIT,
    normalize_by_source,
    normalize_limit,
    normalize_pending_raw_documents,
    normalize_raw_document,
    reprocess_failed_normalizations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 3 content normalization.")
    parser.add_argument("--raw-document-id", type=UUID, default=None)
    parser.add_argument("--source-id", type=UUID, default=None)
    parser.add_argument("--reprocess-failed", action="store_true")
    parser.add_argument("--limit", type=int, default=DEFAULT_NORMALIZATION_LIMIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    limit = normalize_limit(min(args.limit, MAX_NORMALIZATION_LIMIT))

    db = SessionLocal()
    try:
        if args.raw_document_id is not None:
            result = normalize_raw_document(db, args.raw_document_id)
        elif args.source_id is not None:
            result = normalize_by_source(db, args.source_id, limit=limit)
        elif args.reprocess_failed:
            result = reprocess_failed_normalizations(db, limit=limit)
        else:
            result = normalize_pending_raw_documents(db, limit=limit)
    finally:
        db.close()

    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
