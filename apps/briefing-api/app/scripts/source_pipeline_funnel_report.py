import argparse
import json
from datetime import date

from app.db.session import SessionLocal
from app.services.digest_service import resolve_digest_window
from app.services.priority_pipeline_service import build_priority_funnel_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Per-source ingest → normalize → cluster → analyze funnel for priority sources."
    )
    parser.add_argument("--date", type=date.fromisoformat, dest="digest_date", default=None)
    parser.add_argument(
        "--global-batch-limit",
        type=int,
        default=200,
        help="Global orchestration limit used to infer batch starvation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digest_date = args.digest_date or date.today()
    _, window_start, window_end = resolve_digest_window(digest_date=digest_date)

    db = SessionLocal()
    try:
        report = build_priority_funnel_report(
            db,
            window_start=window_start,
            window_end=window_end,
            global_batch_limit=args.global_batch_limit,
        )
    finally:
        db.close()

    print(f"Priority source funnel | {report['window_start']} → {report['window_end']}")
    backlog = report["global_backlog"]
    print(
        "Global backlog: "
        f"pending_norm={backlog['pending_normalization']} "
        f"unclustered={backlog['unclustered_success_articles']} "
        f"needs_analysis={backlog['events_needing_analysis']} "
        f"(batch_limit={backlog['global_batch_limit']})"
    )
    print()
    print(
        "source | raw | norm_ok | dup | fail | pending | all_pending | clustered | analyzed | root_cause"
    )
    print("-" * 120)
    for row in report["sources"]:
        if row.get("status") == "not_configured":
            print(f"{row['source_name']} | NOT_IN_DB | {row['starvation_diagnosis']}")
            continue
        print(
            " | ".join(
                [
                    str(row["source_name"])[:24],
                    str(row["raw_ingested"]),
                    str(row["normalization_success"]),
                    str(row["normalization_duplicate"]),
                    str(row["normalization_failed"]),
                    str(row["pending_normalization"]),
                    str(row.get("all_time_pending_normalization", "")),
                    str(row["clustered"]),
                    str(row["analyzed"]),
                    str(row.get("normalization_root_cause", row["starvation_diagnosis"]))[:48],
                ]
            )
        )
        for key in ("pending_examples", "duplicate_examples", "failed_examples"):
            examples = row.get(key) or []
            if examples:
                print(f"  {key}: {examples}")
        diagnostic = row.get("analysis_diagnostic") or {}
        if diagnostic.get("pending_analysis_events", 0) > 0 or diagnostic.get(
            "clustered_events_all_time", 0
        ) > 0:
            print(
                "  analysis_diagnostic: "
                f"clustered_all={diagnostic.get('clustered_events_all_time')} "
                f"analyzed_all={diagnostic.get('analyzed_events_all_time')} "
                f"pending={diagnostic.get('pending_analysis_events')} "
                f"cause={diagnostic.get('analysis_drop_off_cause')}"
            )
            pending_examples = diagnostic.get("pending_analysis_examples") or []
            if pending_examples:
                print(f"  pending_analysis_examples: {pending_examples}")
    print()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
