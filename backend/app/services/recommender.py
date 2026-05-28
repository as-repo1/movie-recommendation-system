"""
app/services/recommender.py
============================
Recommendation service loaded once at app startup (FastAPI lifespan).

Provides:
  • similar_movies(movie_id, n)     — content-based TF-IDF
  • personalised(ratings, n)        — hybrid LightFM + content
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import settings
from app.schemas.movie import Movie, RatedMovie

logger = logging.getLogger(__name__)


class RecommendationService:
    """Singleton service; call ``load()`` once during startup."""

    def __init__(self) -> None:
        self._movies_df: pd.DataFrame | None = None
        self._similarity: np.ndarray | None = None
        self._lightfm_model = None
        self._lightfm_dataset = None
        self._id_map: dict[int, int] | None = None  # tmdb_id → internal idx
        self.is_ready = False
        self.lightfm_ready = False

    # ─────────────────────────────────────────────────────────────────────────
    # Startup
    # ─────────────────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load all available model artefacts."""
        pd_dir = settings.processed_dir
        self._load_content_model(pd_dir)
        self._load_lightfm_model(pd_dir)

    def _load_content_model(self, d: Path) -> None:
        movies_pkl    = d / "movies.pkl"
        similarity_pkl = d / "similarity.pkl"
        if not (movies_pkl.exists() and similarity_pkl.exists()):
            logger.warning(
                "Content model not found in %s. Run `python scripts/build_model.py` first.", d
            )
            return
        self._movies_df = pd.read_pickle(movies_pkl)
        self._similarity = pickle.loads(similarity_pkl.read_bytes())
        # Build fast TMDB-id → row-index map
        col = "movie_id" if "movie_id" in self._movies_df.columns else "id"
        self._id_map = {int(v): i for i, v in enumerate(self._movies_df[col])}
        self.is_ready = True
        logger.info("Content model loaded (%d movies).", len(self._movies_df))

    def _load_lightfm_model(self, d: Path) -> None:
        model_pkl   = d / "lightfm_model.pkl"
        dataset_pkl = d / "lightfm_dataset.pkl"
        if not (model_pkl.exists() and dataset_pkl.exists()):
            logger.info(
                "LightFM model not found. Run `python scripts/train_lightfm.py` for personalised recs."
            )
            return
        with open(model_pkl, "rb") as f:
            self._lightfm_model = pickle.load(f)
        with open(dataset_pkl, "rb") as f:
            self._lightfm_dataset = pickle.load(f)
        self.lightfm_ready = True
        logger.info("LightFM model loaded.")

    # ─────────────────────────────────────────────────────────────────────────
    # Content-based
    # ─────────────────────────────────────────────────────────────────────────

    def similar_movies(self, movie_id: int, n: int = 10) -> tuple[list[Movie], str]:
        """Return the top-n most similar movies to ``movie_id``."""
        if not self.is_ready:
            return [], "unavailable"

        idx = self._id_map.get(movie_id)
        if idx is None:
            return [], "not_in_dataset"

        scores = self._similarity[idx]
        ranked = np.argsort(scores)[::-1]

        results: list[Movie] = []
        for i in ranked[1:]:
            if len(results) >= n:
                break
            row = self._movies_df.iloc[int(i)]
            results.append(self._row_to_movie(row))
        return results, "content"

    # ─────────────────────────────────────────────────────────────────────────
    # Personalised (hybrid)
    # ─────────────────────────────────────────────────────────────────────────

    def personalised(self, ratings: list[RatedMovie], n: int = 10) -> tuple[list[Movie], str]:
        """
        Return personalised recommendations given a list of user ratings.
        Falls back to content-based aggregation when LightFM is unavailable.
        """
        if not self.is_ready:
            return [], "unavailable"

        if self.lightfm_ready:
            return self._lightfm_personalised(ratings, n)

        # Fallback: aggregate content-based scores weighted by user rating
        return self._weighted_content(ratings, n)

    def _weighted_content(
        self, ratings: list[RatedMovie], n: int
    ) -> tuple[list[Movie], str]:
        """Weighted average of content similarity rows for rated movies."""
        agg = np.zeros(len(self._movies_df))
        rated_indices: set[int] = set()

        for r in ratings:
            idx = self._id_map.get(r.movie_id)
            if idx is None:
                continue
            rated_indices.add(idx)
            weight = r.rating / 10.0
            agg += weight * self._similarity[idx]

        if agg.sum() == 0:
            return [], "no_known_movies"

        # Zero out already-rated movies
        for idx in rated_indices:
            agg[idx] = 0

        top_indices = np.argsort(agg)[::-1][:n]
        results = [self._row_to_movie(self._movies_df.iloc[int(i)]) for i in top_indices]
        return results, "content_weighted"

    def _lightfm_personalised(
        self, ratings: list[RatedMovie], n: int
    ) -> tuple[list[Movie], str]:
        """LightFM inference: create a virtual user from supplied ratings."""
        from lightfm import LightFM
        from scipy.sparse import csr_matrix

        dataset = self._lightfm_dataset
        item_id_map: dict = dataset.mapping()[2]  # tmdb_id → internal item id
        n_items = len(item_id_map)

        # Build a sparse interaction row for the virtual user
        rows, cols, data = [], [], []
        for r in ratings:
            item_id = item_id_map.get(r.movie_id)
            if item_id is None:
                continue
            rows.append(0)
            cols.append(item_id)
            data.append(r.rating / 10.0)

        if not rows:
            return self._weighted_content(ratings, n)

        user_interactions = csr_matrix((data, (rows, cols)), shape=(1, n_items))
        scores = self._lightfm_model.predict(
            user_ids=0,
            item_ids=np.arange(n_items),
            user_features=user_interactions,
        )

        # Map internal item IDs back to TMDB IDs
        reverse_item_map = {v: k for k, v in item_id_map.items()}
        top_item_ids = np.argsort(-scores)
        rated_set = {r.movie_id for r in ratings}

        results: list[Movie] = []
        for item_id in top_item_ids:
            if len(results) >= n:
                break
            tmdb_id = reverse_item_map.get(int(item_id))
            if tmdb_id is None or tmdb_id in rated_set:
                continue
            movie = self._get_movie_by_id(tmdb_id)
            if movie:
                results.append(movie)

        return results, "lightfm_hybrid"

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_movie_by_id(self, movie_id: int) -> Movie | None:
        idx = self._id_map.get(movie_id)
        if idx is None:
            return None
        return self._row_to_movie(self._movies_df.iloc[idx])

    def _row_to_movie(self, row: pd.Series) -> Movie:
        import ast, re
        from app.services.movie_db import PLACEHOLDER

        def _parse_genres(val) -> list[str]:
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    parsed = ast.literal_eval(val)
                    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                        return [g["name"] for g in parsed]
                    return parsed  # already a list of strings
                except Exception:
                    return []
            return []

        title = str(row.get("title", ""))
        year_match = re.search(r"\((\d{4})\)$", title)
        year = int(year_match.group(1)) if year_match else None

        return Movie(
            id=int(row.get("movie_id", row.get("id", 0))),
            title=title.strip(),
            overview=str(row.get("overview", "")),
            genres=_parse_genres(row.get("genres", [])),
            year=year,
            vote_average=float(row.get("vote_average", 0)),
            vote_count=int(row.get("vote_count", 0)),
            runtime=int(row["runtime"]) if pd.notna(row.get("runtime")) else None,
            poster_url=PLACEHOLDER,
            director="",
            writer="",
            cast=[],
        )

    def get_all_titles(self) -> list[dict]:
        """Return a lightweight list of all movies for the search dropdown."""
        if not self.is_ready:
            return []
        col = "movie_id" if "movie_id" in self._movies_df.columns else "id"
        return [
            {"id": int(r[col]), "title": str(r["title"])}
            for _, r in self._movies_df.iterrows()
        ]


# Singleton — imported by main.py and injected into routes via deps.py
recommendation_service = RecommendationService()
