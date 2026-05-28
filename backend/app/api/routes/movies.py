"""app/api/routes/movies.py — Movie search, detail, and popular endpoints."""

from __future__ import annotations

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
    """Return popular movies (TMDB popular → local dataset sorted by votes)."""
    return await movie_db.get_popular(page)


@router.get("/{movie_id}", response_model=Movie)
async def detail(movie_id: int):
    """Fetch full details for a single movie by its TMDB movie ID."""
    movie = await movie_db.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found.")
    return movie
