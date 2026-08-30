"""
src.preprocessing
=================
Comprehensive data pipeline for the movie recommendation system.
Extracts rich metadata (directors, writers, cast, keywords, genres, mood tags, financial stats)
and constructs multi-factor weighted tags for advanced semantic vectorization.
"""

from __future__ import annotations

import ast
import os
import re
import zipfile
from pathlib import Path
from typing import Any
import pandas as pd

# Optional stemming — gracefully skipped if nltk is unavailable
try:
    import nltk
    from nltk.stem.porter import PorterStemmer

    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    _stemmer = PorterStemmer()
    _STEMMING_AVAILABLE = True
except ImportError:  # pragma: no cover
    _STEMMING_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Safe Parsing Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _safe_convert(text: Any) -> list[str]:
    """Safely parse a JSON-like string of ``[{"name": ...}, ...]`` into a list of names."""
    if isinstance(text, list):
        return [str(x["name"]) if isinstance(x, dict) and "name" in x else str(x) for x in text]
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item["name"]) for item in parsed if isinstance(item, dict) and "name" in item]
        return []
    except Exception:
        return []


def _safe_convert_cast(text: Any, top_k: int = 6) -> list[str]:
    """Extract top-k actor names from cast JSON."""
    if isinstance(text, list):
        return [str(x["name"]) if isinstance(x, dict) and "name" in x else str(x) for x in text[:top_k]]
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item["name"]) for item in parsed if isinstance(item, dict) and "name" in item][:top_k]
        return []
    except Exception:
        return []


def _safe_fetch_crew_roles(text: Any) -> tuple[str, str, list[str]]:
    """Extract director, writer/screenplay, and top producers from crew JSON."""
    if not isinstance(text, str) or not text.strip():
        return "", "", []
    try:
        parsed = ast.literal_eval(text)
        if not isinstance(parsed, list):
            return "", "", []
        
        directors = []
        writers = []
        producers = []
        
        for item in parsed:
            if not isinstance(item, dict) or "name" not in item:
                continue
            job = item.get("job", "")
            name = str(item["name"])
            if job == "Director" and name not in directors:
                directors.append(name)
            elif job in ("Writer", "Screenplay", "Author", "Story") and name not in writers:
                writers.append(name)
            elif job in ("Producer", "Executive Producer") and name not in producers:
                producers.append(name)
                
        director_str = ", ".join(directors[:2])
        writer_str = ", ".join(writers[:2])
        return director_str, writer_str, producers[:3]
    except Exception:
        return "", "", []


def _collapse(tokens: list[str]) -> list[str]:
    """Remove spaces within each token so multi-word names become one unified token."""
    return [re.sub(r"[^\w]", "", token.lower()) for token in tokens if token.strip()]


def _stem(text: str) -> str:
    """Lower-case and stem every word in *text* using the Porter stemmer."""
    words = text.split()
    if _STEMMING_AVAILABLE:
        return " ".join(_stemmer.stem(w) for w in words)
    return " ".join(w.lower() for w in words)


def _compute_mood_tags(genres: list[str], keywords: list[str], overview: str) -> list[str]:
    """Classify movie into mood & vibe categories."""
    moods: list[str] = []
    g_set = {g.lower() for g in genres}
    k_set = {k.lower() for k in keywords}
    ov_lower = overview.lower()

    # Mind-Bending / Sci-Fi Vibe
    if "science fiction" in g_set or "mystery" in g_set or any(k in k_set for k in ("time travel", "dystopia", "artificial intelligence", "space", "virtual reality", "mind game")):
        moods.append("mind-bending")
    
    # Dark & Gritty Thriller
    if "thriller" in g_set or "crime" in g_set or "horror" in g_set or any(k in k_set for k in ("serial killer", "dark", "psychological", "conspiracy", "revenge", "murder")):
        moods.append("dark-thriller")

    # Heartwarming / Feel-Good
    if "comedy" in g_set or "animation" in g_set or "family" in g_set or any(k in k_set for k in ("friendship", "coming of age", "feel good", "heartwarming", "dog", "childhood")):
        moods.append("feel-good")

    # Adrenaline & High Octane Action
    if "action" in g_set or "adventure" in g_set or any(k in k_set for k in ("superhero", "explosion", "car chase", "martial arts", "spy", "assassin")):
        moods.append("adrenaline-action")

    # Epic Journey / Fantasy
    if "fantasy" in g_set or ("adventure" in g_set and "history" in g_set) or any(k in k_set for k in ("magic", "sword", "quest", "empire", "kingdom", "mythology")):
        moods.append("epic-journey")

    # Emotional & Romance
    if "romance" in g_set or "drama" in g_set or any(k in k_set for k in ("love story", "relationship", "marriage", "heartbreak", "romantic")):
        moods.append("emotional-drama")

    # Default fallback
    if not moods:
        moods.append("popular-picks")

    return moods


# ─────────────────────────────────────────────────────────────────────────────
# Public Pipeline API
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
    """Run the preprocessing pipeline and return the enriched DataFrame.

    Ensures no duplicate columns, parses full director/writer/cast/genres/keywords/moods,
    and creates weighted semantic tags.
    """
    raw_dir = Path(raw_dir)

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

        # Clean IDs
        movies_raw = movies_raw[movies_raw["id"].astype(str).str.isdigit() == True]
        movies_raw["movie_id"] = movies_raw["id"].astype(int)
        movies_raw = movies_raw.drop(columns=["id"])

        credits_raw["movie_id"] = pd.to_numeric(credits_raw["id"], errors="coerce").dropna().astype(int)
        credits_raw = credits_raw.drop(columns=["id"])

        keywords_raw["movie_id"] = pd.to_numeric(keywords_raw["id"], errors="coerce").dropna().astype(int)
        keywords_raw = keywords_raw.drop(columns=["id"])

        # Merge on movie_id
        movies = movies_raw.merge(credits_raw[["movie_id", "cast", "crew"]], on="movie_id", how="inner")
        movies = movies.merge(keywords_raw[["movie_id", "keywords"]], on="movie_id", how="left")

        movies["vote_count"] = pd.to_numeric(movies["vote_count"], errors="coerce").fillna(0).astype(int)
        movies = movies[movies["vote_count"] >= vote_threshold].reset_index(drop=True)

    else:
        # TMDB 5000
        movies_raw, credits_raw = load_raw_data(raw_dir)
        # Rename id -> movie_id in movies_raw first so there is exactly ONE movie_id column
        movies_raw = movies_raw.rename(columns={"id": "movie_id"})
        # Drop redundant 'title' and 'movie_id' collision by selecting only cast and crew
        credits_clean = credits_raw[["movie_id", "cast", "crew"]]
        movies = movies_raw.merge(credits_clean, on="movie_id", how="inner")

    # Clean & standardize core columns
    for col, default in [
        ("overview", ""),
        ("tagline", ""),
        ("genres", "[]"),
        ("keywords", "[]"),
        ("cast", "[]"),
        ("crew", "[]"),
        ("vote_average", 0.0),
        ("vote_count", 0),
        ("runtime", None),
        ("poster_path", ""),
        ("backdrop_path", ""),
        ("release_date", ""),
        ("budget", 0),
        ("revenue", 0),
    ]:
        if col not in movies.columns:
            movies[col] = default

    # Drop invalid rows & duplicates
    movies = movies.dropna(subset=["movie_id", "title"]).drop_duplicates(subset=["movie_id"]).reset_index(drop=True)
    movies["overview"] = movies["overview"].fillna("").astype(str)
    movies["tagline"] = movies["tagline"].fillna("").astype(str)

    # ── Parse structured features ───────────────────────────────────────────
    movies["genres_list"] = movies["genres"].apply(_safe_convert)
    movies["keywords_list"] = movies["keywords"].apply(_safe_convert)
    movies["cast_list"] = movies["cast"].apply(lambda c: _safe_convert_cast(c, top_k=6))
    
    # Extract director, writer, producers
    crew_tuples = movies["crew"].apply(_safe_fetch_crew_roles)
    movies["director"] = [t[0] for t in crew_tuples]
    movies["writer"] = [t[1] for t in crew_tuples]
    movies["producers"] = [t[2] for t in crew_tuples]

    # Mood classification
    movies["moods"] = [
        _compute_mood_tags(g, k, ov)
        for g, k, ov in zip(movies["genres_list"], movies["keywords_list"], movies["overview"])
    ]

    # Extract year
    def _extract_year(row) -> int | None:
        rel = str(row.get("release_date", "") or "")
        if len(rel) >= 4 and rel[:4].isdigit():
            return int(rel[:4])
        match = re.search(r"\((\d{4})\)$", str(row.get("title", "")))
        return int(match.group(1)) if match else None

    movies["year"] = movies.apply(_extract_year, axis=1)

    # ── Multi-Factor Weighted Tag Generation ─────────────────────────────────
    # Sub-field weighting:
    #   Director: repeated 3x (strong stylistic signal)
    #   Genres: repeated 2x
    #   Keywords: repeated 2x
    #   Top 3 Cast: repeated 2x
    #   Overview + Tagline: 1x
    def _build_weighted_tag_string(row) -> str:
        genres_col = _collapse(row["genres_list"])
        kw_col = _collapse(row["keywords_list"])
        cast_col = _collapse(row["cast_list"][:4])
        director_col = _collapse([d for d in str(row["director"]).split(", ") if d.strip()])
        writer_col = _collapse([w for w in str(row["writer"]).split(", ") if w.strip()])

        # Weighted repeats
        tokens = (
            director_col * 3
            + writer_col * 2
            + genres_col * 2
            + kw_col * 2
            + cast_col * 2
            + row["overview"].split()
            + row["tagline"].split()
        )
        return " ".join(tokens).lower()

    movies["tags"] = movies.apply(_build_weighted_tag_string, axis=1)
    movies["tags"] = movies["tags"].apply(_stem)

    # Finalize columns
    movies["genres"] = movies["genres_list"]
    movies["keywords"] = movies["keywords_list"]
    movies["cast"] = movies["cast_list"]

    # Select clean output columns
    keep_cols = [
        "movie_id",
        "title",
        "overview",
        "tagline",
        "genres",
        "keywords",
        "cast",
        "director",
        "writer",
        "producers",
        "moods",
        "year",
        "vote_average",
        "vote_count",
        "runtime",
        "poster_path",
        "backdrop_path",
        "release_date",
        "budget",
        "revenue",
        "tags",
    ]
    # Filter only available columns
    keep_cols = [c for c in keep_cols if c in movies.columns]
    final_df = movies[keep_cols].copy()

    return final_df
