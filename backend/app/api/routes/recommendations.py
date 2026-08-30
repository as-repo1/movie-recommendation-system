"""app/api/routes/recommendations.py — Similar, personalized, and mood recommendation endpoints."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_id, get_db
from app.schemas.movie import (
    PersonalisedRequest,
    PersonalisedResponse,
    SimilarMoviesResponse,
    MoodRecommendationsResponse,
)
from app.services.movie_db import get_movie, resolve_poster_url
from app.core.config import settings
from app.services.recommender import recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/similar/{movie_id}", response_model=SimilarMoviesResponse)
async def similar(
    movie_id: int,
    n: int = Query(default=10, ge=1, le=24),
    use_mmr: bool = Query(default=True, description="Apply MMR diversity re-ranking"),
):
    """Return top-n movies most similar to the given movie with Bayesian boost and MMR."""
    source_movie = await get_movie(movie_id)
    if source_movie is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found.")

    recommendations, engine = recommendation_service.similar_movies(
        movie_id=movie_id,
        n=n,
        use_mmr=use_mmr,
    )

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
        if url:
            m.poster_url = url

    return SimilarMoviesResponse(
        source_movie=source_movie,
        recommendations=recommendations,
        engine=engine,
    )


@router.get("/mood/{mood}", response_model=MoodRecommendationsResponse)
async def mood_recs(
    mood: str,
    n: int = Query(default=12, ge=1, le=30),
):
    """
    Return curated recommendations filtered by mood & vibe:
    - mind-bending (Sci-Fi & psychological mystery)
    - dark-thriller (Crime, suspense, psychological thriller)
    - feel-good (Comedy, animation, heartwarming)
    - adrenaline-action (High-octane action, superhero, adventure)
    - epic-journey (Fantasy, mythology, grand quests)
    - emotional-drama (Romance, deep drama)
    """
    if not recommendation_service.is_ready:
        raise HTTPException(status_code=503, detail="Recommendation engine is initializing.")

    recs = recommendation_service.mood_recommendations(mood=mood.strip().lower(), n=n)
    
    # Resolve poster URLs in parallel
    tasks = [resolve_poster_url(m.id, m.title, settings.tmdb_api_key) for m in recs]
    poster_urls = await asyncio.gather(*tasks)
    for m, url in zip(recs, poster_urls):
        if url:
            m.poster_url = url

    return MoodRecommendationsResponse(mood=mood, recommendations=recs, total=len(recs))


@router.post("/personalised", response_model=PersonalisedResponse)
async def personalised(body: PersonalisedRequest):
    """
    Return personalised recommendations based on user ratings (1.0–10.0).
    Combines LightFM Matrix Factorization, User Taste Profile Vectors, and MMR Diversity.
    """
    if not recommendation_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Recommendation model not loaded. Run `python scripts/build_model.py` first.",
        )

    recommendations, engine, top_genres = recommendation_service.personalised(
        ratings=body.ratings,
        n=body.n,
        diversity_lambda=body.diversity_lambda,
    )

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
        if url:
            m.poster_url = url

    return PersonalisedResponse(
        recommendations=recommendations,
        engine=engine,
        user_top_genres=top_genres,
    )


@router.get("/personalised", response_model=PersonalisedResponse)
async def personalised_db(
    n: int = Query(default=10, ge=1, le=24),
    diversity_lambda: float = Query(default=0.75, ge=0.0, le=1.0),
    session_id: str = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Return personalised movie recommendations based on user ratings stored in the database.
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
    recommendations, engine, top_genres = recommendation_service.personalised(
        ratings=ratings,
        n=n,
        diversity_lambda=diversity_lambda,
    )

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
        if url:
            m.poster_url = url

    return PersonalisedResponse(
        recommendations=recommendations,
        engine=engine,
        user_top_genres=top_genres,
    )


@router.get("/catalogue", response_model=list[dict])
async def catalogue():
    """Return a lightweight list of all movies in the dataset."""
    return recommendation_service.get_all_titles()
