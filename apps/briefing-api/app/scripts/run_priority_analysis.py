import argparse
import json
from datetime import date

from app.db.session import SessionLocal
from app.data.priority_pipeline_sources import PRIORITY_PIPELINE_SOURCE_NAMES
from app.services.digest_service import resolve_digest_window
from app.services.priority_pipeline_service import (
    CLUSTERED_ANALYSIS_PRIORITY_NAMES,
    DEFAULT_PRIORITY_ANALYSIS_ROUNDS,
    DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    analyze_clustered_priority_sources,
    analyze_priority_sources,
    build_priority_funnel_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run targeted AI analysis for priority Smart Table / competitor sources."
    )
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    )
    parser.add_argument(
        "--analysis-rounds",
        type=int,
        default=DEFAULT_PRIORITY_ANALYSIS_ROUNDS,
    )
    parser.add_argument(
        "--clustered-only",
        action="store_true",
        help="Only analyze RFID Journal and IPC (sources with clustered events focus).",
    )
    parser.add_argument(
        "--source-name",
        action="append",
        default=[],
        help="Restrict to specific source names (repeatable).",
    )
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digest_date = args.digest_date or date.today()
    _, window_start, window_end = resolve_digest_window(digest_date=digest_date)

    source_names: tuple[str, ...] | None = None
    if args.source_name:
        source_names = tuple(args.source_name)
    elif args.clustered_only:
        source_names = CLUSTERED_ANALYSIS_PRIORITY_NAMES

    db = SessionLocal()
    try:
        if args.report_only:
            report = build_priority_funnel_report(
                db,
                window_start=window_start,
                window_end=window_end,
                source_names=source_names or PRIORITY_PIPELINE_SOURCE_NAMES,
            )
            print(json.dumps(report, indent=2))
            return

        if args.clustered_only or source_names == CLUSTERED_ANALYSIS_PRIORITY_NAMES:
            analysis = analyze_clustered_priority_sources(
                db,
                limit_per_source=args.limit_per_source,
                max_rounds=args.analysis_rounds,
                source_names=source_names,
            )
        else:
            analysis = analyze_priority_sources(
                db,
                limit_per_source=args.limit_per_source,
                max_rounds=args.analysis_rounds,
                source_names=source_names,
            )

        funnel = build_priority_funnel_report(
            db,
            window_start=window_start,
            window_end=window_end,
            source_names=source_names or PRIORITY_PIPELINE_SOURCE_NAMES,
        )
        print(json.dumps({"analysis": analysis, "funnel_after": funnel}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
