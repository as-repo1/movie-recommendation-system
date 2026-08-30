"""
tests/test_preprocessing.py — Test data processing pipeline and feature extraction.
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing import build_tags_dataframe, _safe_convert, _safe_convert_cast, _safe_fetch_crew_roles, _compute_mood_tags


def test_safe_convert():
    raw = '[{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}]'
    assert _safe_convert(raw) == ["Action", "Adventure"]
    assert _safe_convert("") == []
    assert _safe_convert(None) == []


def test_safe_convert_cast():
    raw = '[{"name": "Sam Worthington"}, {"name": "Zoe Saldana"}, {"name": "Sigourney Weaver"}]'
    assert _safe_convert_cast(raw, top_k=2) == ["Sam Worthington", "Zoe Saldana"]


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


def test_build_tags_dataframe():
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
