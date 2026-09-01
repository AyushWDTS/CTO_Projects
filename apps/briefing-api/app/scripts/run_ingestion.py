import argparse
import json
from uuid import UUID

from app.db.session import SessionLocal
from app.services.ingestion_service import ingest_all_sources, ingest_source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 raw ingestion.")
    parser.add_argument("--source-id", type=UUID, default=None, help="Optional Source Registry ID.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        if args.source_id is not None:
            result = ingest_source(db, args.source_id)
        else:
            result = ingest_all_sources(db)
    finally:
        db.close()

    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
