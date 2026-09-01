import argparse
import json
import sys
from datetime import date, datetime

from app.db.session import SessionLocal
from app.schemas.orchestration import OrchestrationRunDetail
from app.services.orchestration_service import (
    OrchestrationInvalidRequestError,
    OrchestrationRunAlreadyActiveError,
    run_daily_pipeline,
    run_pipeline_for_window,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the WDTS daily news dashboard pipeline through digest build."
    )
    parser.add_argument("--date", dest="digest_date", type=date.fromisoformat, default=None)
    parser.add_argument("--window-start", type=datetime.fromisoformat, default=None)
    parser.add_argument("--window-end", type=datetime.fromisoformat, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-ingestion", action="store_true")
    parser.add_argument("--skip-normalization", action="store_true")
    parser.add_argument("--skip-clustering", action="store_true")
    parser.add_argument("--skip-ai", action="store_true")
    parser.add_argument("--continue-on-ai-failure", action="store_true")
    parser.add_argument("--refresh-digest", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--digest-limit", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        try:
            if args.window_start or args.window_end:
                result = run_pipeline_for_window(
                    db,
                    window_start=args.window_start,
                    window_end=args.window_end,
                    dry_run=args.dry_run or None,
                    skip_ingestion=args.skip_ingestion,
                    skip_normalization=args.skip_normalization,
                    skip_clustering=args.skip_clustering,
                    skip_ai=args.skip_ai,
                    continue_on_ai_failure=args.continue_on_ai_failure,
                    refresh_digest=args.refresh_digest,
                    limit=args.limit,
                    digest_limit=args.digest_limit,
                    triggered_by="cli",
                )
            else:
                result = run_daily_pipeline(
                    db,
                    digest_date=args.digest_date,
                    dry_run=args.dry_run or None,
                    skip_ingestion=args.skip_ingestion,
                    skip_normalization=args.skip_normalization,
                    skip_clustering=args.skip_clustering,
                    skip_ai=args.skip_ai,
                    continue_on_ai_failure=args.continue_on_ai_failure,
                    refresh_digest=args.refresh_digest,
                    limit=args.limit,
                    digest_limit=args.digest_limit,
                    triggered_by="cli",
                )
            payload = OrchestrationRunDetail.model_validate(result).model_dump(mode="json")
        except (OrchestrationInvalidRequestError, OrchestrationRunAlreadyActiveError) as exc:
            payload = {"status": "failed", "error_message": str(exc)}
    finally:
        db.close()

    print(json.dumps(payload, indent=2))

    # Exit non-zero on failure states so ECS marks the task as failed.
    # This allows CloudWatch alarms and EventBridge retry logic to trigger correctly.
    # Valid terminal statuses:
    #   success         — all steps completed successfully
    #   partial_success — event_analysis failed but the pipeline continued
    #   failed          — pipeline aborted (exception, lock conflict, invalid request)
    #   cancelled       — run was cancelled externally
    terminal_success = {"success", "partial_success"}
    if payload.get("status") not in terminal_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
