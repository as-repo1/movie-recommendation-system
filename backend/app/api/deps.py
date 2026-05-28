"""app/api/deps.py — FastAPI dependencies for database and session context."""

from __future__ import annotations

from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.db import User

async def get_session_id(
    x_session_id: str | None = Header(default=None, alias="X-Session-ID", description="Anonymous user session UUID")
) -> str:
    """Extract and validate the X-Session-ID header."""
    if not x_session_id or not x_session_id.strip():
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is missing or empty. Please set it in the client application."
        )
    return x_session_id.strip()

async def get_current_user_optional(
    authorization: str | None = Header(default=None, description="Bearer token"),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """Extract and validate the Bearer token optionally."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ")[1].strip()
    user_id = decode_access_token(token)
    if not user_id:
        return None
    
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def get_current_user(
    user: User | None = Depends(get_current_user_optional)
) -> User:
    """Required authentication dependency."""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials. Please sign in."
        )
    return user
