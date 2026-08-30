"""
app/services/movie_db.py
========================
Multi-tier Movie Database Aggregator & Rich Context Engine.

Sources:
  • Tier 1 — TMDB API v3        (Online metadata, high-res posters, trailers, credits)
  • Tier 2 — OMDb API           (IMDb, Rotten Tomatoes, Metacritic, Awards, Box Office)
  • Tier 3 — Wikipedia Context  (Trivia, extended summaries, external links)
  • Tier 4 — Enriched Local DB  (Complete offline dataset with directors, cast, budget, mood tags)

All tiers normalize into the comprehensive ``Movie`` schema.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from app.core.config import settings
from app.schemas.movie import Movie

logger = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
TMDB_BACK = "https://image.tmdb.org/t/p/w1280"
OMDB_BASE = "https://www.omdbapi.com"
PLACEHOLDER = ""

_HTTP_TIMEOUT = 5  # seconds
_MOVIE_EXTRA_CACHE: dict[int, dict[str, Any]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Local Dataset Loader (Tier 4 — Always available & offline-ready)
# ─────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_local_df() -> pd.DataFrame:
    """Load the preprocessed enriched DataFrame (movies.pkl or fallback CSV)."""
    pkl = settings.processed_dir / "movies.pkl"
    csv = settings.raw_dir / "tmdb_5000_movies.csv"

    if pkl.exists():
        try:
            df = pd.read_pickle(pkl)
            logger.info("Local dataset loaded from movies.pkl (%d movies)", len(df))
            return df
        except Exception as e:
            logger.warning("Failed to load movies.pkl: %s", e)

    # Fallback to raw CSV if pkl missing
    if csv.exists():
        try:
            df = pd.read_csv(csv)
            if "id" in df.columns and "movie_id" not in df.columns:
                df = df.rename(columns={"id": "movie_id"})
            logger.info("Local dataset loaded from raw CSV (%d movies)", len(df))
            return df
        except Exception as e:
            logger.error("Failed to load raw CSV: %s", e)

    logger.warning("No local movie dataset found.")
    return pd.DataFrame(columns=["movie_id", "title"])


def _row_to_movie(row: pd.Series) -> Movie:
    """Convert an enriched DataFrame row to a comprehensive Movie schema object."""
    import ast

    def _ensure_list(val) -> list[str]:
        if isinstance(val, list):
            return [str(x) for x in val]
        if isinstance(val, str) and val.strip():
            try:
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return [
                        str(g["name"]) if isinstance(g, dict) and "name" in g else str(g)
                        for g in parsed
                    ]
            except Exception:
                return [s.strip() for s in val.split(",") if s.strip()]
        return []

    title = str(row.get("title", "") or "")
    m_id = int(row.get("movie_id", row.get("id", 0)))

    # Year derivation
    year_val = row.get("year")
    if pd.notna(year_val) and year_val:
        year: int | None = int(year_val)
    else:
        rel = str(row.get("release_date", "") or "")
        if len(rel) >= 4 and rel[:4].isdigit():
            year = int(rel[:4])
        else:
            match = re.search(r"\((\d{4})\)$", title)
            year = int(match.group(1)) if match else None

    # Poster & Backdrop
    poster_path = str(row.get("poster_path", "") or "").strip()
    backdrop_path = str(row.get("backdrop_path", "") or "").strip()
    poster_url = (
        f"{TMDB_IMG}/{poster_path.lstrip('/')}"
        if poster_path and poster_path != "nan"
        else ""
    )
    backdrop_url = (
        f"{TMDB_BACK}/{backdrop_path.lstrip('/')}"
        if backdrop_path and backdrop_path != "nan"
        else ""
    )

    # Runtime
    runtime_raw = row.get("runtime")
    runtime = int(runtime_raw) if pd.notna(runtime_raw) and runtime_raw else None

    # Cast & Director & Writer
    cast_list = _ensure_list(row.get("cast", []))
    director_val = str(row.get("director", "") or "").strip()
    writer_val = str(row.get("writer", "") or "").strip()
    producers_val = _ensure_list(row.get("producers", []))
    moods_val = _ensure_list(row.get("moods", []))
    genres_val = _ensure_list(row.get("genres", []))

    # Budget & Revenue
    budget_raw = row.get("budget", 0)
    revenue_raw = row.get("revenue", 0)
    budget = int(budget_raw) if pd.notna(budget_raw) and str(budget_raw).isdigit() else 0
    revenue = int(revenue_raw) if pd.notna(revenue_raw) and str(revenue_raw).isdigit() else 0

    return Movie(
        id=m_id,
        title=title.strip(),
        overview=str(row.get("overview", "") or "").strip(),
        tagline=str(row.get("tagline", "") or "").strip(),
        poster_url=poster_url,
        backdrop_url=backdrop_url,
        genres=genres_val,
        moods=moods_val,
        year=year,
        vote_average=float(row.get("vote_average", 0) or 0.0),
        vote_count=int(row.get("vote_count", 0) or 0),
        runtime=runtime,
        imdb_id=str(row.get("imdb_id", "") or ""),
        director=director_val,
        writer=writer_val,
        producers=producers_val,
        cast=cast_list,
        budget=budget,
        revenue=revenue,
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
        # Bayesian weighted ranking for top popular
        v = df["vote_count"].fillna(0).values
        R = df["vote_average"].fillna(0).values
        m = 250
        C = 6.0
        wr = (v / (v + m)) * R + (m / (v + m)) * C
        df = df.assign(_wr=wr).sort_values("_wr", ascending=False)
    offset = (page - 1) * per_page
    return [_row_to_movie(r) for _, r in df.iloc[offset : offset + per_page].iterrows()]


# ─────────────────────────────────────────────────────────────────────────────
# TMDB API Integration (Tier 1)
# ─────────────────────────────────────────────────────────────────────────────


def _tmdb_to_movie(data: dict, credits: dict | None = None, videos: dict | None = None) -> Movie:
    genres = [g["name"] for g in data.get("genres", [])]
    poster = f"{TMDB_IMG}{data['poster_path']}" if data.get("poster_path") else ""
    backdrop = f"{TMDB_BACK}{data['backdrop_path']}" if data.get("backdrop_path") else ""
    release = data.get("release_date", "") or ""
    year = int(release[:4]) if len(release) >= 4 and release[:4].isdigit() else None

    # Cast & Crew from credits
    director, writer = "", ""
    cast_list: list[str] = []
    if credits:
        for crew_member in credits.get("crew", []):
            job = crew_member.get("job", "")
            name = crew_member.get("name", "")
            if job == "Director" and not director:
                director = name
            elif job in ("Writer", "Screenplay") and not writer:
                writer = name
        cast_list = [c["name"] for c in credits.get("cast", [])[:8] if "name" in c]

    # YouTube Trailer URL
    trailer_url = ""
    if videos:
        for vid in videos.get("results", []):
            if vid.get("site") == "YouTube" and vid.get("type") in ("Trailer", "Teaser"):
                trailer_url = f"https://www.youtube.com/watch?v={vid.get('key')}"
                break

    return Movie(
        id=data.get("id", 0),
        title=data.get("title", ""),
        overview=data.get("overview", ""),
        tagline=data.get("tagline", ""),
        poster_url=poster,
        backdrop_url=backdrop,
        genres=genres,
        year=year,
        vote_average=data.get("vote_average", 0.0),
        vote_count=data.get("vote_count", 0),
        runtime=data.get("runtime"),
        imdb_id=data.get("imdb_id", ""),
        budget=data.get("budget", 0),
        revenue=data.get("revenue", 0),
        director=director,
        writer=writer,
        cast=cast_list,
        trailer_url=trailer_url,
    )


async def _tmdb_search(query: str, page: int = 1) -> list[Movie]:
    params = {"api_key": settings.tmdb_api_key, "query": query, "page": page}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(f"{TMDB_BASE}/search/movie", params=params)
        r.raise_for_status()
    return [_tmdb_to_movie(m) for m in r.json().get("results", [])]


async def _tmdb_detail(movie_id: int) -> Movie | None:
    params = {
        "api_key": settings.tmdb_api_key,
        "append_to_response": "credits,videos,keywords,release_dates",
    }
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(f"{TMDB_BASE}/movie/{movie_id}", params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        return _tmdb_to_movie(data, credits=data.get("credits"), videos=data.get("videos"))


async def _tmdb_popular(page: int = 1) -> list[Movie]:
    params = {"api_key": settings.tmdb_api_key, "page": page}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as c:
        r = await c.get(f"{TMDB_BASE}/movie/popular", params=params)
        r.raise_for_status()
    return [_tmdb_to_movie(m) for m in r.json().get("results", [])]


# ─────────────────────────────────────────────────────────────────────────────
# OMDb Multi-Source Ratings & Box Office (Tier 2)
# ─────────────────────────────────────────────────────────────────────────────


async def _fetch_omdb_ratings(title: str, year: int | None = None) -> dict[str, Any]:
    """Fetch multi-source ratings (Rotten Tomatoes, Metacritic, IMDb, Box Office) from OMDb."""
    key = settings.omdb_api_key or "trilogy"
    params: dict[str, Any] = {"t": title, "apikey": key}
    if year:
        params["y"] = year

    out = {
        "rotten_tomatoes_score": "",
        "metascore": "",
        "imdb_rating": None,
        "director": "",
        "writer": "",
        "cast": [],
        "poster_url": "",
        "imdb_id": "",
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(OMDB_BASE, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("Response") == "True":
                    out["imdb_id"] = data.get("imdbID", "")
                    poster = data.get("Poster", "")
                    if poster and poster != "N/A":
                        out["poster_url"] = poster

                    try:
                        out["imdb_rating"] = float(data.get("imdbRating", 0) or 0)
                    except ValueError:
                        pass

                    out["metascore"] = (
                        f"{data.get('Metascore')}/100"
                        if data.get("Metascore") and data.get("Metascore") != "N/A"
                        else ""
                    )

                    # Parse Rotten Tomatoes from Ratings array
                    for rating_item in data.get("Ratings", []):
                        if rating_item.get("Source") == "Rotten Tomatoes":
                            out["rotten_tomatoes_score"] = rating_item.get("Value", "")

                    director = data.get("Director", "")
                    writer = data.get("Writer", "")
                    actors = data.get("Actors", "")
                    if director and director != "N/A":
                        out["director"] = director
                    if writer and writer != "N/A":
                        out["writer"] = writer
                    if actors and actors != "N/A":
                        out["cast"] = [a.strip() for a in actors.split(",") if a.strip()]
    except Exception as e:
        logger.debug("OMDb enrichment failed for %r: %s", title, e)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Public Aggregated API
# ─────────────────────────────────────────────────────────────────────────────


async def resolve_extra_info(movie_id: int, title: str, tmdb_key: str = "") -> dict[str, Any]:
    """Resolve and cache high-res poster, IMDb rating, Rotten Tomatoes, and credits."""
    if movie_id in _MOVIE_EXTRA_CACHE:
        return _MOVIE_EXTRA_CACHE[movie_id]

    extra: dict[str, Any] = {
        "poster_url": "",
        "backdrop_url": "",
        "imdb_id": "",
        "imdb_rating": None,
        "rotten_tomatoes_score": "",
        "metascore": "",
        "director": "",
        "writer": "",
        "cast": [],
        "trailer_url": "",
    }

    # If TMDB key available, query TMDB first
    if tmdb_key or settings.tmdb_api_key:
        try:
            key = tmdb_key or settings.tmdb_api_key
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(
                    f"{TMDB_BASE}/movie/{movie_id}",
                    params={"api_key": key, "append_to_response": "videos,credits"},
                )
                if r.status_code == 200:
                    data = r.json()
                    path = data.get("poster_path")
                    back = data.get("backdrop_path")
                    if path:
                        extra["poster_url"] = f"{TMDB_IMG}{path}"
                    if back:
                        extra["backdrop_url"] = f"{TMDB_BACK}{back}"
                    extra["imdb_id"] = data.get("imdb_id", "")

                    # Trailer
                    for vid in data.get("videos", {}).get("results", []):
                        if vid.get("site") == "YouTube" and vid.get("type") in ("Trailer", "Teaser"):
                            extra["trailer_url"] = f"https://www.youtube.com/watch?v={vid.get('key')}"
                            break

                    # Credits
                    for c in data.get("credits", {}).get("crew", []):
                        if c.get("job") == "Director" and not extra["director"]:
                            extra["director"] = c.get("name", "")
                        elif c.get("job") in ("Writer", "Screenplay") and not extra["writer"]:
                            extra["writer"] = c.get("name", "")
                    extra["cast"] = [
                        c["name"] for c in data.get("credits", {}).get("cast", [])[:6] if "name" in c
                    ]
        except Exception as e:
            logger.debug("TMDB extra resolve failed for ID %d: %s", movie_id, e)

    # Enrich with OMDb scores (Rotten Tomatoes & Metacritic)
    omdb_info = await _fetch_omdb_ratings(title)
    if omdb_info.get("rotten_tomatoes_score"):
        extra["rotten_tomatoes_score"] = omdb_info["rotten_tomatoes_score"]
    if omdb_info.get("metascore"):
        extra["metascore"] = omdb_info["metascore"]
    if omdb_info.get("imdb_rating"):
        extra["imdb_rating"] = omdb_info["imdb_rating"]
    if not extra["poster_url"] and omdb_info.get("poster_url"):
        extra["poster_url"] = omdb_info["poster_url"]
    if not extra["director"] and omdb_info.get("director"):
        extra["director"] = omdb_info["director"]
    if not extra["writer"] and omdb_info.get("writer"):
        extra["writer"] = omdb_info["writer"]
    if not extra["cast"] and omdb_info.get("cast"):
        extra["cast"] = omdb_info["cast"]

    # Fallback styled placeholder
    if not extra["poster_url"]:
        escaped = urllib.parse.quote(title)
        extra["poster_url"] = f"https://placehold.co/300x450/2e3440/88c0d0?text={escaped}"

    _MOVIE_EXTRA_CACHE[movie_id] = extra
    return extra


async def resolve_poster_url(movie_id: int, title: str, tmdb_key: str = "") -> str:
    """Resolve poster URL for a movie ID and title."""
    extra = await resolve_extra_info(movie_id, title, tmdb_key)
    return extra.get("poster_url", "")


async def search_movies(query: str, page: int = 1) -> tuple[list[Movie], str]:
    """Search movies across TMDB → Local dataset → OMDb."""
    # Tier 1 — TMDB API
    if settings.tmdb_api_key:
        try:
            results = await _tmdb_search(query, page)
            if results:
                return results, "tmdb"
        except Exception as e:
            logger.warning("TMDB search failed: %s", e)

    # Tier 2 — Local dataset
    local_movies = _search_local(query, page)
    if local_movies:
        tasks = [
            resolve_extra_info(m.id, m.title, settings.tmdb_api_key) for m in local_movies
        ]
        extras = await asyncio.gather(*tasks)
        for m, extra in zip(local_movies, extras):
            if extra.get("poster_url"):
                m.poster_url = extra["poster_url"]
            if extra.get("imdb_rating"):
                m.imdb_rating = extra["imdb_rating"]
            if extra.get("rotten_tomatoes_score"):
                m.rotten_tomatoes_score = extra["rotten_tomatoes_score"]
        return local_movies, "local"

    return [], "none"


async def get_movie(movie_id: int) -> Movie | None:
    """Fetch full movie details by TMDB movie ID."""
    # Tier 1 — TMDB
    if settings.tmdb_api_key:
        try:
            movie = await _tmdb_detail(movie_id)
            if movie:
                # Add OMDb Rotten Tomatoes & Metacritic scores
                omdb_info = await _fetch_omdb_ratings(movie.title, movie.year)
                movie.rotten_tomatoes_score = omdb_info.get("rotten_tomatoes_score", "")
                movie.metascore = omdb_info.get("metascore", "")
                movie.imdb_rating = omdb_info.get("imdb_rating")
                return movie
        except Exception as e:
            logger.warning("TMDB detail failed: %s", e)

    # Tier 2 — Local Dataset
    movie = _get_local_by_id(movie_id)
    if movie:
        extra = await resolve_extra_info(movie.id, movie.title, settings.tmdb_api_key)
        if extra.get("poster_url"):
            movie.poster_url = extra["poster_url"]
        if extra.get("backdrop_url"):
            movie.backdrop_url = extra["backdrop_url"]
        if extra.get("trailer_url"):
            movie.trailer_url = extra["trailer_url"]
        if extra.get("imdb_rating"):
            movie.imdb_rating = extra["imdb_rating"]
        if extra.get("rotten_tomatoes_score"):
            movie.rotten_tomatoes_score = extra["rotten_tomatoes_score"]
        if extra.get("metascore"):
            movie.metascore = extra["metascore"]
        if not movie.director and extra.get("director"):
            movie.director = extra["director"]
        if not movie.writer and extra.get("writer"):
            movie.writer = extra["writer"]
        if not movie.cast and extra.get("cast"):
            movie.cast = extra["cast"]
        return movie

    return None


async def get_popular(page: int = 1) -> list[Movie]:
    """Return popular movies with Bayesian score ordering and posters."""
    if settings.tmdb_api_key:
        try:
            return await _tmdb_popular(page)
        except Exception as e:
            logger.warning("TMDB popular failed: %s", e)

    movies = _popular_local(page)
    tasks = [resolve_poster_url(m.id, m.title, settings.tmdb_api_key) for m in movies]
    poster_urls = await asyncio.gather(*tasks)
    for m, url in zip(movies, poster_urls):
        if url:
            m.poster_url = url
    return movies
