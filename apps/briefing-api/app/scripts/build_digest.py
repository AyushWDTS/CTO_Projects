import argparse
import json
from datetime import date, datetime

from app.db.session import SessionLocal
from app.schemas.digest import DigestDetailRead
from app.services.digest_service import (
    DEFAULT_DIGEST_LIMIT,
    build_digest,
    normalize_digest_build_limit,
    preview_digest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Phase 6 digest.")
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    parser.add_argument("--window-start", type=datetime.fromisoformat, default=None)
    parser.add_argument("--window-end", type=datetime.fromisoformat, default=None)
    parser.add_argument("--limit", type=int, default=DEFAULT_DIGEST_LIMIT)
    parser.add_argument("--category", default=None)
    parser.add_argument("--region", default=None)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--include-low", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    limit = normalize_digest_build_limit(args.limit)

    db = SessionLocal()
    try:
        if args.preview:
            result = preview_digest(
                db,
                digest_date=args.digest_date,
                window_start=args.window_start,
                window_end=args.window_end,
                limit=limit,
                category=args.category,
                region=args.region,
                min_score=args.min_score,
                include_low=args.include_low,
            )
            payload = result.model_dump(mode="json")
        else:
            result = build_digest(
                db,
                digest_date=args.digest_date,
                window_start=args.window_start,
                window_end=args.window_end,
                limit=limit,
                category=args.category,
                region=args.region,
                min_score=args.min_score,
                include_low=args.include_low,
                refresh=args.refresh,
            )
            payload = DigestDetailRead.model_validate(result).model_dump(mode="json")
    finally:
        db.close()

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
