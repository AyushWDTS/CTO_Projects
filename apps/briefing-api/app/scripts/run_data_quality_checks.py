import argparse
import json
from uuid import UUID

from app.db.session import SessionLocal
from app.models.data_quality import DataQualitySeverity
from app.services.data_quality_service import run_data_quality_checks, run_source_health_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic data quality checks.")
    parser.add_argument("--source-id", type=UUID, default=None)
    parser.add_argument("--severity", choices=[severity.value for severity in DataQualitySeverity])
    parser.add_argument("--source-health", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print compact JSON output.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.source_health:
            result = run_source_health_checks(db, source_id=args.source_id)
        else:
            min_severity = DataQualitySeverity(args.severity) if args.severity else None
            result = run_data_quality_checks(
                db,
                source_id=args.source_id,
                min_severity=min_severity,
            )
        payload = result.model_dump(mode="json", by_alias=True)
        print(json.dumps(payload if args.json else payload, indent=None if args.json else 2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
