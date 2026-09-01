from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.bookmark import (
    BriefingBookmarkCreate,
    BriefingBookmarkList,
    BriefingBookmarkRead,
)
from app.services.bookmark_service import (
    BookmarkAlreadyExistsError,
    BookmarkNotFoundError,
    create_bookmark,
    delete_bookmark,
    delete_bookmark_by_event,
    get_bookmarked_event_ids,
    list_bookmarks,
)

router = APIRouter(prefix="/api/v1/bookmarks", tags=["bookmarks"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("", response_model=BriefingBookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark_endpoint(
    payload: BriefingBookmarkCreate,
    db: SessionDependency,
) -> BriefingBookmarkRead:
    try:
        return create_bookmark(db, payload)
    except BookmarkAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=BriefingBookmarkList)
def list_bookmarks_endpoint(
    db: SessionDependency,
    user_key: Annotated[str, Query(max_length=100)] = "default",
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BriefingBookmarkList:
    rows, total = list_bookmarks(db, user_key=user_key, limit=limit, offset=offset)
    return BriefingBookmarkList(items=rows, total=total, limit=limit, offset=offset)


@router.get("/event-ids", response_model=list[UUID])
def list_bookmarked_event_ids_endpoint(
    db: SessionDependency,
    user_key: Annotated[str, Query(max_length=100)] = "default",
    event_ids: Annotated[list[UUID] | None, Query()] = None,
) -> list[UUID]:
    return get_bookmarked_event_ids(db, user_key=user_key, event_ids=event_ids)


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark_endpoint(
    bookmark_id: UUID,
    db: SessionDependency,
    user_key: Annotated[str, Query(max_length=100)] = "default",
) -> None:
    try:
        delete_bookmark(db, bookmark_id, user_key=user_key)
    except BookmarkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/by-event/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark_by_event_endpoint(
    event_id: UUID,
    db: SessionDependency,
    user_key: Annotated[str, Query(max_length=100)] = "default",
) -> None:
    try:
        delete_bookmark_by_event(db, event_id, user_key=user_key)
    except BookmarkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
