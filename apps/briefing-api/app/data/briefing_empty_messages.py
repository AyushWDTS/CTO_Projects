from app.data.briefing_coverage import BRIEFING_COVERAGE_MATRIX

STATUS_LABELS = {
    "covered": "covered",
    "partial": "partially covered",
    "manual_only": "manual-only",
    "not_covered": "not yet covered",
}


def empty_section_message(section: str) -> str:
    coverage = BRIEFING_COVERAGE_MATRIX.get(section, {})
    status = str(coverage.get("status") or "partial")
    status_label = STATUS_LABELS.get(status, status.replace("_", " "))
    gaps = coverage.get("gaps") or []
    gap_hint = gaps[0] if gaps else "additional source coverage may be needed"

    return (
        f"No {section} signals in today's window. Automated coverage is {status_label}. "
        f"Known gap: {gap_hint}."
    )
