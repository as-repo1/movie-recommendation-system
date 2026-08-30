"""linux/app/engine.py — In-process Machine Learning engine & Parquet catalog interface."""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from gi.repository import GLib

# Ensure root workspace is on python path for importing src.recommender
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.recommender import TopKSimilarityIndex, load_model, recommend, recommend_by_mood

logger = logging.getLogger(__name__)


class LinuxEngine:
    """High-performance in-process engine wrapping Parquet catalog and TopKSimilarityIndex."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or (PROJECT_ROOT / "data" / "processed")
        self.movies_df: pd.DataFrame | None = None
        self.similarity: TopKSimilarityIndex | np.ndarray | None = None
        self.is_loaded: bool = False
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="MLEngine")

    def load(self) -> bool:
        """Synchronously load Parquet catalog and Top-K similarity matrix."""
        try:
            parquet_path = self.data_dir / "movies_clean.parquet"
            pkl_path = self.data_dir / "movies.pkl"

            if parquet_path.exists():
                self.movies_df = pd.read_parquet(parquet_path)
            elif pkl_path.exists():
                self.movies_df = pd.read_pickle(pkl_path)
            else:
                logger.error("No movie catalog found in %s", self.data_dir)
                return False

            self.movies_df, self.similarity = load_model(str(self.data_dir))
            self.is_loaded = True
            logger.info("LinuxEngine successfully loaded %d movies.", len(self.movies_df))
            return True
        except Exception as e:
            logger.error("Failed to initialize LinuxEngine: %s", e)
            return False

    def load_async(self, callback: Callable[[bool], None]) -> None:
        """Load catalog in background thread and notify on GTK main loop."""
        def _worker():
            success = self.load()
            GLib.idle_add(callback, success)

        self.executor.submit(_worker)

    # ── Discovery & Filtering Queries ────────────────────────────────────────

    def get_hero_movie(self) -> dict[str, Any] | None:
        """Return a visually stunning top-rated blockbuster for the Home hero banner."""
        if not self.is_loaded or self.movies_df is None:
            return None
        # Find top movie with backdrop and high vote count
        df = self.movies_df[self.movies_df["vote_count"] > 5000].sort_values("bayesian_rating", ascending=False)
        if df.empty:
            df = self.movies_df.sort_values("vote_average", ascending=False)
        if not df.empty:
            return self._row_to_dict(df.iloc[0])
        return None

    def get_trending(self, n: int = 15) -> list[dict[str, Any]]:
        """Return top trending films based on vote counts and popularity."""
        if not self.is_loaded or self.movies_df is None:
            return []
        df = self.movies_df.sort_values(["vote_count", "vote_average"], ascending=[False, False]).head(n)
        return [self._row_to_dict(row) for _, row in df.iterrows()]

    def get_top_rated(self, n: int = 15) -> list[dict[str, Any]]:
        """Return highest Bayesian weighted rated films."""
        if not self.is_loaded or self.movies_df is None:
            return []
        col = "bayesian_rating" if "bayesian_rating" in self.movies_df.columns else "vote_average"
        df = self.movies_df[self.movies_df["vote_count"] >= 50].sort_values(col, ascending=False).head(n)
        return [self._row_to_dict(row) for _, row in df.iterrows()]

    def get_by_mood(self, mood: str, n: int = 15) -> list[dict[str, Any]]:
        """Return films matching psychological mood."""
        if not self.is_loaded or self.movies_df is None:
            return []
        return recommend_by_mood(mood, self.movies_df, n=n)

    def get_by_genre(self, genre: str, n: int = 15) -> list[dict[str, Any]]:
        """Return top films matching a specific genre."""
        if not self.is_loaded or self.movies_df is None:
            return []

        def _has_genre(genres) -> bool:
            if isinstance(genres, (list, tuple, np.ndarray, set)):
                return any(str(g).lower() == genre.lower() for g in genres)
            return str(genre).lower() in str(genres).lower()

        mask = self.movies_df["genres"].apply(_has_genre)
        df = self.movies_df[mask].sort_values("vote_count", ascending=False).head(n)
        return [self._row_to_dict(row) for _, row in df.iterrows()]

    def get_all_genres(self) -> list[str]:
        """Return list of distinct genres present in catalog."""
        if not self.is_loaded or self.movies_df is None:
            return []
        genres_set = set()
        for val in self.movies_df["genres"].dropna():
            if isinstance(val, (list, tuple, np.ndarray, set)):
                for g in val:
                    if g and str(g).strip():
                        genres_set.add(str(g).strip())
            elif isinstance(val, str) and val.strip():
                genres_set.add(val.strip())
        return sorted(list(genres_set))

    def get_all_decades(self) -> list[int]:
        """Return list of available decades in catalog."""
        if not self.is_loaded or self.movies_df is None:
            return []
        if "decade" in self.movies_df.columns:
            decades = self.movies_df["decade"].dropna().unique().astype(int)
            return sorted([d for d in decades if 1920 <= d <= 2030], reverse=True)
        return [2020, 2010, 2000, 1990, 1980, 1970]

    # ── Search & Filter ──────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        genre: str = "All",
        decade: int | None = None,
        runtime_category: str = "All",
        min_rating: float = 0.0,
        sort_by: str = "popularity",
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        """Multi-criteria search with real-time fuzzy title/cast matching."""
        if not self.is_loaded or self.movies_df is None:
            return []

        df = self.movies_df

        # Advanced Search Syntax Parser
        if query and query.strip():
            raw_q = query.strip()
            tokens = raw_q.split()
            remaining_terms = []

            for token in tokens:
                if token.lower().startswith("actor:") or token.lower().startswith("cast:"):
                    act_val = token.split(":", 1)[1].lower()
                    if "cast" in df.columns:
                        df = df[df["cast"].apply(lambda c: any(act_val in str(a).lower() for a in c) if isinstance(c, (list, tuple, np.ndarray)) else act_val in str(c).lower())]
                elif token.lower().startswith("dir:") or token.lower().startswith("director:"):
                    dir_val = token.split(":", 1)[1].lower()
                    if "director" in df.columns:
                        df = df[df["director"].str.lower().str.contains(dir_val, na=False)]
                elif token.lower().startswith("genre:"):
                    g_val = token.split(":", 1)[1].lower()
                    df = df[df["genres"].apply(lambda gs: any(g_val in str(g).lower() for g in gs) if isinstance(gs, (list, tuple, np.ndarray)) else g_val in str(gs).lower())]
                elif token.lower().startswith("year:"):
                    try:
                        y_val = int(token.split(":", 1)[1])
                        df = df[df["year"] == y_val]
                    except ValueError:
                        pass
                elif token.startswith(">20") or token.startswith(">19"):
                    try:
                        y_val = int(token[1:])
                        df = df[df["year"] >= y_val]
                    except ValueError:
                        pass
                elif token.startswith("<20") or token.startswith("<19"):
                    try:
                        y_val = int(token[1:])
                        df = df[df["year"] <= y_val]
                    except ValueError:
                        pass
                elif token.lower().startswith("rating:>"):
                    try:
                        r_val = float(token.split(":>", 1)[1])
                        df = df[df["vote_average"] >= r_val]
                    except ValueError:
                        pass
                else:
                    remaining_terms.append(token)

            if remaining_terms:
                sub_q = " ".join(remaining_terms).lower()
                mask_title = df["title"].str.lower().str.contains(sub_q, na=False)
                mask_dir = df["director"].str.lower().str.contains(sub_q, na=False) if "director" in df.columns else False
                mask_overview = df["overview"].str.lower().str.contains(sub_q, na=False) if "overview" in df.columns else False
                df = df[mask_title | mask_dir | mask_overview]


        # Genre filter
        if genre and genre != "All":
            def _has_genre(genres) -> bool:
                if isinstance(genres, (list, tuple, np.ndarray, set)):
                    return any(str(g).lower() == genre.lower() for g in genres)
                return str(genre).lower() in str(genres).lower()
            df = df[df["genres"].apply(_has_genre)]

        # Decade filter
        if decade is not None and decade > 0 and "decade" in df.columns:
            df = df[df["decade"] == decade]

        # Runtime Category filter
        if runtime_category and runtime_category != "All" and "runtime_category" in df.columns:
            df = df[df["runtime_category"] == runtime_category]

        # Rating filter
        if min_rating > 0.0:
            df = df[df["vote_average"] >= min_rating]

        # Sort Order
        if sort_by == "rating":
            col = "bayesian_rating" if "bayesian_rating" in df.columns else "vote_average"
            df = df.sort_values(col, ascending=False)
        elif sort_by == "year":
            df = df.sort_values("year", ascending=False)
        elif sort_by == "profit" and "profit" in df.columns:
            df = df.sort_values("profit", ascending=False)
        else:  # Popularity / vote count
            df = df.sort_values("vote_count", ascending=False)

        return [self._row_to_dict(row) for _, row in df.head(limit).iterrows()]

    # ── Similar Recommendations & Detail ─────────────────────────────────────

    def get_similar(self, movie_id_or_title: int | str, n: int = 12) -> list[dict[str, Any]]:
        """Return content-based recommendations with MMR and explainable match chips."""
        if not self.is_loaded or self.movies_df is None or self.similarity is None:
            return []
        try:
            return recommend(movie_id_or_title, self.movies_df, self.similarity, n=n, use_mmr=True)
        except Exception as e:
            logger.warning("Failed to generate recommendations for %s: %s", movie_id_or_title, e)
            return []

    def get_movie_by_id(self, movie_id: int) -> dict[str, Any] | None:
        """Fetch movie dictionary by TMDB ID."""
        if not self.is_loaded or self.movies_df is None:
            return None
        rows = self.movies_df[self.movies_df["movie_id"] == movie_id]
        if not rows.empty:
            return self._row_to_dict(rows.iloc[0])
        return None

    # ── Async Dispatch Wrappers ──────────────────────────────────────────────

    def search_async(self, query_params: dict[str, Any], callback: Callable[[list[dict[str, Any]]], None]) -> None:
        """Run search asynchronously and dispatch results to callback on GTK Main Thread."""
        def _worker():
            results = self.search(**query_params)
            GLib.idle_add(callback, results)

        self.executor.submit(_worker)

    def get_similar_async(self, movie_id_or_title: int | str, n: int, callback: Callable[[list[dict[str, Any]]], None]) -> None:
        """Run recommendations asynchronously and dispatch results to callback on GTK Main Thread."""
        def _worker():
            results = self.get_similar(movie_id_or_title, n=n)
            GLib.idle_add(callback, results)

        self.executor.submit(_worker)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _row_to_dict(self, row: pd.Series) -> dict[str, Any]:
        def _to_list(val) -> list[str]:
            if isinstance(val, (list, tuple, np.ndarray, set)):
                return [str(x).strip() for x in val if x is not None and str(x).strip()]
            return []

        poster_path = str(row.get("poster_path", "") or "").strip()
        backdrop_path = str(row.get("backdrop_path", "") or "").strip()

        return {
            "movie_id": int(row["movie_id"]),
            "title": str(row["title"]).strip(),
            "overview": str(row.get("overview", "") or "").strip(),
            "tagline": str(row.get("tagline", "") or "").strip(),
            "genres": _to_list(row.get("genres", [])),
            "moods": _to_list(row.get("moods", [])),
            "year": int(row["year"]) if pd.notna(row.get("year")) and row.get("year") else None,
            "vote_average": float(row.get("vote_average", 0.0)),
            "vote_count": int(row.get("vote_count", 0)),
            "runtime": int(row["runtime"]) if pd.notna(row.get("runtime")) and row.get("runtime") else None,
            "runtime_category": str(row.get("runtime_category", "Feature")),
            "director": str(row.get("director", "") or "").strip(),
            "writer": str(row.get("writer", "") or "").strip(),
            "cast": _to_list(row.get("cast", [])),
            "poster_path": poster_path,
            "backdrop_path": backdrop_path,
            "budget": int(row.get("budget", 0)) if str(row.get("budget", "")).isdigit() else 0,
            "revenue": int(row.get("revenue", 0)) if str(row.get("revenue", "")).isdigit() else 0,
            "profit": float(row.get("profit", 0.0)) if pd.notna(row.get("profit")) else 0.0,
            "roi": float(row.get("roi", 0.0)) if pd.notna(row.get("roi")) else 0.0,
            "bayesian_rating": float(row.get("bayesian_rating", 0.0)) if pd.notna(row.get("bayesian_rating")) else 0.0,
        }


# Global singleton instance
engine = LinuxEngine()
