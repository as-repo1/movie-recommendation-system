"""linux/app/state.py — Application state manager and window geometry persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "reclens"
STATE_FILE = CONFIG_DIR / "state.json"


@dataclass
class AppState:
    window_width: int = 1100
    window_height: int = 750
    window_maximized: bool = False
    active_view: str = "home"
    dark_mode: bool = True
    volume: float = 0.8
    last_query: str = ""

    @classmethod
    def load(cls) -> AppState:
        """Load state from disk or return default state."""
        if not STATE_FILE.exists():
            return cls()
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            return cls(
                window_width=int(data.get("window_width", 1100)),
                window_height=int(data.get("window_height", 750)),
                window_maximized=bool(data.get("window_maximized", False)),
                active_view=str(data.get("active_view", "home")),
                dark_mode=bool(data.get("dark_mode", True)),
                volume=float(data.get("volume", 0.8)),
                last_query=str(data.get("last_query", "")),
            )
        except Exception as e:
            logger.warning("Failed to load application state from %s: %s", STATE_FILE, e)
            return cls()

    def save(self) -> None:
        """Persist state to disk safely."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            logger.error("Failed to save application state: %s", e)
