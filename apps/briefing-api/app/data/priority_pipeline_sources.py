"""Sources that must not be starved by global normalization/clustering/analysis batches."""

PRIORITY_PIPELINE_SOURCE_NAMES: tuple[str, ...] = (
    # AI / ML / CV
    "MIT Technology Review AI",
    "VentureBeat AI",
    "NVIDIA Newsroom",
    # Competitor / smart-table gaming suppliers and labs
    "TCSJOHNHUXLEY",
    "Tangam Systems",
    "Interblock",
    "Gaming Laboratories International (GLI)",
    "BMM Testlabs",
    "Light & Wonder Newsroom",
    # Semiconductors / components / automation
    "Semiconductor Engineering",
    "EE Times",
    "RFID Journal",
    "IPC",
    "SEMI",
    "Zebra Technologies Newsroom",
    "NXP Newsroom",
)
