from app.data.briefing_sections import BriefingSection

COVERAGE_STATUS_VALUES = {"covered", "partial", "manual_only", "not_covered"}

BRIEFING_COVERAGE_MATRIX = {
    BriefingSection.AI_ML_CV.value: {
        "status": "partial",
        "regions": ["Global", "US"],
        "current_sources": [
            "MIT Technology Review AI",
            "VentureBeat AI",
            "The Verge AI",
            "NVIDIA Newsroom",
            "IEEE Spectrum AI",
        ],
        "gaps": ["Academic CV conference feeds and edge-AI deployment case studies"],
    },
    BriefingSection.SMART_TABLES.value: {
        "status": "partial",
        "regions": ["Global"],
        "current_sources": [
            "RFID Journal",
            "CDC Gaming Reports",
            "GGRAsia",
            "Inside Asian Gaming",
            "Gaming Laboratories International (GLI)",
            "BMM Testlabs",
            "TCSJOHNHUXLEY",
            "Tangam Systems",
            "Interblock",
        ],
        "gaps": [
            "Activate GLI/BMM/supplier news pages for automatic ingestion; "
            "add Everi and Table Trac press feeds when stable URLs are verified"
        ],
    },
    BriefingSection.SEMICONDUCTORS.value: {
        "status": "partial",
        "regions": ["Global", "Asia", "US"],
        "current_sources": [
            "SEMI",
            "Semiconductor Engineering",
            "EE Times",
            "IPC",
            "NXP Newsroom",
            "Office of the United States Trade Representative",
        ],
        "gaps": ["PCB distributor and foundry capacity feeds"],
    },
    BriefingSection.AUTOMATION.value: {
        "status": "partial",
        "regions": ["Global"],
        "current_sources": ["Zebra Technologies Newsroom", "IEEE Spectrum AI"],
        "gaps": ["Industrial automation and edge-compute vendor feeds"],
    },
    BriefingSection.COMPETITORS.value: {
        "status": "partial",
        "regions": ["Global"],
        "current_sources": [
            "MGM Resorts Investor Relations",
            "Las Vegas Sands Investor Relations",
            "Light & Wonder Newsroom",
            "Tangam Systems",
            "Interblock",
            "TCSJOHNHUXLEY",
        ],
        "gaps": ["Additional competitor press releases and filings"],
    },
    BriefingSection.REGULATION.value: {
        "status": "partial",
        "regions": ["US", "UK", "Philippines", "Global"],
        "current_sources": [
            "Nevada Gaming Control Board",
            "PAGCOR",
            "UK Gambling Commission",
            "FinCEN",
        ],
        "gaps": ["Macau and Australia gaming regulator feeds"],
    },
}


def validate_coverage_matrix() -> None:
    expected_sections = set(BRIEFING_COVERAGE_MATRIX)
    required = {
        BriefingSection.AI_ML_CV.value,
        BriefingSection.SMART_TABLES.value,
        BriefingSection.SEMICONDUCTORS.value,
        BriefingSection.AUTOMATION.value,
        BriefingSection.COMPETITORS.value,
        BriefingSection.REGULATION.value,
    }
    if expected_sections != required:
        raise ValueError("Coverage matrix sections do not match dashboard briefing sections")
    for section, payload in BRIEFING_COVERAGE_MATRIX.items():
        if payload.get("status") not in COVERAGE_STATUS_VALUES:
            raise ValueError(f"Invalid coverage status for {section}")
