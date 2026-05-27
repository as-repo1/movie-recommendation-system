"""
src.poster
==========
Movie poster retrieval with a two-tier fallback strategy.

Priority
--------
1. **TMDB API** — highest quality, requires a free API key.
2. **OMDb demo tier** — no personal key required, lower coverage.
3. **Placeholder** — a styled grey tile shown when all else fails.

Public API
----------
get_poster(movie_id, title, api_key="") → str  (image URL)
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

TMDB_BASE_URL  = "https://api.themoviedb.org/3/movie"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

OMDB_BASE_URL  = "https://www.omdbapi.com/"
OMDB_DEMO_KEY  = "trilogy"  # public demo key — limited but key-free

PLACEHOLDER_URL = (
    "https://via.placeholder.com/300x450/1a1a2e/a78bfa"
    "?text=No+Poster"
)

_REQUEST_TIMEOUT = 5  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _fetch_tmdb(movie_id: int, api_key: str) -> str | None:
    """Return the TMDB poster URL for *movie_id*, or ``None`` on failure."""
    try:
        url = f"{TMDB_BASE_URL}/{movie_id}?api_key={api_key}&language=en-US"
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        path = resp.json().get("poster_path")
        if path:
            return f"{TMDB_IMAGE_URL}{path}"
    except Exception as exc:
        logger.debug("TMDB poster fetch failed for movie_id=%s: %s", movie_id, exc)
    return None


def _fetch_omdb(title: str) -> str | None:
    """Return an OMDb poster URL for *title*, or ``None`` on failure."""
    try:
        params = {"t": title, "apikey": OMDB_DEMO_KEY}
        resp = requests.get(OMDB_BASE_URL, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        poster = data.get("Poster", "")
        if poster and poster != "N/A":
            return poster
    except Exception as exc:
        logger.debug("OMDb poster fetch failed for title=%r: %s", title, exc)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def get_poster(movie_id: int, title: str, api_key: str = "") -> str:
    """Return the best available poster URL for a movie.

    The function tries sources in priority order and always returns a valid URL:

    1. TMDB API (if *api_key* is non-empty)
    2. OMDb demo tier (no personal key needed)
    3. Styled placeholder image

    Parameters
    ----------
    movie_id:
        TMDB movie ID (the ``movie_id`` column in the dataset).
    title:
        Human-readable movie title used for the OMDb fallback search.
    api_key:
        Optional TMDB API key.  Get one free at
        https://www.themoviedb.org/settings/api

    Returns
    -------
    A fully-qualified image URL string.
    """
    # Tier 1 — TMDB
    if api_key:
        url = _fetch_tmdb(movie_id, api_key)
        if url:
            return url

    # Tier 2 — OMDb fallback
    url = _fetch_omdb(title)
    if url:
        return url

    # Tier 3 — placeholder
    return PLACEHOLDER_URL
