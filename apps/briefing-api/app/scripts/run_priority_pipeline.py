import argparse
import json
from datetime import date

from app.db.session import SessionLocal
from app.services.digest_service import resolve_digest_window
from app.services.priority_pipeline_service import (
    DEFAULT_PRIORITY_NORMALIZATION_ROUNDS,
    DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    analyze_clustered_priority_sources,
    analyze_priority_sources,
    build_priority_funnel_report,
    cluster_priority_sources,
    normalize_priority_sources,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize, cluster, and analyze priority competitor/smart-table sources."
    )
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=DEFAULT_PRIORITY_PER_SOURCE_LIMIT,
    )
    parser.add_argument(
        "--normalization-rounds",
        type=int,
        default=DEFAULT_PRIORITY_NORMALIZATION_ROUNDS,
    )
    parser.add_argument("--skip-normalization", action="store_true")
    parser.add_argument("--skip-clustering", action="store_true")
    parser.add_argument("--skip-analysis", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    digest_date = args.digest_date or date.today()
    _, window_start, window_end = resolve_digest_window(digest_date=digest_date)

    db = SessionLocal()
    try:
        if args.report_only:
            report = build_priority_funnel_report(
                db,
                window_start=window_start,
                window_end=window_end,
            )
            print(json.dumps(report, indent=2))
            return

        payload: dict = {"digest_date": digest_date.isoformat()}
        if not args.skip_normalization:
            payload["normalization"] = normalize_priority_sources(
                db,
                limit_per_source=args.limit_per_source,
                max_rounds=args.normalization_rounds,
            )
        if not args.skip_clustering:
            payload["clustering"] = cluster_priority_sources(
                db,
                limit_per_source=args.limit_per_source,
            )
        if not args.skip_analysis:
            if args.skip_normalization and args.skip_clustering:
                payload["analysis"] = analyze_clustered_priority_sources(
                    db,
                    limit_per_source=args.limit_per_source,
                )
            else:
                payload["analysis"] = analyze_priority_sources(
                    db,
                    limit_per_source=args.limit_per_source,
                )
        payload["funnel_after"] = build_priority_funnel_report(
            db,
            window_start=window_start,
            window_end=window_end,
        )
        print(json.dumps(payload, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
