from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.source import FetchMethod, Source, SourceType
from app.schemas.source import SourceCreate, SourceUpdate


class SourceNotFoundError(Exception):
    pass


class DuplicateSourceError(Exception):
    pass


def create_source(db: Session, source_create: SourceCreate) -> Source:
    if _source_exists_for_url(db, source_create.url):
        raise DuplicateSourceError("A source with this URL already exists.")

    source = Source(**source_create.model_dump())
    db.add(source)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateSourceError("A source with this URL or RSS URL already exists.") from exc

    db.refresh(source)
    return source


def get_source(db: Session, source_id: UUID) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise SourceNotFoundError("Source not found.")
    return source


def list_sources(
    db: Session,
    *,
    limit: int,
    offset: int,
    source_type: SourceType | None = None,
    category: str | None = None,
    region: str | None = None,
    is_active: bool | None = None,
    priority: int | None = None,
    fetch_method: FetchMethod | None = None,
) -> tuple[list[Source], int]:
    filters = {
        "source_type": source_type,
        "category": category,
        "region": region,
        "is_active": is_active,
        "priority": priority,
        "fetch_method": fetch_method,
    }
    query = _apply_filters(select(Source), filters).order_by(
        Source.created_at.desc(),
        Source.name.asc(),
    )
    count_query = _apply_filters(select(func.count(Source.id)), filters)

    total = db.scalar(count_query) or 0
    sources = list(db.scalars(query.limit(limit).offset(offset)))
    return sources, total


def update_source(db: Session, source_id: UUID, source_update: SourceUpdate) -> Source:
    source = get_source(db, source_id)
    update_data = source_update.model_dump(exclude_unset=True)

    if "url" in update_data and update_data["url"] != source.url:
        if _source_exists_for_url(db, update_data["url"], exclude_source_id=source_id):
            raise DuplicateSourceError("A source with this URL already exists.")

    for field, value in update_data.items():
        setattr(source, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateSourceError("A source with this URL or RSS URL already exists.") from exc

    db.refresh(source)
    return source


def deactivate_source(db: Session, source_id: UUID) -> Source:
    source = get_source(db, source_id)
    source.is_active = False
    db.commit()
    db.refresh(source)
    return source


def activate_source(db: Session, source_id: UUID) -> Source:
    source = get_source(db, source_id)
    source.is_active = True
    db.commit()
    db.refresh(source)
    return source


def _source_exists_for_url(
    db: Session,
    url: str,
    *,
    exclude_source_id: UUID | None = None,
) -> bool:
    query = select(Source.id).where(Source.url == url)
    if exclude_source_id is not None:
        query = query.where(Source.id != exclude_source_id)
    return db.scalar(query) is not None


def _apply_filters(query: Select[tuple[Source]] | Select[tuple[int]], filters: dict[str, object]):
    if filters["source_type"] is not None:
        query = query.where(Source.source_type == filters["source_type"])
    if filters["category"] is not None:
        query = query.where(Source.category == filters["category"])
    if filters["region"] is not None:
        query = query.where(Source.region == filters["region"])
    if filters["is_active"] is not None:
        query = query.where(Source.is_active == filters["is_active"])
    if filters["priority"] is not None:
        query = query.where(Source.priority == filters["priority"])
    if filters["fetch_method"] is not None:
        query = query.where(Source.fetch_method == filters["fetch_method"])
    return query
