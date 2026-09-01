import re

COMPETITOR_ENTITIES: list[dict[str, list[str]]] = [
    {"name": "Light & Wonder", "aliases": ["light and wonder", "light & wonder", "lnw"]},
    {"name": "Aristocrat", "aliases": ["aristocrat leisure", "aristocrat gaming"]},
    {"name": "IGT", "aliases": ["international game technology", "igt corporation"]},
    {"name": "Konami", "aliases": ["konami gaming", "konami digital"]},
    {"name": "Everi", "aliases": ["everi holdings"]},
    {"name": "Tangam", "aliases": ["tangam systems"]},
    {"name": "Acres", "aliases": ["acres manufacturing", "acres technology"]},
    {"name": "Interblock", "aliases": ["interblock usa"]},
    {"name": "TCSJOHNHUXLEY", "aliases": ["tcsjohnhuxley", "tcs john huxley"]},
    {"name": "Table Trac", "aliases": ["table trac", "tabletrac"]},
]


def match_competitor(text: str) -> str | None:
    lowered = text.lower()
    for entry in COMPETITOR_ENTITIES:
        names = [entry["name"], *entry.get("aliases", [])]
        for name in names:
            pattern = rf"\b{re.escape(name.lower())}\b" if len(name) <= 4 else re.escape(name.lower())
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                return entry["name"]
    return None
