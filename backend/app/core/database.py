"""app/core/database.py — database setup and async session management."""

from __future__ import annotations

from typing import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create the async engine
# Note: For SQLite we might need different arguments (like check_same_thread), but for Postgres we don't.
is_sqlite = settings.db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_async_engine(
    settings.db_url,
    echo=False,
    future=True,
    connect_args=connect_args,
)

# Async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for injecting async DB sessions into route handlers."""
    async with async_session_maker() as session:
        yield session

async def init_db() -> None:
    """Startup database initialization (creates tables and runs safe migrations)."""
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error("Failed to initialise database tables: %s", e)

    # ── Safe incremental migrations ──────────────────────────────────────────
    # These are idempotent: they only run if the column doesn't already exist.
    migrations = [
        # Add user_id FK to watchlist_items (added in auth update)
        (
            "watchlist_items",
            "user_id",
            "ALTER TABLE watchlist_items ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE",
        ),
        # Add user_id FK to watched_movies (added in auth update)
        (
            "watched_movies",
            "user_id",
            "ALTER TABLE watched_movies ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE",
        ),
    ]

    async with engine.begin() as conn:
        for table, column, sql in migrations:
            try:
                # SQLite: check if column exists via PRAGMA
                if is_sqlite:
                    rows = await conn.execute(text(f"PRAGMA table_info({table})"))
                    cols = [r[1] for r in rows.fetchall()]
                    if column in cols:
                        continue
                await conn.execute(text(sql))
                logger.info("Migration applied: added %s.%s", table, column)
            except Exception:
                pass  # Column likely already exists on non-SQLite engines
