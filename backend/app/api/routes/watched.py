"""app/api/routes/watched.py — database-backed watched list and ratings endpoints (user-aware)."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_id, get_db, get_current_user_optional
from app.models.db import WatchedMovie, WatchlistItem, User

router = APIRouter(tags=["watched"])


class WatchedEntry(BaseModel):
    rating: float = Field(..., ge=0.5, le=10.0)
    added_at: datetime = Field(..., serialization_alias="addedAt")

    model_config = {"populate_by_name": True}


class WatchedAddRequest(BaseModel):
    movie_id: int = Field(..., description="TMDB movie ID to mark as watched")
    rating: float = Field(..., ge=0.5, le=10.0, description="User rating 0.5–10.0")


class WatchedUpdateRequest(BaseModel):
    rating: float = Field(..., ge=0.5, le=10.0, description="Updated user rating 0.5–10.0")


def _build_watched_filter(session_id: str, user: User | None):
    """Return the appropriate SQLAlchemy filter based on auth state."""
    if user:
        return WatchedMovie.user_id == user.id
    return (WatchedMovie.session_id == session_id) & (WatchedMovie.user_id == None)  # noqa: E711


def _build_watchlist_filter(session_id: str, user: User | None):
    if user:
        return WatchlistItem.user_id == user.id
    return (WatchlistItem.session_id == session_id) & (WatchlistItem.user_id == None)  # noqa: E711


@router.get("", response_model=dict[int, WatchedEntry])
async def get_watched(
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all watched movies with ratings for the current user/session."""
    stmt = select(WatchedMovie).where(_build_watched_filter(session_id, current_user))
    items = (await db.execute(stmt)).scalars().all()
    return {
        item.movie_id: WatchedEntry(rating=item.rating, added_at=item.added_at)
        for item in items
    }


@router.post("", response_model=dict[int, WatchedEntry])
async def add_watched(
    body: WatchedAddRequest,
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Mark a movie as watched with rating. Auto-removes from watchlist."""
    stmt = select(WatchedMovie).where(
        _build_watched_filter(session_id, current_user),
        WatchedMovie.movie_id == body.movie_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.rating = body.rating
        existing.added_at = datetime.now(timezone.utc)
    else:
        db.add(WatchedMovie(
            session_id=session_id,
            movie_id=body.movie_id,
            rating=body.rating,
            user_id=current_user.id if current_user else None,
        ))

    # Remove from watchlist automatically
    await db.execute(delete(WatchlistItem).where(
        _build_watchlist_filter(session_id, current_user),
        WatchlistItem.movie_id == body.movie_id,
    ))
    await db.commit()

    return await get_watched(session_id=session_id, current_user=current_user, db=db)


@router.put("/{movie_id}", response_model=dict[int, WatchedEntry])
async def update_rating(
    movie_id: int,
    body: WatchedUpdateRequest,
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Update the rating for a watched movie."""
    stmt = select(WatchedMovie).where(
        _build_watched_filter(session_id, current_user),
        WatchedMovie.movie_id == movie_id,
    )
    item = (await db.execute(stmt)).scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} is not in your watched list.")

    item.rating = body.rating
    await db.commit()

    return await get_watched(session_id=session_id, current_user=current_user, db=db)


@router.delete("/{movie_id}", response_model=dict[int, WatchedEntry])
async def remove_watched(
    movie_id: int,
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Remove a movie from the watched list."""
    await db.execute(delete(WatchedMovie).where(
        _build_watched_filter(session_id, current_user),
        WatchedMovie.movie_id == movie_id,
    ))
    await db.commit()

    return await get_watched(session_id=session_id, current_user=current_user, db=db)
