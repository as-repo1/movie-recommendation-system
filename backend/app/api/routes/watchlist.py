"""app/api/routes/watchlist.py — database-backed watchlist endpoints (user-aware)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_id, get_db, get_current_user_optional
from app.models.db import WatchlistItem, User

router = APIRouter(tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    movie_id: int = Field(..., description="TMDB movie ID to add to watchlist")


def _build_watchlist_filter(session_id: str, user: User | None):
    """Return the appropriate SQLAlchemy filter based on auth state."""
    if user:
        return WatchlistItem.user_id == user.id
    return (WatchlistItem.session_id == session_id) & (WatchlistItem.user_id == None)  # noqa: E711


@router.get("", response_model=list[int])
async def get_watchlist(
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all movie IDs in the user's watchlist, ordered by date added (newest first)."""
    stmt = (
        select(WatchlistItem.movie_id)
        .where(_build_watchlist_filter(session_id, current_user))
        .order_by(WatchlistItem.added_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=list[int])
async def add_to_watchlist(
    body: WatchlistAddRequest,
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Add a movie to the watchlist. Returns the updated watchlist."""
    stmt = select(WatchlistItem).where(
        _build_watchlist_filter(session_id, current_user),
        WatchlistItem.movie_id == body.movie_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if not existing:
        item = WatchlistItem(
            session_id=session_id,
            movie_id=body.movie_id,
            user_id=current_user.id if current_user else None,
        )
        db.add(item)
        await db.commit()

    return await get_watchlist(session_id=session_id, current_user=current_user, db=db)


@router.delete("/{movie_id}", response_model=list[int])
async def remove_from_watchlist(
    movie_id: int,
    session_id: str = Depends(get_session_id),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Remove a movie from the watchlist. Returns the updated watchlist."""
    stmt = delete(WatchlistItem).where(
        _build_watchlist_filter(session_id, current_user),
        WatchlistItem.movie_id == movie_id,
    )
    await db.execute(stmt)
    await db.commit()

    return await get_watchlist(session_id=session_id, current_user=current_user, db=db)
