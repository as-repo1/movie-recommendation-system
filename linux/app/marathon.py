"""linux/app/marathon.py — AI Movie Marathon and Playlist Sequence Generator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from linux.app.engine import engine

logger = logging.getLogger(__name__)


@dataclass
class MarathonStep:
    slot: str  # e.g., "1. The Opening Hook", "2. The Deep Dive", "3. The Core Masterpiece", "4. The Climax", "5. The Cooldown"
    movie: dict[str, Any]
    rationale: str


@dataclass
class MovieMarathon:
    title: str
    moods: list[str]
    total_runtime_mins: int
    steps: list[MarathonStep]


class MarathonGenerator:
    """Generates intelligent 5-film viewing marathons tailored by mood and pacing."""

    SLOTS = [
        ("1. The Opening Hook", "High-energy opener to immerse you immediately"),
        ("2. The Atmosphere Builder", "Expands narrative depth and emotional investment"),
        ("3. The Core Masterpiece", "The heavyweight pinnacle of the marathon"),
        ("4. The Mind-Bending Climax", "Peak tension and unforgettable twists"),
        ("5. The Cathartic Finale", "Satisfying cooldown to conclude the cinematic marathon"),
    ]

    def generate_marathon(self, selected_moods: list[str], max_movies: int = 5) -> MovieMarathon | None:
        """Create a 5-movie paced playlist from selected moods."""
        if not engine.is_loaded:
            engine.load()

        if not selected_moods:
            selected_moods = ["mind-bending", "epic-journey"]

        candidates: list[dict[str, Any]] = []
        for mood in selected_moods:
            movies = engine.get_by_mood(mood, n=15)
            candidates.extend(movies)


        # Deduplicate candidates
        seen_ids = set()
        unique_candidates = []
        for m in candidates:
            if m["movie_id"] not in seen_ids:
                seen_ids.add(m["movie_id"])
                unique_candidates.append(m)

        if len(unique_candidates) < max_movies:
            # Fallback to trending
            trending = engine.get_trending(n=max_movies)
            for m in trending:
                if m["movie_id"] not in seen_ids:
                    seen_ids.add(m["movie_id"])
                    unique_candidates.append(m)

        # Select 5 best pacing candidates
        selected = unique_candidates[:max_movies]
        steps = []
        total_runtime = 0

        for i, m in enumerate(selected):
            slot_name, rationale = self.SLOTS[i % len(self.SLOTS)]
            rt = m.get("runtime") or 110
            total_runtime += rt
            steps.append(MarathonStep(slot=slot_name, movie=m, rationale=rationale))

        mood_title = " & ".join(m.replace("-", " ").title() for m in selected_moods)
        return MovieMarathon(
            title=f"The {mood_title} Marathon Experience",
            moods=selected_moods,
            total_runtime_mins=total_runtime,
            steps=steps,
        )


marathon_generator = MarathonGenerator()
