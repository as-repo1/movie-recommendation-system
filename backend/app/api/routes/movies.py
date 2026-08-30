"""app/api/routes/movies.py — Movie search, detail, popular, and genre endpoints."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException, Query


from app.schemas.movie import Movie, MovieSearchResponse
from app.services import movie_db

router = APIRouter(tags=["movies"])


@router.get("/search", response_model=MovieSearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Movie title search query"),
    page: int = Query(default=1, ge=1),
):
    """Search for movies by title across TMDB → OMDb → local dataset."""
    movies, source = await movie_db.search_movies(q.strip(), page)
    return MovieSearchResponse(movies=movies, total=len(movies), page=page, query=q)


@router.get("/popular", response_model=list[Movie])
async def popular(page: int = Query(default=1, ge=1)):
    """Return popular movies with Bayesian score ordering."""
    return await movie_db.get_popular(page)


@router.get("/genres", response_model=list[str])
async def list_genres():
    """Return all unique genres available in the movie catalog."""
    df = movie_db._load_local_df()
    if df.empty or "genres" not in df.columns:
        return [
            "Action", "Adventure", "Animation", "Comedy", "Crime",
            "Documentary", "Drama", "Family", "Fantasy", "History",
            "Horror", "Music", "Mystery", "Romance", "Science Fiction",
            "Thriller", "War", "Western"
        ]
    all_genres: set[str] = set()
    for g_list in df["genres"]:
        if isinstance(g_list, (list, tuple, np.ndarray)):
            for g in g_list:
                g_str = str(g).strip()
                if g_str and g_str.lower() not in ("none", "nan", "null"):
                    all_genres.add(g_str)
    return sorted(list(all_genres)) or [
        "Action", "Adventure", "Animation", "Comedy", "Crime",
        "Documentary", "Drama", "Family", "Fantasy", "History",
        "Horror", "Music", "Mystery", "Romance", "Science Fiction",
        "Thriller", "War", "Western"
    ]



@router.get("/{movie_id}", response_model=Movie)
async def detail(movie_id: int):
    """Fetch comprehensive details for a movie (directors, cast, trailers, ratings)."""
    movie = await movie_db.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found.")
    return movie
