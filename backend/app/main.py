"""app/main.py — FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import movies, recommendations, watchlist, watched, auth
from app.core.config import settings
from app.services.recommender import recommendation_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models and initialise database once at startup, release resources on shutdown."""
    recommendation_service.load()
    
    # Run async database table creation
    from app.core.database import init_db
    await init_db()
    
    yield
    # cleanup if needed


app = FastAPI(
    title="RecLens API",
    description="Movie recommendation API — content-based + LightFM hybrid engine.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,            prefix="/api/auth")
app.include_router(movies.router,          prefix="/api/movies")
app.include_router(recommendations.router, prefix="/api/recommendations")
app.include_router(watchlist.router,       prefix="/api/watchlist")
app.include_router(watched.router,         prefix="/api/watched")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "content_model": recommendation_service.is_ready,
        "lightfm_model": recommendation_service.lightfm_ready,
    }


@app.get("/", tags=["system"])
def root():
    return {"message": "RecLens API — visit /docs for the interactive API explorer."}
