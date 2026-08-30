"""
tests/test_preprocessing.py — Test data processing pipeline and feature extraction.
"""

import sys
import tempfile
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing import (
    build_tags_dataframe,
    _safe_convert,
    _safe_convert_cast,
    _safe_fetch_crew_roles,
    _compute_mood_tags,
    _parse_delimited_or_json,
)


def test_safe_convert():
    # JSON list of dicts
    raw_json = '[{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}]'
    assert _safe_convert(raw_json) == ["Action", "Adventure"]

    # Comma-separated string format (TMDB Daily format)
    raw_csv = "Action, Adventure, Science Fiction"
    assert _safe_convert(raw_csv) == ["Action", "Adventure", "Science Fiction"]

    # Pipe-separated format
    raw_pipe = "Action|Adventure|Fantasy"
    assert _safe_convert(raw_pipe) == ["Action", "Adventure", "Fantasy"]

    assert _safe_convert("") == []
    assert _safe_convert(None) == []


def test_safe_convert_cast():
    raw_json = '[{"name": "Sam Worthington"}, {"name": "Zoe Saldana"}, {"name": "Sigourney Weaver"}]'
    assert _safe_convert_cast(raw_json, top_k=2) == ["Sam Worthington", "Zoe Saldana"]

    # Comma-separated cast string (TMDB Daily format)
    raw_csv = "Sam Worthington, Zoe Saldana, Sigourney Weaver, Stephen Lang"
    assert _safe_convert_cast(raw_csv, top_k=3) == ["Sam Worthington", "Zoe Saldana", "Sigourney Weaver"]


def test_safe_fetch_crew_roles():
    raw = '[{"job": "Director", "name": "James Cameron"}, {"job": "Writer", "name": "James Cameron"}, {"job": "Producer", "name": "Jon Landau"}]'
    director, writer, producers = _safe_fetch_crew_roles(raw)
    assert director == "James Cameron"
    assert writer == "James Cameron"
    assert "Jon Landau" in producers


def test_compute_mood_tags():
    moods = _compute_mood_tags(["Science Fiction", "Mystery"], ["space", "time travel"], "A mind-bending journey")
    assert "mind-bending" in moods

    moods_action = _compute_mood_tags(["Action", "Adventure"], ["superhero", "explosion"], "An action packed fight")
    assert "adrenaline-action" in moods_action


def test_build_tags_dataframe_tmdb5000():
    raw_dir = PROJECT_ROOT / "data" / "raw"
    df = build_tags_dataframe(raw_dir=raw_dir, dataset="tmdb5000")
    
    assert not df.empty
    # Must have single movie_id column
    assert df.columns.tolist().count("movie_id") == 1
    assert "tags" in df.columns
    assert "director" in df.columns
    assert "cast" in df.columns
    assert "moods" in df.columns
    assert len(df) > 4000


def test_build_tags_dataframe_tmdb_daily_mock():
    """Verify ingestion of Alan Vourch's TMDB Daily format."""
    mock_data = pd.DataFrame([
        {
            "id": 19995,
            "title": "Avatar",
            "vote_average": 7.5,
            "vote_count": 18000,
            "status": "Released",
            "release_date": "2009-12-15",
            "revenue": 2787965087,
            "runtime": 162,
            "adult": "False",
            "backdrop_path": "/vL5LR6WdxWPjZRFRCm40crEjTe.jpg",
            "budget": 237000000,
            "imdb_id": "tt0499549",
            "overview": "In the 22nd century, a paraplegic Marine is dispatched to the moon Pandora on a unique mission.",
            "popularity": 185.0,
            "poster_path": "/jRXYjXNq0Cs2TcJjLkki24MLPu.jpg",
            "tagline": "Enter the World of Pandora.",
            "genres": "Action, Adventure, Fantasy, Science Fiction",
            "cast": "Sam Worthington, Zoe Saldana, Sigourney Weaver, Stephen Lang",
            "director": "James Cameron",
            "writers": "James Cameron",
            "keywords": "alien, moon, space warfare, marine, tribe",
            "imdb_rating": 7.9,
        },
        {
            "id": 157336,
            "title": "Interstellar",
            "vote_average": 8.4,
            "vote_count": 32000,
            "status": "Released",
            "release_date": "2014-11-05",
            "revenue": 701729206,
            "runtime": 169,
            "adult": "False",
            "backdrop_path": "/rAiYTgg0kW6CH6Zf5vrMEi0tV1.jpg",
            "budget": 165000000,
            "imdb_id": "tt0816692",
            "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole.",
            "popularity": 140.0,
            "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
            "tagline": "Mankind was born on Earth. It was never meant to die here.",
            "genres": "Adventure, Drama, Science Fiction",
            "cast": "Matthew McConaughey, Anne Hathaway, Jessica Chastain",
            "director": "Christopher Nolan",
            "writers": "Jonathan Nolan, Christopher Nolan",
            "keywords": "wormhole, black hole, time dilation, astronaut, physics",
            "imdb_rating": 8.7,
        }
    ])

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        mock_data.to_csv(f.name, index=False)
        temp_csv = Path(f.name)

    try:
        processed_df = build_tags_dataframe(
            raw_dir=temp_csv.parent,
            dataset="tmdb_daily",
            archive_path=temp_csv,
            vote_threshold=10,
        )

        assert len(processed_df) == 2
        assert "movie_id" in processed_df.columns
        assert "tags" in processed_df.columns
        assert "director" in processed_df.columns
        assert processed_df.iloc[0]["director"] == "James Cameron"
        assert processed_df.iloc[1]["director"] == "Christopher Nolan"
        assert "mind-bending" in processed_df.iloc[1]["moods"]
        assert len(processed_df.iloc[0]["genres"]) == 4
        assert len(processed_df.iloc[0]["cast"]) >= 3
        # Check financial and classification enrichment
        assert processed_df.iloc[0]["profit"] > 0
        assert processed_df.iloc[0]["runtime_category"] == "Epic"
        assert processed_df.iloc[0]["decade"] == 2000
        assert processed_df.iloc[1]["decade"] == 2010
        assert "bayesian_rating" in processed_df.columns
    finally:
        if temp_csv.exists():
            temp_csv.unlink()


def test_sanitize_text_and_entities():
    from src.preprocessing import sanitize_text, clean_ascii_tokens

    assert sanitize_text("<b>Avatar</b> &amp; Titanic &quot;Epic&quot;") == "Avatar & Titanic \"Epic\""
    assert sanitize_text("  Spaced   Out   \n Text  ") == "Spaced Out Text"
    assert sanitize_text(None) == ""
    assert sanitize_text("nan") == ""
    assert sanitize_text("null") == ""

    # Accent cleaning
    assert clean_ascii_tokens("Ménage à Trois") == "Menage a Trois"
    assert clean_ascii_tokens("Amélie") == "Amelie"


def test_clean_raw_dataframe_filters_and_deduplication():
    from src.preprocessing import clean_raw_dataframe

    raw = pd.DataFrame([
        # Valid movie
        {
            "id": 1,
            "title": "The Matrix",
            "overview": "A computer hacker learns about the true nature of reality.",
            "vote_count": 1000,
            "vote_average": 8.7,
            "status": "Released",
            "release_date": "1999-03-31",
            "imdb_id": "tt0133093",
            "budget": 63000000,
            "revenue": 463517383,
            "runtime": 136,
            "adult": "False",
        },
        # Duplicate TMDB ID with lower votes
        {
            "id": 1,
            "title": "The Matrix Duplicate",
            "overview": "A computer hacker learns about reality duplicate.",
            "vote_count": 50,
            "vote_average": 6.0,
            "status": "Released",
            "release_date": "1999-03-31",
            "imdb_id": "tt0133093",
            "budget": 63000000,
            "revenue": 463517383,
            "runtime": 136,
            "adult": "False",
        },
        # Duplicate by IMDb ID
        {
            "id": 999,
            "title": "The Matrix (IMDb Dup)",
            "overview": "A computer hacker learns about the true nature of reality again.",
            "vote_count": 500,
            "vote_average": 8.5,
            "status": "Released",
            "release_date": "1999-03-31",
            "imdb_id": "tt0133093",
            "budget": 63000000,
            "revenue": 463517383,
            "runtime": 136,
            "adult": "False",
        },
        # Placeholder title
        {
            "id": 2,
            "title": "Untitled Project",
            "overview": "Some placeholder overview for an untitled film.",
            "vote_count": 100,
            "vote_average": 5.0,
            "status": "Released",
            "release_date": "2020-01-01",
        },
        # Cancelled movie
        {
            "id": 3,
            "title": "Cancelled Movie",
            "overview": "This movie was cancelled in pre-production stages.",
            "vote_count": 50,
            "vote_average": 5.0,
            "status": "Canceled",
            "release_date": "2021-01-01",
        },
        # Low votes
        {
            "id": 4,
            "title": "Unvoted Film",
            "overview": "Nobody has seen or voted for this obscure film.",
            "vote_count": 2,
            "vote_average": 5.0,
            "status": "Released",
            "release_date": "2022-01-01",
        },
    ])

    clean = clean_raw_dataframe(raw, min_votes=15, released_only=True)
    assert len(clean) == 1
    assert clean.iloc[0]["movie_id"] == 1
    assert clean.iloc[0]["title"] == "The Matrix"
    assert clean.iloc[0]["decade"] == 1990
    assert clean.iloc[0]["runtime_category"] == "Feature"
    assert clean.iloc[0]["profit"] == 463517383 - 63000000
    assert clean.iloc[0]["is_profitable"] is True
    assert clean.iloc[0]["roi"] > 5.0

