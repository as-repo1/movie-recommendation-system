"""
tests/test_api.py — Integration tests for FastAPI endpoints.
"""

import sys
import uuid
from pathlib import Path
import pytest
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.core.database import init_db
from app.services.recommender import recommendation_service


@pytest.fixture(scope="session", autouse=True)
async def setup_test_app():
    recommendation_service.load()
    await init_db()


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["content_model"] is True


@pytest.mark.asyncio
async def test_popular_movies():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/movies/popular")
        assert r.status_code == 200
        movies = r.json()
        assert len(movies) > 0
        assert "title" in movies[0]
        assert "id" in movies[0]
        assert "vote_average" in movies[0]


@pytest.mark.asyncio
async def test_search_movies():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/movies/search?q=Dark Knight")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] > 0
        titles = [m["title"] for m in data["movies"]]
        assert any("Dark Knight" in t for t in titles)


@pytest.mark.asyncio
async def test_movie_genres():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/movies/genres")
        assert r.status_code == 200
        genres = r.json()
        assert "Action" in genres
        assert "Science Fiction" in genres


@pytest.mark.asyncio
async def test_movie_detail():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Avatar TMDB ID: 19995
        r = await client.get("/api/movies/19995")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 19995
        assert "Avatar" in data["title"]
        assert "James Cameron" in data["director"]
        assert len(data["cast"]) > 0


@pytest.mark.asyncio
async def test_similar_recommendations():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/recommendations/similar/19995?n=6")
        assert r.status_code == 200
        data = r.json()
        assert len(data["recommendations"]) == 6
        assert data["source_movie"]["id"] == 19995
        for rec in data["recommendations"]:
            assert rec["match_percentage"] is not None
            assert rec["match_reason"] != ""


@pytest.mark.asyncio
async def test_mood_recommendations():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/recommendations/mood/mind-bending?n=8")
        assert r.status_code == 200
        data = r.json()
        assert data["mood"] == "mind-bending"
        assert len(data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_personalised_recommendations():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        body = {
            "ratings": [
                {"movie_id": 19995, "rating": 9.5},  # Avatar
                {"movie_id": 157336, "rating": 10.0}, # Interstellar
            ],
            "n": 6
        }
        r = await client.post("/api/recommendations/personalised", json=body)
        assert r.status_code == 200
        data = r.json()
        assert len(data["recommendations"]) == 6
        assert "Science Fiction" in data["user_top_genres"]


@pytest.mark.asyncio
async def test_watchlist_and_watched_flow():
    session_id = str(uuid.uuid4())
    headers = {"X-Session-ID": session_id}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers) as client:
        # Add to watchlist
        r = await client.post("/api/watchlist", json={"movie_id": 19995})
        assert r.status_code == 200
        assert 19995 in r.json()

        # Get watchlist
        r = await client.get("/api/watchlist")
        assert r.status_code == 200
        assert 19995 in r.json()

        # Mark watched with rating 9.0 (auto removes from watchlist)
        r = await client.post("/api/watched", json={"movie_id": 19995, "rating": 9.0})
        assert r.status_code == 200
        watched_data = r.json()
        assert "19995" in watched_data or 19995 in watched_data

        # Verify removed from watchlist
        r = await client.get("/api/watchlist")
        assert 19995 not in r.json()

        # DB personalized recs
        r = await client.get("/api/recommendations/personalised?n=5")
        assert r.status_code == 200
        assert len(r.json()["recommendations"]) == 5


@pytest.mark.asyncio
async def test_auth_registration_and_session_migration():
    session_id = str(uuid.uuid4())
    anon_headers = {"X-Session-ID": session_id}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Add item anonymously
        await client.post("/api/watchlist", json={"movie_id": 157336}, headers=anon_headers)

        username = f"user_{uuid.uuid4().hex[:8]}"
        reg_body = {
            "username": username,
            "password": "securepassword123",
            "anonymous_session_id": session_id,
        }
        r = await client.post("/api/auth/register", json=reg_body)
        assert r.status_code == 201
        token_data = r.json()
        token = token_data["access_token"]

        # Check /me with token
        auth_headers = {"Authorization": f"Bearer {token}", "X-Session-ID": session_id}
        me_resp = await client.get("/api/auth/me", headers=auth_headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == username

        # Check migrated watchlist
        wl_resp = await client.get("/api/watchlist", headers=auth_headers)
        assert wl_resp.status_code == 200
        assert 157336 in wl_resp.json()
