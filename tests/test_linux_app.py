"""tests/test_linux_app.py — Automated tests for Linux Native Desktop application components."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from linux.app.db import LocalDatabase
from linux.app.engine import LinuxEngine
from linux.app.image_loader import ImageLoader
from linux.app.state import AppState


def test_linux_app_state_persistence(tmp_path: Path):
    """Test saving and restoring window state."""
    state_file = tmp_path / "test_state.json"
    
    state = AppState(
        window_width=1280,
        window_height=800,
        window_maximized=True,
        active_view="mood",
    )
    
    # Save to custom file
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state.__dict__, f)
        
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["window_width"] == 1280
    assert data["window_height"] == 800
    assert data["window_maximized"] is True
    assert data["active_view"] == "mood"


def test_linux_local_database_operations(tmp_path: Path):
    """Test local SQLite watchlist, watched history, ratings, and export/import."""
    db_file = tmp_path / "test_db.sqlite"
    db = LocalDatabase(db_file)

    # 1. Watchlist operations
    assert not db.is_in_watchlist(101)
    added = db.add_to_watchlist(
        movie_id=101,
        title="Inception",
        year=2010,
        poster_path="/inception.jpg",
        vote_average=8.4,
    )
    assert added is True
    assert db.is_in_watchlist(101)

    wl = db.get_watchlist()
    assert len(wl) == 1
    assert wl[0].title == "Inception"
    assert wl[0].year == 2010

    # 2. Watched operations
    assert not db.is_watched(101)
    marked = db.mark_as_watched(
        movie_id=101,
        title="Inception",
        year=2010,
        poster_path="/inception.jpg",
        vote_average=8.4,
        user_rating=5.0,
        notes="Masterpiece sci-fi film",
    )
    assert marked is True
    assert db.is_watched(101)
    # Marked as watched should automatically remove from watchlist
    assert not db.is_in_watchlist(101)

    watched_list = db.get_watched()
    assert len(watched_list) == 1
    assert watched_list[0].user_rating == 5.0
    assert watched_list[0].notes == "Masterpiece sci-fi film"

    # 3. Export to JSON & Markdown
    json_export = tmp_path / "export.json"
    md_export = tmp_path / "export.md"
    csv_export = tmp_path / "export.csv"

    assert db.export_data(json_export, format="json") is True
    assert db.export_data(md_export, format="markdown") is True
    assert db.export_data(csv_export, format="csv") is True

    assert json_export.exists() and json_export.stat().st_size > 0
    assert md_export.exists() and md_export.stat().st_size > 0
    assert csv_export.exists() and csv_export.stat().st_size > 0

    # 4. Import back into a fresh DB
    fresh_db = LocalDatabase(tmp_path / "fresh_db.sqlite")
    imported_count = fresh_db.import_data(json_export)
    assert imported_count >= 1
    assert fresh_db.is_watched(101)


def test_linux_engine_queries():
    """Test LinuxEngine catalog loading, discovery, filtering, and recommendations."""
    engine = LinuxEngine()
    loaded = engine.load()
    assert loaded is True
    assert engine.is_loaded is True
    assert engine.movies_df is not None and len(engine.movies_df) > 0

    # Hero & Trending
    hero = engine.get_hero_movie()
    assert hero is not None
    assert "title" in hero and "movie_id" in hero

    trending = engine.get_trending(n=5)
    assert len(trending) == 5

    # Mood filter
    mood_recs = engine.get_by_mood("mind-bending", n=6)
    assert len(mood_recs) == 6

    # Search
    results = engine.search(query="Inception", limit=5)
    assert len(results) >= 1
    assert any("Inception" in r["title"] for r in results)

    # Multi-filter search (Genre + Sort)
    action_results = engine.search(genre="Action", sort_by="rating", limit=5)
    assert len(action_results) == 5
    assert all("Action" in r["genres"] for r in action_results)

    # Similar recommendations
    sims = engine.get_similar("Inception", n=5)
    assert len(sims) == 5
    for s in sims:
        assert "match_percentage" in s
        assert "match_reason" in s


def test_linux_image_loader_caching(tmp_path: Path):
    """Test ImageLoader local cache directory and cache pruning."""
    cache_dir = tmp_path / "image_cache"
    loader = ImageLoader(cache_dir=cache_dir)
    assert cache_dir.exists()
    assert loader.cache_dir == cache_dir


def test_linux_theme_manager():
    """Test ThemeManager palettes and dynamic theme selection."""
    from linux.app.theme_manager import THEMES, theme_manager

    assert len(THEMES) >= 6
    assert "catppuccin" in THEMES
    assert "nord" in THEMES
    assert "dracula" in THEMES
    assert "oled" in THEMES
    assert "sunset" in THEMES
    assert "adwaita_light" in THEMES

    # Check theme properties
    cat = theme_manager.get_theme("catppuccin")
    assert cat.is_dark is True
    assert cat.accent_color == "#89b4fa"

    nord = theme_manager.get_theme("nord")
    assert nord.is_dark is True
    assert nord.accent_color == "#88c0d0"

    all_th = theme_manager.get_all_themes()
    assert len(all_th) >= 6


def test_linux_movie_chat_engine():
    """Test contextual Q&A responses generated by MovieChatEngine."""
    from linux.app.chat_engine import MovieChatEngine

    movie = {
        "movie_id": 101,
        "title": "Inception",
        "year": 2010,
        "director": "Christopher Nolan",
        "genres": ["Action", "Science Fiction"],
        "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
        "overview": "A thief who steals corporate secrets through dream-sharing technology.",
        "mood_tags": ["mind-bending", "adrenaline-action"],
        "vote_average": 8.4,
        "vote_count": 35000,
        "budget": 160000000,
        "revenue": 825532764,
        "profit": 665532764,
    }
    chat = MovieChatEngine(movie)

    # Test director inquiry
    ans_dir = chat.answer_question("Who directed this movie?")
    assert "Christopher Nolan" in ans_dir

    # Test plot inquiry
    ans_plot = chat.answer_question("What is the plot about?")
    assert "dream-sharing technology" in ans_plot

    # Test financial inquiry
    ans_fin = chat.answer_question("What was the box office profit?")
    assert "Profit:" in ans_fin or "Gross:" in ans_fin

    # Test recommendation verdict
    ans_verdict = chat.answer_question("Why should I watch it?")
    assert "Verdict:" in ans_verdict


def test_linux_marathon_generator():
    """Test 5-movie playlist sequence generation by MarathonGenerator."""
    from linux.app.marathon import marathon_generator

    marathon = marathon_generator.generate_marathon(["mind-bending", "epic-journey"], max_movies=5)
    assert marathon is not None
    assert len(marathon.steps) == 5
    assert marathon.total_runtime_mins > 0
    assert "Opening Hook" in marathon.steps[0].slot


def test_linux_advanced_search_syntax():
    """Test advanced query tokens in LinuxEngine."""
    from linux.app.engine import LinuxEngine

    engine = LinuxEngine()
    engine.load()

    # Director query
    nolan_results = engine.search("director:nolan >2010", limit=5)
    assert len(nolan_results) > 0
    assert all("Nolan" in str(r.get("director", "")) for r in nolan_results)
    assert all(r.get("year", 0) >= 2010 for r in nolan_results)

    # Actor query
    leo_results = engine.search("actor:dicaprio", limit=5)
    assert len(leo_results) > 0
    assert all(any("dicaprio" in a.lower() for a in r.get("cast", [])) for r in leo_results)


