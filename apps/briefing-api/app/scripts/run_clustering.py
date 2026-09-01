import argparse
import json
from uuid import UUID

from app.db.session import SessionLocal
from app.services.clustering_service import (
    DEFAULT_CLUSTERING_LIMIT,
    cluster_article,
    cluster_by_source,
    cluster_pending_articles,
    normalize_event_limit,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 duplicate detection and clustering.")
    parser.add_argument("--article-id", type=UUID, default=None)
    parser.add_argument("--source-id", type=UUID, default=None)
    parser.add_argument("--limit", type=int, default=DEFAULT_CLUSTERING_LIMIT)
    parser.add_argument("--reprocess", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    limit = normalize_event_limit(args.limit)

    db = SessionLocal()
    try:
        if args.article_id is not None:
            result = cluster_article(db, args.article_id, reprocess=args.reprocess)
        elif args.source_id is not None:
            result = cluster_by_source(
                db,
                args.source_id,
                limit=limit,
                reprocess=args.reprocess,
            )
        else:
            result = cluster_pending_articles(db, limit=limit, reprocess=args.reprocess)
    finally:
        db.close()

    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
