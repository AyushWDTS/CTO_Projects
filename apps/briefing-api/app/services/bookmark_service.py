from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.bookmark import BriefingBookmark
from app.schemas.bookmark import BriefingBookmarkCreate, BriefingBookmarkRead


class BookmarkNotFoundError(Exception):
    pass


class BookmarkAlreadyExistsError(Exception):
    pass


def create_bookmark(db: Session, payload: BriefingBookmarkCreate) -> BriefingBookmarkRead:
    existing = db.scalar(
        select(BriefingBookmark).where(
            BriefingBookmark.user_key == payload.user_key,
            BriefingBookmark.event_id == payload.event_id,
        )
    )
    if existing is not None:
        raise BookmarkAlreadyExistsError("Bookmark already exists for this story.")

    bookmark = BriefingBookmark(
        user_key=payload.user_key,
        event_id=payload.event_id,
        digest_id=payload.digest_id,
        digest_item_id=payload.digest_item_id,
        digest_date=payload.digest_date,
        section=payload.section,
        headline=payload.headline,
        summary=payload.summary,
        why_it_matters=payload.why_it_matters,
        suggested_action=payload.suggested_action,
        source_url=payload.source_url,
        importance_tier=payload.importance_tier,
        note=payload.note,
        metadata_=payload.metadata,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return BriefingBookmarkRead.model_validate(bookmark)


def list_bookmarks(
    db: Session,
    *,
    user_key: str = "default",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[BriefingBookmarkRead], int]:
    filters = BriefingBookmark.user_key == user_key
    total = db.scalar(select(func.count(BriefingBookmark.id)).where(filters)) or 0
    rows = list(
        db.scalars(
            select(BriefingBookmark)
            .where(filters)
            .order_by(BriefingBookmark.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return [BriefingBookmarkRead.model_validate(row) for row in rows], int(total)


def get_bookmarked_event_ids(
    db: Session,
    *,
    user_key: str = "default",
    event_ids: list[UUID] | None = None,
) -> list[UUID]:
    query: Select[tuple[UUID]] = select(BriefingBookmark.event_id).where(
        BriefingBookmark.user_key == user_key
    )
    if event_ids:
        query = query.where(BriefingBookmark.event_id.in_(event_ids))
    return list(db.scalars(query))


def delete_bookmark(db: Session, bookmark_id: UUID, *, user_key: str = "default") -> None:
    bookmark = db.scalar(
        select(BriefingBookmark).where(
            BriefingBookmark.id == bookmark_id,
            BriefingBookmark.user_key == user_key,
        )
    )
    if bookmark is None:
        raise BookmarkNotFoundError("Bookmark not found.")
    db.delete(bookmark)
    db.commit()


def delete_bookmark_by_event(
    db: Session,
    event_id: UUID,
    *,
    user_key: str = "default",
) -> None:
    bookmark = db.scalar(
        select(BriefingBookmark).where(
            BriefingBookmark.user_key == user_key,
            BriefingBookmark.event_id == event_id,
        )
    )
    if bookmark is None:
        raise BookmarkNotFoundError("Bookmark not found.")
    db.delete(bookmark)
    db.commit()
