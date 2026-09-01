import argparse
import json
import sys
from datetime import UTC, datetime
from datetime import date as date_type

from app.db.session import SessionLocal
from app.schemas.orchestration import OrchestrationRunDetail
from app.services.orchestration_service import (
    OrchestrationInvalidRequestError,
    OrchestrationRunAlreadyActiveError,
    run_demo_pipeline,
)


def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


def _log(msg: str) -> None:
    print(f"[demo {_ts()}] {msg}", file=sys.stderr, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the demo pipeline: ingest new content and process only items "
            "fetched since the last successful orchestration run."
        )
    )
    parser.add_argument("--date", dest="digest_date", type=date_type.fromisoformat, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-ingestion", action="store_true")
    parser.add_argument("--continue-on-ai-failure", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--digest-limit", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _log("Opening DB session")
    db = SessionLocal()
    payload: dict = {}
    try:
        _log(f"Starting demo pipeline for date={args.digest_date or 'today'}")
        try:
            result = run_demo_pipeline(
                db,
                digest_date=args.digest_date,
                dry_run=args.dry_run or None,
                skip_ingestion=args.skip_ingestion,
                continue_on_ai_failure=args.continue_on_ai_failure,
                limit=args.limit,
                digest_limit=args.digest_limit,
                triggered_by="cli",
            )
            payload = OrchestrationRunDetail.model_validate(result).model_dump(mode="json")
            _log(f"Pipeline complete: status={payload.get('status')} digest_id={payload.get('digest_id')}")
        except (OrchestrationInvalidRequestError, OrchestrationRunAlreadyActiveError) as exc:
            _log(f"Pipeline rejected: {exc}")
            payload = {"status": "failed", "error_message": str(exc)}
    except KeyboardInterrupt:
        _log("Interrupted by user")
        payload = {"status": "cancelled", "error_message": "keyboard_interrupt"}
    except Exception as exc:
        _log(f"Unexpected error: {exc}")
        payload = {"status": "error", "error_message": str(exc)}
        raise
    finally:
        _log("Closing DB session")
        db.close()

    print(json.dumps(payload, indent=2), flush=True)
    _log("Script finished")
    sys.exit(0)


if __name__ == "__main__":
    main()
