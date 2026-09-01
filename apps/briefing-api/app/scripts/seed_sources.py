from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.source_catalog import (
    SOURCE_URL_MIGRATIONS,
    all_catalog_sources,
    validate_source_catalog,
)
from app.db.session import SessionLocal
from app.models.source import Source
from app.schemas.source import SourceCreate

INITIAL_SOURCES = all_catalog_sources()


def seed_sources(
    db: Session,
    sources: list[SourceCreate] | None = None,
) -> dict[str, int]:
    created = 0
    updated = 0
    if sources is None:
        source_list = INITIAL_SOURCES
        validate_source_catalog(source_list)
    else:
        source_list = sources

    for source_create in source_list:
        source_data = source_create.model_dump()
        existing_source = db.scalar(select(Source).where(Source.url == source_data["url"]))
        if existing_source is None:
            legacy_urls = SOURCE_URL_MIGRATIONS.get(source_data["url"], [])
            if legacy_urls:
                existing_source = db.scalar(select(Source).where(Source.url.in_(legacy_urls)))

        if existing_source is None:
            db.add(Source(**source_data))
            created += 1
            continue

        for field, value in source_data.items():
            setattr(existing_source, field, value)
        updated += 1

    db.commit()
    return {"created": created, "updated": updated}


def main() -> None:
    db = SessionLocal()
    try:
        result = seed_sources(db)
    finally:
        db.close()

    print(f"Seeded sources: created={result['created']} updated={result['updated']}")


if __name__ == "__main__":
    main()
