"""app/api/routes/auth.py — user registration and authentication routes."""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.db import User, WatchlistItem, WatchedMovie

router = APIRouter(tags=["authentication"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    anonymous_session_id: str | None = Field(default=None)


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _migrate_anonymous_data(session_id: str, user_id: int, db: AsyncSession) -> None:
    """
    Move anonymous watchlist + watched movies to the newly authenticated user.
    Skips duplicates if the user already has that movie in the list.
    """
    # --- Watchlist ---
    anon_wl = (await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.session_id == session_id,
            WatchlistItem.user_id == None,  # noqa: E711
        )
    )).scalars().all()

    if anon_wl:
        user_wl_ids = set((await db.execute(
            select(WatchlistItem.movie_id).where(WatchlistItem.user_id == user_id)
        )).scalars().all())
        for item in anon_wl:
            if item.movie_id in user_wl_ids:
                await db.delete(item)          # drop dupe anon row
            else:
                item.user_id = user_id         # adopt into account

    # --- Watched movies ---
    anon_wm = (await db.execute(
        select(WatchedMovie).where(
            WatchedMovie.session_id == session_id,
            WatchedMovie.user_id == None,  # noqa: E711
        )
    )).scalars().all()

    if anon_wm:
        user_wm_ids = set((await db.execute(
            select(WatchedMovie.movie_id).where(WatchedMovie.user_id == user_id)
        )).scalars().all())
        for item in anon_wm:
            if item.movie_id in user_wm_ids:
                await db.delete(item)
            else:
                item.user_id = user_id

    await db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: AuthRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user. Migrates anonymous watchlist/watched data if session_id provided."""
    # Duplicate username check
    existing = (await db.execute(
        select(User).where(User.username == body.username.strip())
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username is already taken.")

    user = User(
        username=body.username.strip(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if body.anonymous_session_id and body.anonymous_session_id.strip():
        await _migrate_anonymous_data(body.anonymous_session_id.strip(), user.id, db)

    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenResponse)
async def login(body: AuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate credentials and return a JWT. Migrates anonymous data if session_id provided."""
    user = (await db.execute(
        select(User).where(User.username == body.username.strip())
    )).scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    if body.anonymous_session_id and body.anonymous_session_id.strip():
        await _migrate_anonymous_data(body.anonymous_session_id.strip(), user.id, db)

    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return user
