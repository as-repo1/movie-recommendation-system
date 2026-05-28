"""
app/services/movie_db.py
========================
Movie data service with a three-tier lookup strategy:

  Tier 1 — TMDB API v3        (if TMDB_API_KEY is set)
  Tier 2 — OMDb API           (if OMDB_API_KEY is set)
  Tier 3 — Local dataset      (always available; TMDB 5000 CSV / movies.pkl)

All tiers return the same ``Movie`` schema so callers are source-agnostic.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from functools import lru_cache
from pathlib import Path

import httpx
import pandas as pd

from app.core.config import settings
from app.schemas.movie import Movie

logger = logging.getLogger(__name__)

TMDB_BASE   = "https://api.themoviedb.org/3"
TMDB_IMG    = "https://image.tmdb.org/t/p/w500"
TMDB_BACK   = "https://image.tmdb.org/t/p/w1280"
OMDB_BASE   = "http://www.omdbapi.com"
PLACEHOLDER = ""  # frontend renders its own SVG placeholder

_HTTP_TIMEOUT = 6  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# Local dataset loader (Tier 3 — always available)
# ─────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_local_df() -> pd.DataFrame:
    """Load the TMDB 5000 processed DataFrame (movies.pkl or raw CSV)."""
    pkl = settings.processed_dir / "movies.pkl"
    csv = settings.raw_dir / "tmdb_5000_movies.csv"

    if pkl.exists():
        df = pd.read_pickle(pkl)
        # movies.pkl has: movie_id, title, tags — enrich with poster_path from CSV
        if csv.exists() and "poster_path" not in df.columns:
            try:
                extra = pd.read_csv(csv, usecols=["id", "poster_path", "release_date",
                                                   "overview", "genres", "vote_average",
                                                   "vote_count", "runtime"])
                extra = extra.rename(columns={"id": "movie_id"})
                df = df.merge(extra, on="movie_id", how="left")
            except Exception as e:
                logger.warning("Could not enrich pkl with CSV poster data: %s", e)
        logger.info("Local dataset loaded from movies.pkl (%d movies)", len(df))
        return df

    # Try raw CSV
    if csv.exists():
        df = pd.read_csv(csv, usecols=["id", "title", "overview", "genres",
                                        "vote_average", "vote_count", "runtime",
                                        "poster_path", "release_date"])
        df = df.rename(columns={"id": "movie_id"})
        logger.info("Local dataset loaded from CSV (%d movies)", len(df))
        return df

    logger.warning("No local movie dataset found; local search unavailable.")
    return pd.DataFrame(columns=["movie_id", "title"])


def _row_to_movie(row: pd.Series) -> Movie:
    """Convert a DataFrame row to a Movie schema object."""
    import ast

    def _parse_genres(val) -> list[str]:
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                parsed = ast.literal_eval(val)
                return [g["name"] for g in parsed if isinstance(g, dict)]
            except Exception:
                return []
        return []

    genres = _parse_genres(row.get("genres", []))
    title  = str(row.get("title", ""))

    # Derive year from release_date or title "(YYYY)" suffix
    release = str(row.get("release_date", "") or "")
    if len(release) >= 4 and release[:4].isdigit():
        year: int | None = int(release[:4])
    else:
        year_match = re.search(r"\((\d{4})\)$", title)
        year = int(year_match.group(1)) if year_match else None

    # Build poster URL from TMDB image CDN — public, no API key required
    poster_path = row.get("poster_path", "") or ""
    if not isinstance(poster_path, str) or not poster_path.strip():
        poster_url = ""
    else:
        poster_path = poster_path.strip()
        poster_url = f"{TMDB_IMG}{poster_path}" if poster_path.startswith("/") else f"{TMDB_IMG}/{poster_path}"

    return Movie(
        id=int(row.get("movie_id", row.get("id", 0))),
        title=title.strip(),
        overview=str(row.get("overview", "") or ""),
        genres=genres,
        year=year,
        vote_average=float(row.get("vote_average", 0) or 0),
        vote_count=int(row.get("vote_count", 0) or 0),
        runtime=int(row["runtime"]) if pd.notna(row.get("runtime")) else None,
        poster_url=poster_url,
        director="",
        writer="",
        cast=[],
    )


def _search_local(query: str, page: int = 1, per_page: int = 20) -> list[Movie]:
    df = _load_local_df()
    if df.empty:
        return []
    mask = df["title"].str.contains(query, case=False, na=False)
    results = df[mask].head(per_page * page).tail(per_page)
    return [_row_to_movie(r) for _, r in results.iterrows()]


def _get_local_by_id(movie_id: int) -> Movie | None:
    df = _load_local_df()
    col = "movie_id" if "movie_id" in df.columns else "id"
    row_df = df[df[col] == movie_id]
    if row_df.empty:
        return None
    return _row_to_movie(row_df.iloc[0])


def _popular_local(page: int = 1, per_page: int = 20) -> list[Movie]:
    df = _load_local_df()
    if df.empty:
        return []
    if "vote_count" in df.columns and "vote_average" in df.columns:
        df = df.sort_values("vote_count", ascending=False)
    offset = (page - 1) * per_page
    return [_row_to_movie(r) for _, r in df.iloc[offset:offset + per_page].iterrows()]


# ─────────────────────────────────────────────────────────────────────────────
# TMDB helpers (Tier 1)
# ─────────────────────────────────────────────────────────────────────────────


def _tmdb_movie(data: dict) -> Movie:
    genres = [g["name"] for g in data.get("genres", [])]
    poster = f"{TMDB_IMG}{data['poster_path']}" if data.get("poster_path") else PLACEHOLDER
    backdrop = f"{TMDB_BACK}{data['backdrop_path']}" if data.get("backdrop_path") else ""
    release = data.get("release_date", "") or ""
    year = int(release[:4]) if len(release) >= 4 else None
    return Movie(
        id=data.get("id", 0),
        title=data.get("title", ""),
        overview=data.get("overview", ""),
        poster_url=poster,
        backdrop_url=backdrop,
        genres=genres,
        year=year,
        vote_average=data.get("vote_average", 0),
        vote_count=data.get("vote_count", 0),
        runtime=data.get("runtime"),
        imdb_id=data.get("imdb_id", ""),
        director="",
        writer="",
        cast=[],
    )


async def _tmdb_search(query: str, page: int = 1) -> list[Movie]:
    params = {"api_key": settings.tmdb_api_key, "query": query, "page": page}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(f"{TMDB_BASE}/search/movie", params=params)
        r.raise_for_status()
    return [_tmdb_movie(m) for m in r.json().get("results", [])]


async def _tmdb_detail(movie_id: int) -> Movie | None:
    params = {"api_key": settings.tmdb_api_key}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(f"{TMDB_BASE}/movie/{movie_id}", params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
    return _tmdb_movie(r.json())


async def _tmdb_popular(page: int = 1) -> list[Movie]:
    params = {"api_key": settings.tmdb_api_key, "page": page}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(f"{TMDB_BASE}/movie/popular", params=params)
        r.raise_for_status()
    return [_tmdb_movie(m) for m in r.json().get("results", [])]


# ─────────────────────────────────────────────────────────────────────────────
# OMDb helpers (Tier 2)
# ─────────────────────────────────────────────────────────────────────────────


def _omdb_movie(data: dict, movie_id: int = 0) -> Movie:
    genres = [g.strip() for g in data.get("Genre", "").split(",") if g.strip()]
    year_str = data.get("Year", "") or ""
    try:
        year = int(year_str[:4])
    except ValueError:
        year = None
    poster = data.get("Poster", "") or ""
    if poster == "N/A":
        poster = PLACEHOLDER
    try:
        rating = float(data.get("imdbRating", 0) or 0)
    except ValueError:
        rating = 0.0
    try:
        votes = int((data.get("imdbVotes", "0") or "0").replace(",", ""))
    except ValueError:
        votes = 0
    runtime_str = data.get("Runtime", "") or ""
    runtime = int(runtime_str.split()[0]) if runtime_str and runtime_str[0].isdigit() else None
    director = data.get("Director", "")
    writer = data.get("Writer", "")
    actors_str = data.get("Actors", "")
    cast = [a.strip() for a in actors_str.split(",") if a.strip()] if actors_str and actors_str != "N/A" else []

    return Movie(
        id=movie_id,
        title=data.get("Title", ""),
        overview=data.get("Plot", ""),
        poster_url=poster,
        genres=genres,
        year=year,
        vote_average=rating,
        vote_count=votes,
        runtime=runtime,
        imdb_id=data.get("imdbID", ""),
        director=director if director != "N/A" else "",
        writer=writer if writer != "N/A" else "",
        cast=cast,
    )


async def _omdb_search(query: str, page: int = 1) -> list[Movie]:
    key = settings.omdb_api_key or "trilogy"
    params = {"s": query, "apikey": key, "page": page, "type": "movie"}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(OMDB_BASE, params=params)
        r.raise_for_status()
    data = r.json()
    if data.get("Response") != "True":
        return []

    # Build a lookup from imdbID → local TMDB movie_id
    df = _load_local_df()
    imdb_to_tmdb: dict[str, int] = {}
    if not df.empty and "imdb_id" in df.columns:
        for _, row in df[["movie_id", "imdb_id"]].dropna().iterrows():
            imdb_to_tmdb[str(row["imdb_id"])] = int(row["movie_id"])

    results = []
    for item in data.get("Search", []):
        imdb_id = item.get("imdbID", "")
        # Try to get the real TMDB id from local dataset
        tmdb_id = imdb_to_tmdb.get(imdb_id, 0)
        if tmdb_id == 0:
            # Try matching by title in local dataset as fallback
            title = item.get("Title", "")
            if not df.empty and title:
                mask = df["title"].str.lower() == title.lower()
                matched = df[mask]
                if not matched.empty:
                    tmdb_id = int(matched.iloc[0].get("movie_id", 0))
        if tmdb_id == 0:
            continue  # skip results with no resolvable ID
        results.append(Movie(
            id=tmdb_id,
            title=item.get("Title", ""),
            year=int(item["Year"][:4]) if item.get("Year", "")[:4].isdigit() else None,
            poster_url=item.get("Poster", PLACEHOLDER) if item.get("Poster", "") != "N/A" else PLACEHOLDER,
            imdb_id=imdb_id,
            director="",
            writer="",
            cast=[],
        ))
    return results



async def _omdb_detail(imdb_id: str) -> Movie | None:
    key = settings.omdb_api_key or "trilogy"
    params = {"i": imdb_id, "plot": "full", "apikey": key}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(OMDB_BASE, params=params)
        r.raise_for_status()
    data = r.json()
    if data.get("Response") != "True":
        return None
    return _omdb_movie(data)


# ── Public API (source-agnostic) ─────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────

_MOVIE_EXTRA_CACHE: dict[int, dict[str, Any]] = {}


async def resolve_extra_info(movie_id: int, title: str, tmdb_key: str = "") -> dict[str, Any]:
    """Resolve poster URL, IMDb ID, director, writer, and cast dynamically using TMDB or OMDb, and cache them."""
    if movie_id in _MOVIE_EXTRA_CACHE:
        return _MOVIE_EXTRA_CACHE[movie_id]

    extra = {"poster_url": "", "imdb_id": "", "director": "", "writer": "", "cast": []}

    # If TMDB API key is provided, try TMDB first
    if tmdb_key:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(
                    f"https://api.themoviedb.org/3/movie/{movie_id}",
                    params={"api_key": tmdb_key}
                )
                if r.status_code == 200:
                    data = r.json()
                    path = data.get("poster_path")
                    extra["poster_url"] = f"https://image.tmdb.org/t/p/w500{path}" if path else ""
                    extra["imdb_id"] = data.get("imdb_id", "")
                    _MOVIE_EXTRA_CACHE[movie_id] = extra
                    return extra
        except Exception as e:
            logger.debug("Failed to resolve extra info from TMDB for ID %d: %s", movie_id, e)

    # Fallback to OMDb by title using default trilogy key if none set
    omdb_key = settings.omdb_api_key or "trilogy"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(
                "http://www.omdbapi.com/",
                params={"t": title, "apikey": omdb_key}
            )
            if r.status_code == 200:
                data = r.json()
                poster = data.get("Poster")
                extra["poster_url"] = poster if (poster and poster != "N/A") else ""
                extra["imdb_id"] = data.get("imdbID", "")

                director = data.get("Director", "")
                writer = data.get("Writer", "")
                actors_str = data.get("Actors", "")

                extra["director"] = director if director != "N/A" else ""
                extra["writer"] = writer if writer != "N/A" else ""
                extra["cast"] = [a.strip() for a in actors_str.split(",") if a.strip()] if actors_str and actors_str != "N/A" else []

                _MOVIE_EXTRA_CACHE[movie_id] = extra
                return extra
    except Exception as e:
            logger.debug("Failed to resolve extra info from OMDb for title %r: %s", title, e)

    # Final fallback placeholder (Nord themed)
    escaped_title = urllib.parse.quote(title)
    extra["poster_url"] = f"https://placehold.co/300x450/2e3440/88c0d0?text={escaped_title}"
    _MOVIE_EXTRA_CACHE[movie_id] = extra
    return extra


async def resolve_poster_url(movie_id: int, title: str, tmdb_key: str = "") -> str:
    """Helper keeping poster resolution API compatible."""
    extra = await resolve_extra_info(movie_id, title, tmdb_key)
    return extra["poster_url"]


async def search_movies(query: str, page: int = 1) -> tuple[list[Movie], str]:
    """Search movies. Returns (results, source_name).

    Strategy:
      1. TMDB API — best results, real TMDB IDs, requires API key
      2. Local dataset — always available, guaranteed correct TMDB IDs
      3. OMDb API — cross-referenced against local dataset for IDs
    """
    # Tier 1 — TMDB (if key available — always correct IDs)
    if settings.tmdb_api_key:
        try:
            results = await _tmdb_search(query, page)
            if results:
                return results, "tmdb"
        except Exception as e:
            logger.warning("TMDB search failed: %s", e)

    # Tier 2 — local dataset (instant, always correct IDs)
    local_movies = _search_local(query, page)
    if local_movies:
        tasks = [resolve_poster_url(m.id, m.title, settings.tmdb_api_key) for m in local_movies]
        poster_urls = await asyncio.gather(*tasks)
        for m, url in zip(local_movies, poster_urls):
            if url:
                m.poster_url = url
        return local_movies, "local"

    # Tier 3 — OMDb (IDs cross-referenced with local dataset, so still reliable)
    try:
        results = await _omdb_search(query, page)
        if results:
            return results, "omdb"
    except Exception as e:
        logger.warning("OMDb search failed: %s", e)

    return [], "none"



async def get_movie(movie_id: int) -> Movie | None:
    """Fetch full movie details by TMDB movie_id."""
    if settings.tmdb_api_key:
        try:
            return await _tmdb_detail(movie_id)
        except Exception as e:
            logger.warning("TMDB detail failed: %s", e)
            
    # Fall back to local dataset
    movie = _get_local_by_id(movie_id)
    if movie:
        extra = await resolve_extra_info(movie.id, movie.title, settings.tmdb_api_key)
        movie.poster_url = extra["poster_url"]
        movie.imdb_id = extra["imdb_id"]
        movie.director = extra.get("director", "")
        movie.writer = extra.get("writer", "")
        movie.cast = extra.get("cast", [])
    return movie


async def get_popular(page: int = 1) -> list[Movie]:
    """Return popular movies."""
    if settings.tmdb_api_key:
        try:
            return await _tmdb_popular(page)
        except Exception as e:
            logger.warning("TMDB popular failed: %s", e)
            
    movies = _popular_local(page)
    tasks = [
        resolve_poster_url(m.id, m.title, settings.tmdb_api_key)
        for m in movies
    ]
    poster_urls = await asyncio.gather(*tasks)
    for m, url in zip(movies, poster_urls):
        m.poster_url = url
    return movies
