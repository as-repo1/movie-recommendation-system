"""app/schemas/movie.py — Pydantic schemas shared by all routes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Movie(BaseModel):
    """A single movie record returned by the API."""

    id: int = Field(..., description="TMDB movie ID")
    title: str
    overview: str = ""
    poster_url: str = ""
    backdrop_url: str = ""
    genres: list[str] = []
    year: int | None = None
    vote_average: float = 0.0
    vote_count: int = 0
    runtime: int | None = None  # minutes
    imdb_id: str = ""
    director: str = ""
    writer: str = ""
    cast: list[str] = []


class MovieSearchResponse(BaseModel):
    movies: list[Movie]
    total: int
    page: int
    query: str


class SimilarMoviesResponse(BaseModel):
    source_movie: Movie
    recommendations: list[Movie]
    engine: str = Field(..., description="'content', 'hybrid', or 'fallback'")


class RatedMovie(BaseModel):
    """A movie the user has rated (sent from client for personalised recs)."""

    movie_id: int
    rating: float = Field(..., ge=0.5, le=10.0)


class PersonalisedRequest(BaseModel):
    ratings: list[RatedMovie] = Field(..., min_length=1)
    n: int = Field(default=10, ge=1, le=20)


class PersonalisedResponse(BaseModel):
    recommendations: list[Movie]
    engine: str
