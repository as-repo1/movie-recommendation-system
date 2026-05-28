"""app/api/routes/recommendations.py — Similar and personalised rec endpoints."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_id, get_db
from app.schemas.movie import (
    PersonalisedRequest,
    PersonalisedResponse,
    SimilarMoviesResponse,
)
from app.services.movie_db import get_movie, resolve_poster_url
from app.core.config import settings
from app.services.recommender import recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/similar/{movie_id}", response_model=SimilarMoviesResponse)
async def similar(
    movie_id: int,
    n: int = Query(default=10, ge=1, le=20),
):
    """
    Return the top-n movies most similar to the given movie.
    Uses TF-IDF content-based engine. Falls back gracefully if model
    is not yet trained.
    """
    source_movie = await get_movie(movie_id)
    if source_movie is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found.")

    recommendations, engine = recommendation_service.similar_movies(movie_id, n)

    if engine == "unavailable":
        raise HTTPException(
            status_code=503,
            detail="Recommendation model not loaded. Run `python scripts/build_model.py` first.",
        )

    # Resolve poster URLs in parallel
    tasks = [
        resolve_poster_url(m.id, m.title, settings.tmdb_api_key)
        for m in recommendations
    ]
    poster_urls = await asyncio.gather(*tasks)
    for m, url in zip(recommendations, poster_urls):
        m.poster_url = url

    return SimilarMoviesResponse(
        source_movie=source_movie,
        recommendations=recommendations,
        engine=engine,
    )


@router.post("/personalised", response_model=PersonalisedResponse)
async def personalised(body: PersonalisedRequest):
    """
    Return personalised movie recommendations based on the user's ratings.

    The client sends a list of ``{movie_id, rating}`` pairs (from localStorage /
    SharedPreferences). No server-side user account is required.

    Uses LightFM hybrid model when available; falls back to weighted content-based.
    """
    if not recommendation_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Recommendation model not loaded. Run `python scripts/build_model.py` first.",
        )

    recommendations, engine = recommendation_service.personalised(body.ratings, body.n)

    if not recommendations:
        raise HTTPException(
            status_code=404,
            detail="None of the rated movies were found in the recommendation dataset.",
        )

    # Resolve poster URLs in parallel
    tasks = [
        resolve_poster_url(m.id, m.title, settings.tmdb_api_key)
        for m in recommendations
    ]
    poster_urls = await asyncio.gather(*tasks)
    for m, url in zip(recommendations, poster_urls):
        m.poster_url = url

    return PersonalisedResponse(recommendations=recommendations, engine=engine)


@router.get("/personalised", response_model=PersonalisedResponse)
async def personalised_db(
    n: int = Query(default=10, ge=1, le=20),
    session_id: str = Depends(get_session_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Return personalised movie recommendations based on the user's ratings stored in the database.

    Looks up ratings associated with the session ID from X-Session-ID header.
    """
    if not recommendation_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Recommendation model not loaded. Run `python scripts/build_model.py` first.",
        )

    from sqlalchemy import select
    from app.models.db import WatchedMovie
    from app.schemas.movie import RatedMovie

    stmt = select(WatchedMovie).where(WatchedMovie.session_id == session_id)
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        raise HTTPException(
            status_code=400,
            detail="No ratings found for this session. Rate some movies to get personalised recommendations.",
        )

    ratings = [RatedMovie(movie_id=item.movie_id, rating=item.rating) for item in items]
    recommendations, engine = recommendation_service.personalised(ratings, n)

    if not recommendations:
        raise HTTPException(
            status_code=404,
            detail="None of the rated movies were found in the recommendation dataset.",
        )

    # Resolve poster URLs in parallel
    tasks = [
        resolve_poster_url(m.id, m.title, settings.tmdb_api_key)
        for m in recommendations
    ]
    poster_urls = await asyncio.gather(*tasks)
    for m, url in zip(recommendations, poster_urls):
        m.poster_url = url

    return PersonalisedResponse(recommendations=recommendations, engine=engine)



@router.get("/catalogue", response_model=list[dict])
async def catalogue():
    """Return a lightweight list of all movies in the dataset (id + title).
    Used by the frontend / Android app to populate the search dropdown."""
    return recommendation_service.get_all_titles()
