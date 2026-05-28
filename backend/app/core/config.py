"""app/core/config.py — centralised settings via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── API keys (both optional — app degrades gracefully without them) ──────
    tmdb_api_key: str = ""
    omdb_api_key: str = ""

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = ""

    # ── Security & Authentication ────────────────────────────────────────────
    secret_key: str = "supersecret_key_change_me_in_production"
    access_token_expire_minutes: int = 10080  # 1 week (60 * 24 * 7)

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = self.project_root / "data" / "db.sqlite"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"

    # ── Data paths (absolute or relative to project root) ───────────────────
    project_root: Path = Path(__file__).resolve().parents[3]


    @property
    def processed_dir(self) -> Path:
        return self.project_root / "data" / "processed"

    @property
    def raw_dir(self) -> Path:
        return self.project_root / "data" / "raw"

    # ── ML settings ──────────────────────────────────────────────────────────
    max_recommendations: int = 20
    default_recommendations: int = 10

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost"]


settings = Settings()
