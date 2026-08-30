"""linux/app/db.py — Local SQLite database for Watchlist, Watched History, and User Ratings."""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".local" / "share" / "reclens"
DB_PATH = DATA_DIR / "db.sqlite"


@dataclass
class WatchlistItem:
    movie_id: int
    title: str
    year: int | None
    poster_path: str
    vote_average: float
    added_at: str
    notes: str = ""


@dataclass
class WatchedItem:
    movie_id: int
    title: str
    year: int | None
    poster_path: str
    vote_average: float
    user_rating: float | None
    watched_at: str
    notes: str = ""


class LocalDatabase:
    """Thread-safe SQLite local storage manager for desktop user profiles."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    movie_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    year INTEGER,
                    poster_path TEXT,
                    vote_average REAL DEFAULT 0,
                    added_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS watched (
                    movie_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    year INTEGER,
                    poster_path TEXT,
                    vote_average REAL DEFAULT 0,
                    user_rating REAL,
                    watched_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_watchlist_added ON watchlist(added_at DESC);
                CREATE INDEX IF NOT EXISTS idx_watched_date ON watched(watched_at DESC);
                """
            )

    # ── Watchlist Operations ─────────────────────────────────────────────────

    def add_to_watchlist(
        self,
        movie_id: int,
        title: str,
        year: int | None = None,
        poster_path: str = "",
        vote_average: float = 0.0,
        notes: str = "",
    ) -> bool:
        """Add a film to user watchlist."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO watchlist (movie_id, title, year, poster_path, vote_average, added_at, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(movie_id) DO UPDATE SET
                        title = excluded.title,
                        year = excluded.year,
                        poster_path = excluded.poster_path,
                        vote_average = excluded.vote_average,
                        notes = excluded.notes
                    """,
                    (movie_id, title, year, poster_path, vote_average, now, notes),
                )
                return True
        except Exception as e:
            logger.error("Failed to add movie %d to watchlist: %s", movie_id, e)
            return False

    def remove_from_watchlist(self, movie_id: int) -> bool:
        """Remove a film from user watchlist."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM watchlist WHERE movie_id = ?", (movie_id,))
                return True
        except Exception as e:
            logger.error("Failed to remove movie %d from watchlist: %s", movie_id, e)
            return False

    def is_in_watchlist(self, movie_id: int) -> bool:
        """Check if a film is in the watchlist."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM watchlist WHERE movie_id = ?", (movie_id,))
            return cur.fetchone() is not None

    def get_watchlist(self) -> list[WatchlistItem]:
        """Fetch all watchlist items ordered by most recently added."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
            return [
                WatchlistItem(
                    movie_id=row["movie_id"],
                    title=row["title"],
                    year=row["year"],
                    poster_path=row["poster_path"] or "",
                    vote_average=float(row["vote_average"] or 0.0),
                    added_at=row["added_at"],
                    notes=row["notes"] or "",
                )
                for row in cur.fetchall()
            ]

    # ── Watched History Operations ───────────────────────────────────────────

    def mark_as_watched(
        self,
        movie_id: int,
        title: str,
        year: int | None = None,
        poster_path: str = "",
        vote_average: float = 0.0,
        user_rating: float | None = None,
        notes: str = "",
    ) -> bool:
        """Mark a film as watched with optional user rating and notes."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO watched (movie_id, title, year, poster_path, vote_average, user_rating, watched_at, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(movie_id) DO UPDATE SET
                        title = excluded.title,
                        year = excluded.year,
                        poster_path = excluded.poster_path,
                        vote_average = excluded.vote_average,
                        user_rating = excluded.user_rating,
                        notes = excluded.notes
                    """,
                    (movie_id, title, year, poster_path, vote_average, user_rating, now, notes),
                )
                # Also optionally remove from watchlist once watched
                conn.execute("DELETE FROM watchlist WHERE movie_id = ?", (movie_id,))
                return True
        except Exception as e:
            logger.error("Failed to mark movie %d as watched: %s", movie_id, e)
            return False

    def remove_from_watched(self, movie_id: int) -> bool:
        """Remove a film from watched history."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM watched WHERE movie_id = ?", (movie_id,))
                return True
        except Exception as e:
            logger.error("Failed to remove movie %d from watched: %s", movie_id, e)
            return False

    def is_watched(self, movie_id: int) -> bool:
        """Check if a film is in watched history."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM watched WHERE movie_id = ?", (movie_id,))
            return cur.fetchone() is not None

    def get_watched(self) -> list[WatchedItem]:
        """Fetch all watched items ordered by most recently watched."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM watched ORDER BY watched_at DESC")
            return [
                WatchedItem(
                    movie_id=row["movie_id"],
                    title=row["title"],
                    year=row["year"],
                    poster_path=row["poster_path"] or "",
                    vote_average=float(row["vote_average"] or 0.0),
                    user_rating=float(row["user_rating"]) if row["user_rating"] is not None else None,
                    watched_at=row["watched_at"],
                    notes=row["notes"] or "",
                )
                for row in cur.fetchall()
            ]

    # ── Export & Import Operations ───────────────────────────────────────────

    def export_data(self, target_file: Path, format: str = "json") -> bool:
        """Export user watchlist and watched history to JSON, CSV, or Markdown."""
        try:
            watchlist = self.get_watchlist()
            watched = self.get_watched()

            if format.lower() == "json":
                data = {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "watchlist": [item.__dict__ for item in watchlist],
                    "watched": [item.__dict__ for item in watched],
                }
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return True

            elif format.lower() == "csv":
                with open(target_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["type", "movie_id", "title", "year", "vote_average", "user_rating", "date", "notes"])
                    for w in watchlist:
                        writer.writerow(["watchlist", w.movie_id, w.title, w.year, w.vote_average, "", w.added_at, w.notes])
                    for w in watched:
                        writer.writerow(["watched", w.movie_id, w.title, w.year, w.vote_average, w.user_rating or "", w.watched_at, w.notes])
                return True

            elif format.lower() == "markdown" or format.lower() == "md":
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write("# RecLens Movie Collection Export\n\n")
                    f.write(f"Exported on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
                    f.write("## 📌 Watchlist\n\n")
                    if not watchlist:
                        f.write("*No items in watchlist.*\n\n")
                    else:
                        for w in watchlist:
                            f.write(f"- **{w.title}** ({w.year or 'N/A'}) — Rating: {w.vote_average:.1f}/10\n")
                    f.write("\n## 🎬 Watched History\n\n")
                    if not watched:
                        f.write("*No items in watched history.*\n\n")
                    else:
                        for w in watched:
                            user_r = f"⭐ {w.user_rating:.1f}/5" if w.user_rating else "No rating"
                            f.write(f"- **{w.title}** ({w.year or 'N/A'}) — Your Rating: {user_r} (TMDB: {w.vote_average:.1f}/10)\n")
                return True

            return False
        except Exception as e:
            logger.error("Failed to export data: %s", e)
            return False

    def import_data(self, source_file: Path) -> int:
        """Import watchlist and watched entries from JSON backup. Returns count of imported items."""
        count = 0
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)

            for item in data.get("watchlist", []):
                if self.add_to_watchlist(
                    movie_id=int(item["movie_id"]),
                    title=str(item["title"]),
                    year=int(item["year"]) if item.get("year") else None,
                    poster_path=str(item.get("poster_path", "")),
                    vote_average=float(item.get("vote_average", 0.0)),
                    notes=str(item.get("notes", "")),
                ):
                    count += 1

            for item in data.get("watched", []):
                if self.mark_as_watched(
                    movie_id=int(item["movie_id"]),
                    title=str(item["title"]),
                    year=int(item["year"]) if item.get("year") else None,
                    poster_path=str(item.get("poster_path", "")),
                    vote_average=float(item.get("vote_average", 0.0)),
                    user_rating=float(item["user_rating"]) if item.get("user_rating") is not None else None,
                    notes=str(item.get("notes", "")),
                ):
                    count += 1

            return count
        except Exception as e:
            logger.error("Failed to import data from %s: %s", source_file, e)
            return 0


# Global singleton instance
local_db = LocalDatabase()
