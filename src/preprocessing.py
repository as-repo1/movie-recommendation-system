"""
src.preprocessing
=================
Full data pipeline for the movie recommendation system.

Supports both TMDB 5000 and the expanded Kaggle Movies Dataset.
"""

from __future__ import annotations

import ast
import os
import zipfile
from pathlib import Path
import pandas as pd

# Optional stemming — gracefully skipped if nltk is unavailable
try:
    import nltk
    from nltk.stem.porter import PorterStemmer

    nltk.download("punkt", quiet=True)
    _stemmer = PorterStemmer()
    _STEMMING_AVAILABLE = True
except ImportError:  # pragma: no cover
    _STEMMING_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Safe private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _safe_convert(text: str) -> list[str]:
    """Safely parse a JSON-like string of ``[{"name": ...}, ...]`` into a list of names."""
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [item["name"] for item in parsed if isinstance(item, dict) and "name" in item]
        return []
    except Exception:
        return []


def _safe_convert_top3(text: str) -> list[str]:
    """Like ``_safe_convert`` but only returns the first three entries."""
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [item["name"] for item in parsed if isinstance(item, dict) and "name" in item][:3]
        return []
    except Exception:
        return []


def _safe_fetch_director(text: str) -> list[str]:
    """Return a list containing the director's name (or empty if none listed)."""
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [
                item["name"]
                for item in parsed
                if isinstance(item, dict) and item.get("job") == "Director" and "name" in item
            ]
        return []
    except Exception:
        return []


def _collapse(tokens: list[str]) -> list[str]:
    """Remove spaces within each token so multi-word names become one token."""
    return [token.replace(" ", "") for token in tokens]


def _stem(text: str) -> str:
    """Lower-case and stem every word in *text* using the Porter stemmer."""
    words = text.split()
    if _STEMMING_AVAILABLE:
        return " ".join(_stemmer.stem(w) for w in words)
    return " ".join(w.lower() for w in words)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def load_raw_data(raw_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two TMDB CSV files from *raw_dir*."""
    raw_dir = Path(raw_dir)
    movies_path = raw_dir / "tmdb_5000_movies.csv"
    credits_path = raw_dir / "tmdb_5000_credits.csv"

    for path in (movies_path, credits_path):
        if not path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {path}\n"
                "Please unzip the dataset archives inside data/raw/ first."
            )

    movies_df = pd.read_csv(movies_path)
    credits_df = pd.read_csv(credits_path)
    return movies_df, credits_df


def build_tags_dataframe(
    raw_dir: str | Path,
    dataset: str = "tmdb5000",
    archive_path: str | Path | None = None,
    vote_threshold: int = 30,
) -> pd.DataFrame:
    """Run the preprocessing pipeline and return the tags DataFrame with enriched metadata.

    Parameters
    ----------
    raw_dir:
        Directory containing the fallback TMDB 5000 files.
    dataset:
        "tmdb5000" or "kaggle".
    archive_path:
        Path to more-datasets/archive.zip.
    vote_threshold:
        Min vote count to filter Kaggle movies.
    """
    if dataset == "kaggle":
        if archive_path is None:
            raise ValueError("archive_path must be specified for 'kaggle' dataset.")
        archive_path = Path(archive_path)
        if not archive_path.exists():
            raise FileNotFoundError(f"Kaggle archive zip not found at {archive_path}")

        print(f"[INFO]  Loading Kaggle dataset from {archive_path.name} ...")
        with zipfile.ZipFile(archive_path) as z:
            with z.open("movies_metadata.csv") as f:
                movies_raw = pd.read_csv(f, low_memory=False)
            with z.open("credits.csv") as f:
                credits_raw = pd.read_csv(f)
            with z.open("keywords.csv") as f:
                keywords_raw = pd.read_csv(f)

        # Clean corrupted IDs
        movies_raw = movies_raw[movies_raw["id"].str.isdigit() == True]
        movies_raw["id"] = movies_raw["id"].astype(int)

        credits_raw["id"] = pd.to_numeric(credits_raw["id"], errors="coerce")
        credits_raw = credits_raw.dropna(subset=["id"])
        credits_raw["id"] = credits_raw["id"].astype(int)

        keywords_raw["id"] = pd.to_numeric(keywords_raw["id"], errors="coerce")
        keywords_raw = keywords_raw.dropna(subset=["id"])
        keywords_raw["id"] = keywords_raw["id"].astype(int)

        # Merge on ID
        movies = movies_raw.merge(credits_raw, on="id").merge(keywords_raw, on="id")
        movies = movies.rename(columns={"id": "movie_id"})

        # Clean vote counts & filter
        movies["vote_count"] = pd.to_numeric(movies["vote_count"], errors="coerce").fillna(0).astype(int)
        movies = movies[movies["vote_count"] >= vote_threshold].reset_index(drop=True)

    else:
        # Fallback tmdb5000
        movies_raw, credits_raw = load_raw_data(raw_dir)
        movies = movies_raw.merge(credits_raw, on="title")
        movies = movies.rename(columns={"id": "movie_id"})

    # Ensure metadata columns exist
    meta_cols = [
        "movie_id",
        "title",
        "overview",
        "genres",
        "keywords",
        "cast",
        "crew",
        "vote_average",
        "vote_count",
        "runtime",
        "poster_path",
        "release_date",
    ]
    for c in meta_cols:
        if c not in movies.columns:
            movies[c] = ""

    movies = movies[meta_cols]
    # Drop rows missing crucial search features
    movies = movies.dropna(subset=["movie_id", "title", "overview"]).drop_duplicates(subset=["movie_id"]).reset_index(drop=True)

    # ── Feature extraction & parsing ────────────────────────────────────────
    movies["genres_list"] = movies["genres"].apply(_safe_convert)
    movies["keywords_list"] = movies["keywords"].apply(_safe_convert)
    movies["cast_list"] = movies["cast"].apply(_safe_convert_top3)
    movies["crew_list"] = movies["crew"].apply(_safe_fetch_director)

    # ── Collapse tokens ─────────────────────────────────────────────────────
    genres_collapsed = movies["genres_list"].apply(_collapse)
    keywords_collapsed = movies["keywords_list"].apply(_collapse)
    cast_collapsed = movies["cast_list"].apply(_collapse)
    crew_collapsed = movies["crew_list"].apply(_collapse)
    overview_tokens = movies["overview"].apply(str.split)

    # ── Combine tags ────────────────────────────────────────────────────────
    movies["tags"] = (
        overview_tokens
        + genres_collapsed
        + keywords_collapsed
        + cast_collapsed
        + crew_collapsed
    )

    # ── Build final enriched DataFrame ──────────────────────────────────────
    movies["tags"] = movies["tags"].apply(lambda tokens: " ".join(tokens).lower())
    movies["tags"] = movies["tags"].apply(_stem)

    # Clean genres column to store as list of strings directly
    movies["genres"] = movies["genres_list"]

    # Drop intermediate columns
    movies = movies.drop(columns=["genres_list", "keywords_list", "cast_list", "crew_list"])

    return movies
