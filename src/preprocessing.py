"""
src.preprocessing
=================
Comprehensive data cleaning, text sanitization, and preprocessing pipeline.

Supports:
- TMDB 5000 Movies & Credits dataset
- Alan Vourch's TMDB Movies Daily Updates (1.2M+ Dataset)
- Kaggle The Movies Dataset

Features:
- Multi-key deduplication (ID, IMDb ID, Canonical Title + Year)
- Text sanitization (HTML entity stripping, unicode normalization, punctuation cleaning)
- Multi-factor sub-field weighted token generation
- Psychological mood classification taxonomy
- Pre-calculated Bayesian weighted rating quality priors
"""

from __future__ import annotations

import ast
import html
import os
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
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
# Text Sanitization & Cleaning Helpers
# ─────────────────────────────────────────────────────────────────────────────


def sanitize_text(text: Any) -> str:
    """Clean HTML tags, decode HTML entities, strip unprintable chars, and normalize spaces."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    s = str(text).strip()
    if not s or s.lower() in ("nan", "none", "null", "n/a"):
        return ""

    # Unescape HTML entities (e.g. &amp; -> &, &quot; -> ")
    s = html.unescape(s)
    # Strip HTML tags
    s = re.sub(r"<[^>]+>", " ", s)
    # Normalize unicode to NFKC
    s = unicodedata.normalize("NFKC", s)
    # Remove control characters
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", s)
    # Normalize excess whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_ascii_tokens(text: str) -> str:
    """Normalize accents for robust token matching (e.g. 'Ménage' -> 'Menage')."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def _parse_delimited_or_json(text: Any, top_k: int | None = None) -> list[str]:
    """Safely parse comma/pipe-separated strings, JSON lists of dicts, or Python lists into clean string lists."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return []
    if isinstance(text, list):
        items = [sanitize_text(x.get("name", x) if isinstance(x, dict) else x) for x in text]
        return [i for i in items if i][:top_k]

    if not isinstance(text, str) or not text.strip():
        return []

    cleaned = sanitize_text(text)
    if not cleaned or cleaned.lower() in ("none", "nan", "[]", "{}"):
        return []

    # Try JSON / AST evaluation for '[{"name": ...}, ...]' or '["Action", ...]'
    if (cleaned.startswith("[") and cleaned.endswith("]")) or (cleaned.startswith("{") and cleaned.endswith("}")):
        try:
            parsed = ast.literal_eval(cleaned)
            if isinstance(parsed, list):
                out = []
                for item in parsed:
                    if isinstance(item, dict):
                        name = sanitize_text(item.get("name") or item.get("title") or "")
                        if name:
                            out.append(name)
                    elif item:
                        san = sanitize_text(item)
                        if san:
                            out.append(san)
                return out[:top_k]
            elif isinstance(parsed, dict) and "name" in parsed:
                san = sanitize_text(parsed["name"])
                return [san] if san else []
        except Exception:
            pass

    # Delimited string format: "Action, Adventure, Science Fiction" or "Action|Adventure"
    for delim in [",", "|", "/"]:
        if delim in cleaned:
            parts = [sanitize_text(p) for p in cleaned.split(delim)]
            valid = [p for p in parts if p and p.lower() not in ("none", "nan", "null", "n/a")]
            if valid:
                return valid[:top_k]

    # Single value string
    if cleaned and cleaned.lower() not in ("none", "nan", "[]", "{}"):
        return [cleaned]

    return []


def _safe_convert(text: Any) -> list[str]:
    """Safely parse a JSON-like string or delimited list into string tokens."""
    return _parse_delimited_or_json(text)


def _safe_convert_cast(text: Any, top_k: int = 6) -> list[str]:
    """Extract top-k actor names from cast JSON or comma-separated string."""
    return _parse_delimited_or_json(text, top_k=top_k)


def _safe_fetch_crew_roles(text: Any) -> tuple[str, str, list[str]]:
    """Extract director, writer/screenplay, and top producers from crew JSON."""
    if not isinstance(text, str) or not text.strip():
        return "", "", []
    try:
        parsed = ast.literal_eval(text)
        if not isinstance(parsed, list):
            return "", "", []
        director, writer = "", ""
        producers = []
        for member in parsed:
            if not isinstance(member, dict):
                continue
            job = member.get("job", "")
            name = sanitize_text(member.get("name", ""))
            if not name:
                continue
            if job == "Director" and not director:
                director = name
            elif job in ("Writer", "Screenplay") and not writer:
                writer = name
            elif job in ("Producer", "Executive Producer") and len(producers) < 4:
                producers.append(name)
        return director, writer, producers
    except Exception:
        return "", "", []


def _collapse(elements: list[str]) -> list[str]:
    """Remove spaces inside multi-word names to treat them as single tokens (e.g. 'Tom Hanks' -> 'tomhanks')."""
    return [
        clean_ascii_tokens(elem).replace(" ", "").replace("-", "").replace(".", "").replace("'", "").lower()
        for elem in elements
        if elem
    ]


def _stem(text: str) -> str:
    """Apply Porter Stemmer to every word in *text*."""
    if not _STEMMING_AVAILABLE or not text:
        return text
    return " ".join(_stemmer.stem(word) for word in text.split())


# ─────────────────────────────────────────────────────────────────────────────
# Mood / Vibe Classifier Taxonomy
# ─────────────────────────────────────────────────────────────────────────────

MOOD_DEFINITIONS: dict[str, dict[str, set[str]]] = {
    "mind-bending": {
        "genres": {"science fiction", "mystery"},
        "keywords": {
            "time travel", "space", "simulation", "matrix", "artificial intelligence",
            "dystopia", "parallel world", "alien", "dimension", "mind", "memory", "quantum",
            "philosophical", "twist", "psychological", "conspiracy", "virtual reality", "wormhole"
        },
    },
    "dark-thriller": {
        "genres": {"crime", "thriller", "mystery", "horror"},
        "keywords": {
            "serial killer", "investigation", "detective", "murder", "noir", "hostage",
            "betrayal", "undercover", "dark", "gritty", "assassin", "revenge", "mafia",
            "police", "corruption", "psychopath", "terror", "gangster", "heist"
        },
    },
    "feel-good": {
        "genres": {"comedy", "animation", "family"},
        "keywords": {
            "friendship", "holiday", "heartwarming", "dog", "magic", "parody", "satire",
            "coming of age", "romance", "cheerful", "uplifting", "musical", "humor", "cute", "school"
        },
    },
    "adrenaline-action": {
        "genres": {"action", "adventure"},
        "keywords": {
            "superhero", "explosion", "chase", "martial arts", "car chase", "heist",
            "gunfight", "special forces", "warfare", "mercenary", "race", "combat", "survival", "spy"
        },
    },
    "epic-journey": {
        "genres": {"fantasy", "adventure"},
        "keywords": {
            "quest", "magic", "sword", "dragon", "kingdom", "medieval", "mythology",
            "expedition", "journey", "treasure", "island", "destiny", "prophecy", "empire", "space opera"
        },
    },
    "emotional-drama": {
        "genres": {"drama", "romance"},
        "keywords": {
            "love", "relationship", "marriage", "divorce", "loss", "tragedy", "illness",
            "biography", "historical", "struggle", "family drama", "tearjerker", "passion", "courtroom"
        },
    },
}


def _compute_mood_tags(
    genres: list[str],
    keywords: list[str],
    overview: str = "",
) -> list[str]:
    """Assign structured mood/vibe labels based on genres, keywords, and synopsis."""
    norm_genres = {g.lower().strip() for g in genres}
    norm_keywords = {k.lower().strip() for k in keywords}
    norm_overview = overview.lower() if overview else ""

    assigned: list[str] = []
    for mood_name, rules in MOOD_DEFINITIONS.items():
        score = 0
        genre_matches = norm_genres & rules["genres"]
        score += len(genre_matches) * 2

        for kw in rules["keywords"]:
            if kw in norm_keywords or kw in norm_overview:
                score += 1

        if score >= 2 or (genre_matches and score >= 1):
            assigned.append(mood_name)

    return assigned


# ─────────────────────────────────────────────────────────────────────────────
# Quality Priors & Enrichment Helpers
# ─────────────────────────────────────────────────────────────────────────────


def calculate_bayesian_rating(
    df: pd.DataFrame,
    min_votes_quantile: float = 0.60,
) -> pd.Series:
    """Compute precalculated Bayesian weighted ratings (IMDb formula).

    WR = (v / (v + m)) * R + (m / (v + m)) * C
    """
    if "vote_count" not in df.columns or "vote_average" not in df.columns or df.empty:
        return pd.Series(np.zeros(len(df)), index=df.index, dtype=float)

    v = pd.to_numeric(df["vote_count"], errors="coerce").fillna(0).values
    R = pd.to_numeric(df["vote_average"], errors="coerce").fillna(0.0).values

    valid_mask = v > 0
    if valid_mask.any():
        m = float(np.quantile(v[valid_mask], min_votes_quantile))
        C = float(np.mean(R[valid_mask]))
    else:
        m, C = 50.0, 6.0

    denom = v + m
    denom[denom == 0] = 1.0
    wr = (v / denom) * R + (m / denom) * C
    return pd.Series(np.clip(wr, 0.0, 10.0), index=df.index, dtype=float)


def classify_runtime(runtime: Any) -> str:
    """Classify runtime into Short (<45m), Feature (45-150m), or Epic (>150m)."""
    if runtime is None or pd.isna(runtime):
        return "Feature"
    try:
        r = float(runtime)
        if r < 45:
            return "Short"
        elif r <= 150:
            return "Feature"
        else:
            return "Epic"
    except (ValueError, TypeError):
        return "Feature"


# ─────────────────────────────────────────────────────────────────────────────
# Data Cleaning & Normalization Pipeline
# ─────────────────────────────────────────────────────────────────────────────

_PLACEHOLDER_TITLES = {
    "untitled",
    "untitled project",
    "test",
    "test movie",
    "null",
    "none",
    "nan",
    "n/a",
    "unknown",
    "tbd",
    "tba",
}


def clean_raw_dataframe(
    raw_df: pd.DataFrame,
    min_votes: int = 15,
    min_overview_len: int = 15,
    drop_adult: bool = True,
    released_only: bool = True,
) -> pd.DataFrame:
    """Execute end-to-end data cleaning, sanitization, multi-key deduplication, and enrichment.

    1. Deduplication on numeric IDs, IMDb IDs, and (normalized_title, release_year) collisions.
    2. Status & content validation (non-adult, released, valid synopsis, non-placeholder title).
    3. Text sanitization across all string fields (HTML unescaping, unicode NFKC normalization).
    4. Casting numeric types and extracting year, decade, runtime classification, and profit metrics.
    """
    df = raw_df.copy()
    print(f"[INFO]  Starting enterprise data cleaning on {len(df):,} raw records...")

    # Standardize ID column
    id_col = "id" if "id" in df.columns else "movie_id"
    df = df[pd.to_numeric(df[id_col], errors="coerce").notna()]
    df["movie_id"] = df[id_col].astype(int)

    # 1. Deduplicate by primary movie_id
    df = df.drop_duplicates(subset=["movie_id"]).reset_index(drop=True)

    # 2. Filter adult content
    if drop_adult and "adult" in df.columns:
        df = df[df["adult"].astype(str).str.lower().isin(["false", "0", "nan", "", "none"])]

    # 3. Filter status
    if released_only and "status" in df.columns:
        status_s = df["status"].fillna("").astype(str).str.strip().str.lower()
        # Accept 'released', 'post production', or empty status if vote_count > 0
        valid_status = status_s.isin(["released", "post production", ""])
        # Reject explicitly cancelled / rumored / planned
        invalid_status = status_s.isin(["canceled", "cancelled", "rumored", "planned"])
        df = df[valid_status & ~invalid_status]

    # 4. Clean vote_count & vote_average
    if "vote_count" in df.columns:
        df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce").fillna(0).astype(int)
        if min_votes > 0:
            df = df[df["vote_count"] >= min_votes]

    if "vote_average" in df.columns:
        df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce").fillna(0.0).astype(float)
        df["vote_average"] = df["vote_average"].clip(0.0, 10.0)

    # 5. Sanitize Text Columns
    for col in ["title", "overview", "tagline", "original_title"]:
        if col in df.columns:
            df[col] = df[col].apply(sanitize_text)

    # Filter out empty or placeholder titles
    if "title" in df.columns:
        df["_title_check"] = df["title"].astype(str).str.strip().str.lower()
        has_alphanumeric = df["_title_check"].apply(lambda t: any(c.isalnum() for c in str(t)))
        valid_title_mask = (
            (df["_title_check"].str.len() > 0)
            & (~df["_title_check"].isin(_PLACEHOLDER_TITLES))
            & has_alphanumeric
        )
        df = df[valid_title_mask].drop(columns=["_title_check"])


    # Filter out empty or short placeholder overviews
    if min_overview_len > 0 and "overview" in df.columns:
        df = df[df["overview"].str.len() >= min_overview_len]

    # 6. Extract Release Year & Decade
    def _extract_year(val: Any, title_val: Any) -> int | None:
        rel = str(val or "").strip()
        if len(rel) >= 4 and rel[:4].isdigit():
            y = int(rel[:4])
            if 1880 <= y <= 2035:
                return y
        m = re.search(r"\((\d{4})\)$", str(title_val or ""))
        if m:
            y = int(m.group(1))
            if 1880 <= y <= 2035:
                return y
        return None

    rel_col = df["release_date"] if "release_date" in df.columns else pd.Series([""] * len(df))
    df["year"] = [_extract_year(r, t) for r, t in zip(rel_col, df["title"])]
    df["decade"] = [(y // 10 * 10) if y is not None else None for y in df["year"]]

    # 7. Deduplication by IMDb ID (if present and valid)
    if "imdb_id" in df.columns:
        df["imdb_id"] = df["imdb_id"].fillna("").astype(str).str.strip()
        has_imdb = df["imdb_id"].str.startswith("tt")
        imdb_unique = df[has_imdb].sort_values(by=["vote_count", "vote_average"], ascending=[False, False])
        imdb_unique = imdb_unique.drop_duplicates(subset=["imdb_id"])
        no_imdb = df[~has_imdb]
        df = pd.concat([imdb_unique, no_imdb], ignore_index=True)

    # 8. Tertiary Deduplication on canonical (normalized_title, year)
    df["_title_norm"] = df["title"].apply(clean_ascii_tokens).str.lower().str.strip()
    df = df.sort_values(by=["vote_count", "vote_average"], ascending=[False, False])
    df = df.drop_duplicates(subset=["_title_norm", "year"]).reset_index(drop=True)
    df = df.drop(columns=["_title_norm"], errors="ignore")

    # 9. Sanitize numeric financial attributes & calculate Profit/ROI
    for num_col in ["budget", "revenue"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(0).astype(int)
        else:
            df[num_col] = 0

    # Calculate financial profit (revenue - budget)
    if "revenue" in df.columns and "budget" in df.columns:
        has_financials = (df["revenue"] > 0) & (df["budget"] > 0)
        df["profit"] = np.where(has_financials, df["revenue"] - df["budget"], 0)
        df["is_profitable"] = np.where(has_financials, df["profit"] > 0, None)
        df["roi"] = np.where(
            (df["budget"] >= 100_000) & (df["revenue"] > 0),
            ((df["revenue"] - df["budget"]) / df["budget"]).round(2),
            None,
        )
    else:
        df["profit"] = 0
        df["is_profitable"] = None
        df["roi"] = None

    # 10. Runtime validation and classification
    if "runtime" in df.columns:
        df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce").fillna(0).astype(int)
        df.loc[(df["runtime"] < 10) | (df["runtime"] > 600), "runtime"] = None
    else:
        df["runtime"] = None

    df["runtime_category"] = df["runtime"].apply(classify_runtime)

    # 11. Precomputed Bayesian Weighted Rating
    df["bayesian_rating"] = calculate_bayesian_rating(df).round(2)

    print(f"[INFO]  Cleaning complete: {len(df):,} high-quality valid movies retained.")
    return df.reset_index(drop=True)


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


def _load_tmdb_daily_file(source_path: Path) -> pd.DataFrame:
    """Load Alan Vourch's TMDB Daily Updates CSV or ZIP file."""
    if source_path.suffix == ".zip":
        with zipfile.ZipFile(source_path) as z:
            csv_names = [n for n in z.namelist() if n.endswith(".csv") and not n.startswith("__MACOSX")]
            if not csv_names:
                raise ValueError(f"No CSV file found inside {source_path.name}")
            target_name = next((n for n in csv_names if "movie" in n.lower()), csv_names[0])
            print(f"[INFO]  Reading {target_name} from {source_path.name} ...")
            with z.open(target_name) as f:
                return pd.read_csv(f, low_memory=False)
    else:
        print(f"[INFO]  Reading {source_path.name} ...")
        return pd.read_csv(source_path, low_memory=False)


def build_tags_dataframe(
    raw_dir: str | Path,
    dataset: str = "auto",
    archive_path: str | Path | None = None,
    vote_threshold: int = 15,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Run the comprehensive cleaning and preprocessing pipeline.

    Produces an enriched, clean DataFrame ready for portable TF-IDF indexing.
    """
    raw_dir = Path(raw_dir)

    # ── Auto detection ────────────────────────────────────────────────────────
    if dataset == "auto":
        if archive_path and Path(archive_path).exists():
            p = Path(archive_path)
            if "daily" in p.name.lower() or "tmdb_movie" in p.name.lower() or "all_movies" in p.name.lower():
                dataset = "tmdb_daily"
            else:
                dataset = "kaggle"
        else:
            daily_candidates = (
                list(raw_dir.glob("TMDB_all_movies*.csv"))
                + list(raw_dir.glob("TMDB_movie*.csv"))
                + list(raw_dir.glob("*tmdb*daily*.zip"))
            )
            if daily_candidates:
                dataset = "tmdb_daily"
                archive_path = daily_candidates[0]
            elif (raw_dir / "tmdb_5000_movies.csv").exists():
                dataset = "tmdb5000"
            else:
                dataset = "tmdb5000"

    print(f"[INFO]  Running preprocessing pipeline using '{dataset}' dataset mode...")

    if dataset == "tmdb_daily":
        source_path = Path(archive_path) if archive_path else raw_dir / "TMDB_all_movies.csv"
        if not source_path.exists():
            candidates = (
                list(raw_dir.glob("TMDB_all_movies*.csv"))
                + list(raw_dir.glob("TMDB_movie*.csv"))
                + list(raw_dir.glob("*tmdb*daily*.zip"))
            )
            if candidates:
                source_path = candidates[0]
            else:
                raise FileNotFoundError(f"TMDB Daily dataset not found at {source_path}")

        raw_df = _load_tmdb_daily_file(source_path)
        # Apply full cleaning pipeline
        clean_df = clean_raw_dataframe(raw_df, min_votes=vote_threshold)

        # Standardize director / writer / cast
        if "director" not in clean_df.columns and "crew" in clean_df.columns:
            crew_tuples = clean_df["crew"].apply(_safe_fetch_crew_roles)
            clean_df["director"] = [t[0] for t in crew_tuples]
            clean_df["writer"] = [t[1] for t in crew_tuples]
            clean_df["producers"] = [t[2] for t in crew_tuples]
        else:
            if "director" not in clean_df.columns:
                clean_df["director"] = ""
            if "writers" in clean_df.columns and "writer" not in clean_df.columns:
                clean_df["writer"] = clean_df["writers"].fillna("").astype(str)
            elif "writer" not in clean_df.columns:
                clean_df["writer"] = ""
            if "producers" not in clean_df.columns:
                clean_df["producers"] = [[] for _ in range(len(clean_df))]

        clean_df["genres_list"] = clean_df["genres"].apply(_safe_convert) if "genres" in clean_df.columns else [[] for _ in range(len(clean_df))]
        clean_df["keywords_list"] = clean_df["keywords"].apply(_safe_convert) if "keywords" in clean_df.columns else [[] for _ in range(len(clean_df))]
        clean_df["cast_list"] = clean_df["cast"].apply(lambda c: _safe_convert_cast(c, top_k=6)) if "cast" in clean_df.columns else [[] for _ in range(len(clean_df))]

        movies = clean_df

    elif dataset == "kaggle":
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

        movies_raw = clean_raw_dataframe(movies_raw, min_votes=vote_threshold)
        credits_raw["movie_id"] = pd.to_numeric(credits_raw["id"], errors="coerce").dropna().astype(int)
        keywords_raw["movie_id"] = pd.to_numeric(keywords_raw["id"], errors="coerce").dropna().astype(int)

        movies = movies_raw.merge(credits_raw[["movie_id", "cast", "crew"]], on="movie_id", how="inner")
        movies = movies.merge(keywords_raw[["movie_id", "keywords"]], on="movie_id", how="left")

        movies["genres_list"] = movies["genres"].apply(_safe_convert)
        movies["keywords_list"] = movies["keywords"].apply(_safe_convert)
        movies["cast_list"] = movies["cast"].apply(lambda c: _safe_convert_cast(c, top_k=6))
        crew_tuples = movies["crew"].apply(_safe_fetch_crew_roles)
        movies["director"] = [t[0] for t in crew_tuples]
        movies["writer"] = [t[1] for t in crew_tuples]
        movies["producers"] = [t[2] for t in crew_tuples]

    else:
        # TMDB 5000
        movies_raw, credits_raw = load_raw_data(raw_dir)
        movies_raw = clean_raw_dataframe(movies_raw, min_votes=0)
        credits_clean = credits_raw[["movie_id", "cast", "crew"]]
        movies = movies_raw.merge(credits_clean, on="movie_id", how="inner")

        movies["genres_list"] = movies["genres"].apply(_safe_convert)
        movies["keywords_list"] = movies["keywords"].apply(_safe_convert)
        movies["cast_list"] = movies["cast"].apply(lambda c: _safe_convert_cast(c, top_k=6))
        crew_tuples = movies["crew"].apply(_safe_fetch_crew_roles)
        movies["director"] = [t[0] for t in crew_tuples]
        movies["writer"] = [t[1] for t in crew_tuples]
        movies["producers"] = [t[2] for t in crew_tuples]

    # Mood classification
    movies["moods"] = [
        _compute_mood_tags(g, k, ov)
        for g, k, ov in zip(movies["genres_list"], movies["keywords_list"], movies["overview"])
    ]

    # ── Multi-Factor Weighted Tag Generation ─────────────────────────────────
    def _build_weighted_tag_string(row) -> str:
        genres_col = _collapse(row["genres_list"])
        kw_col = _collapse(row["keywords_list"])
        cast_col = _collapse(row["cast_list"][:4])
        director_col = _collapse([d for d in str(row["director"]).split(",") if d.strip()])
        writer_col = _collapse([w for w in str(row["writer"]).split(",") if w.strip()])

        tokens = (
            director_col * 3
            + writer_col * 2
            + genres_col * 2
            + kw_col * 2
            + cast_col * 2
            + sanitize_text(row["overview"]).split()
            + sanitize_text(row.get("tagline", "")).split()
        )
        return " ".join(tokens).lower()

    movies["tags"] = movies.apply(_build_weighted_tag_string, axis=1)
    movies["tags"] = movies["tags"].apply(_stem)

    # Finalize columns
    movies["genres"] = movies["genres_list"]
    movies["keywords"] = movies["keywords_list"]
    movies["cast"] = movies["cast_list"]

    # Filter top_n if requested
    if "popularity" in movies.columns:
        movies["popularity"] = pd.to_numeric(movies["popularity"], errors="coerce").fillna(0)
        movies = movies.sort_values("popularity", ascending=False)
    elif "vote_count" in movies.columns:
        movies = movies.sort_values("vote_count", ascending=False)

    if top_n and len(movies) > top_n:
        print(f"[INFO]  Selecting top {top_n:,} most popular/rated movies for active recommendation model.")
        movies = movies.head(top_n).reset_index(drop=True)

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
        "decade",
        "vote_average",
        "vote_count",
        "bayesian_rating",
        "runtime",
        "runtime_category",
        "poster_path",
        "backdrop_path",
        "release_date",
        "budget",
        "revenue",
        "profit",
        "roi",
        "is_profitable",
        "imdb_id",
        "imdb_rating",
        "imdb_votes",
        "popularity",
        "tags",
    ]
    keep_cols = [c for c in keep_cols if c in movies.columns]
    return movies[keep_cols].copy()

