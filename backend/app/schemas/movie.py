"""app/schemas/movie.py — Pydantic schemas shared by all routes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Movie(BaseModel):
    """A single movie record returned by the API with comprehensive metadata."""

    id: int = Field(..., description="TMDB movie ID")
    title: str
    overview: str = ""
    tagline: str = ""
    poster_url: str = ""
    backdrop_url: str = ""
    genres: list[str] = []
    moods: list[str] = []
    year: int | None = None
    vote_average: float = 0.0
    vote_count: int = 0
    runtime: int | None = None  # minutes
    imdb_id: str = ""
    imdb_rating: float | None = None
    rotten_tomatoes_score: str = ""
    metascore: str = ""
    director: str = ""
    writer: str = ""
    producers: list[str] = []
    cast: list[str] = []
    budget: int = 0
    revenue: int = 0
    certification: str = ""
    trailer_url: str = ""
    match_percentage: int | None = None
    match_reason: str = ""


class MovieSearchResponse(BaseModel):
    movies: list[Movie]
    total: int
    page: int
    query: str


class SimilarMoviesResponse(BaseModel):
    source_movie: Movie
    recommendations: list[Movie]
    engine: str = Field(..., description="'content', 'hybrid', 'bayesian_mmr', or 'fallback'")


class RatedMovie(BaseModel):
    """A movie the user has rated (sent from client for personalised recs)."""

    movie_id: int
    rating: float = Field(..., ge=0.5, le=10.0)


class PersonalisedRequest(BaseModel):
    ratings: list[RatedMovie] = Field(..., min_length=1)
    n: int = Field(default=10, ge=1, le=24)
    diversity_lambda: float = Field(default=0.75, ge=0.0, le=1.0)


class PersonalisedResponse(BaseModel):
    recommendations: list[Movie]
    engine: str
    user_top_genres: list[str] = []


class MoodRecommendationsResponse(BaseModel):
    mood: str
    recommendations: list[Movie]
    total: int
