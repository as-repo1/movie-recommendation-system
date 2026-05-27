"""
src.preprocessing
=================
Full data pipeline for the movie recommendation system.

Steps
-----
1. Load raw CSVs from the ``data/raw/`` directory (unzipped).
2. Merge movies + credits on ``title``.
3. Extract genres, keywords, top-3 cast, and director.
4. Collapse multi-word names so they become single tokens.
5. Combine all features into a single ``tags`` string per movie.
6. Lower-case and stem every tag word (Porter stemmer).

Public API
----------
build_tags_dataframe(raw_dir)  →  pd.DataFrame  (columns: movie_id, title, tags)
"""

from __future__ import annotations

import ast
import os
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
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _convert(text: str) -> list[str]:
    """Parse a JSON-like string of ``[{"name": ...}, ...]`` into a list of names."""
    return [item["name"] for item in ast.literal_eval(text)]


def _convert_top3(text: str) -> list[str]:
    """Like ``_convert`` but only returns the first three entries."""
    return [item["name"] for item in ast.literal_eval(text)][:3]


def _fetch_director(text: str) -> list[str]:
    """Return a list containing the director's name (or empty if none listed)."""
    return [
        item["name"]
        for item in ast.literal_eval(text)
        if item.get("job") == "Director"
    ]


def _collapse(tokens: list[str]) -> list[str]:
    """Remove spaces within each token so multi-word names become one token.

    Example: ``"Sam Worthington"`` → ``"SamWorthington"``
    This prevents the vectoriser from splitting names into common first/last
    name fragments.
    """
    return [token.replace(" ", "") for token in tokens]


def _stem(text: str) -> str:
    """Lower-case and stem every word in *text* using the Porter stemmer.

    Falls back to plain lower-casing if nltk is not installed.
    """
    words = text.split()
    if _STEMMING_AVAILABLE:
        return " ".join(_stemmer.stem(w) for w in words)
    return " ".join(w.lower() for w in words)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def load_raw_data(raw_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two TMDB CSV files from *raw_dir*.

    Parameters
    ----------
    raw_dir:
        Directory containing ``tmdb_5000_movies.csv`` and
        ``tmdb_5000_credits.csv``.

    Returns
    -------
    (movies_df, credits_df)
    """
    raw_dir = Path(raw_dir)
    movies_path = raw_dir / "tmdb_5000_movies.csv"
    credits_path = raw_dir / "tmdb_5000_credits.csv"

    for path in (movies_path, credits_path):
        if not path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {path}\n"
                "Please unzip the dataset archives inside data/raw/ first:\n"
                "  cd data/raw && unzip tmdb_5000_movies.csv.zip && unzip tmdb_5000_credits.csv.zip"
            )

    movies_df = pd.read_csv(movies_path)
    credits_df = pd.read_csv(credits_path)
    return movies_df, credits_df


def build_tags_dataframe(raw_dir: str | Path) -> pd.DataFrame:
    """Run the full preprocessing pipeline and return the tags DataFrame.

    Parameters
    ----------
    raw_dir:
        Directory containing ``tmdb_5000_movies.csv`` and
        ``tmdb_5000_credits.csv`` (unzipped).

    Returns
    -------
    pd.DataFrame with columns ``movie_id``, ``title``, ``tags``.
    """
    movies_raw, credits_raw = load_raw_data(raw_dir)

    # Merge & select relevant columns
    movies = movies_raw.merge(credits_raw, on="title")
    movies = movies[["movie_id", "title", "overview", "genres", "keywords", "cast", "crew"]]

    # Drop rows with any missing value
    movies = movies.dropna().drop_duplicates().reset_index(drop=True)

    # ── Feature extraction ──────────────────────────────────────────────────
    movies["genres"]   = movies["genres"].apply(_convert)
    movies["keywords"] = movies["keywords"].apply(_convert)
    movies["cast"]     = movies["cast"].apply(_convert_top3)   # top 3 actors only
    movies["crew"]     = movies["crew"].apply(_fetch_director)  # director only

    # ── Collapse multi-word names into single tokens ────────────────────────
    for col in ("genres", "keywords", "cast", "crew"):
        movies[col] = movies[col].apply(_collapse)

    # ── Split overview into tokens (list of words) ──────────────────────────
    movies["overview"] = movies["overview"].apply(str.split)

    # ── Combine all features into a single tags string ──────────────────────
    movies["tags"] = (
        movies["overview"]
        + movies["genres"]
        + movies["keywords"]
        + movies["cast"]
        + movies["crew"]
    )

    # ── Build final slim DataFrame ──────────────────────────────────────────
    result = movies[["movie_id", "title", "tags"]].copy()
    result["tags"] = result["tags"].apply(lambda tokens: " ".join(tokens).lower())

    # ── Stem every word ─────────────────────────────────────────────────────
    result["tags"] = result["tags"].apply(_stem)

    return result
