"""
app/services/recommender.py
============================
High-performance Recommendation service with Bayesian rating boosting,
Maximal Marginal Relevance (MMR) diversity re-ranking, Mood matching,
and LightFM Hybrid Collaborative Filtering.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import settings
from app.schemas.movie import Movie, RatedMovie
from src.recommender import recommend as core_recommend, recommend_by_mood as core_recommend_by_mood, _calculate_bayesian_scores, _maximal_marginal_relevance

logger = logging.getLogger(__name__)


class RecommendationService:
    """Singleton service loaded during app startup."""

    def __init__(self) -> None:
        self._movies_df: pd.DataFrame | None = None
        self._similarity: np.ndarray | None = None
        self._bayesian_scores: np.ndarray | None = None
        self._lightfm_model = None
        self._lightfm_dataset = None
        self._id_map: dict[int, int] = {}  # tmdb_id → internal row index
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
        movies_pkl = d / "movies.pkl"
        similarity_pkl = d / "similarity.pkl"
        if not (movies_pkl.exists() and similarity_pkl.exists()):
            logger.warning(
                "Content model not found in %s. Run `python scripts/build_model.py` first.", d
            )
            return
        with open(movies_pkl, "rb") as f:
            self._movies_df = pickle.load(f)
        with open(similarity_pkl, "rb") as f:
            self._similarity = pickle.load(f)

        # Precompute Bayesian rating quality scores
        self._bayesian_scores = _calculate_bayesian_scores(self._movies_df)

        # Build fast TMDB-id → row-index map
        col = "movie_id" if "movie_id" in self._movies_df.columns else "id"
        self._id_map = {int(v): i for i, v in enumerate(self._movies_df[col])}
        self.is_ready = True
        logger.info("Content recommendation engine loaded (%d movies).", len(self._movies_df))

    def _load_lightfm_model(self, d: Path) -> None:
        model_pkl = d / "lightfm_model.pkl"
        dataset_pkl = d / "lightfm_dataset.pkl"
        if not (model_pkl.exists() and dataset_pkl.exists()):
            logger.info("LightFM model not found. Using content-weighted personalization.")
            return
        try:
            with open(model_pkl, "rb") as f:
                self._lightfm_model = pickle.load(f)
            with open(dataset_pkl, "rb") as f:
                self._lightfm_dataset = pickle.load(f)
            self.lightfm_ready = True
            logger.info("LightFM collaborative model loaded.")
        except Exception as e:
            logger.warning("Could not load LightFM model: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # Similar Movies (Content + Quality Prior + MMR)
    # ─────────────────────────────────────────────────────────────────────────

    def similar_movies(
        self,
        movie_id: int,
        n: int = 10,
        use_mmr: bool = True,
    ) -> tuple[list[Movie], str]:
        """Return top-n most similar movies with Bayesian quality boost and MMR diversity."""
        if not self.is_ready or self._movies_df is None or self._similarity is None:
            return [], "unavailable"

        idx = self._id_map.get(movie_id)
        if idx is None:
            return [], "not_in_dataset"

        try:
            raw_recs = core_recommend(
                movie_title_or_id=movie_id,
                movies_df=self._movies_df,
                similarity=self._similarity,
                n=n,
                use_mmr=use_mmr,
                quality_weight=0.20,
            )
            results = [self._dict_to_movie(r) for r in raw_recs]
            return results, "bayesian_mmr"
        except Exception as e:
            logger.error("Error in recommendation generation: %s", e)
            return [], "error"

    # ─────────────────────────────────────────────────────────────────────────
    # Mood Recommendations
    # ─────────────────────────────────────────────────────────────────────────

    def mood_recommendations(self, mood: str, n: int = 12) -> list[Movie]:
        """Return top picks for a specific mood category."""
        if not self.is_ready or self._movies_df is None:
            return []
        raw = core_recommend_by_mood(mood, self._movies_df, n=n)
        return [self._dict_to_movie(r) for r in raw]

    # ─────────────────────────────────────────────────────────────────────────
    # Personalised Hybrid Recommendations
    # ─────────────────────────────────────────────────────────────────────────

    def personalised(
        self,
        ratings: list[RatedMovie],
        n: int = 10,
        diversity_lambda: float = 0.75,
    ) -> tuple[list[Movie], str, list[str]]:
        """Compute personalised recommendations from user rating history."""
        if not self.is_ready or self._movies_df is None:
            return [], "unavailable", []

        # Analyze user top genres
        genre_counts: dict[str, float] = {}
        for r in ratings:
            idx = self._id_map.get(r.movie_id)
            if idx is not None:
                row_genres = self._movies_df.iloc[idx].get("genres", [])
                weight = (r.rating - 5.0)  # positive for >5, negative for <5
                for g in row_genres:
                    genre_counts[g] = genre_counts.get(g, 0.0) + weight

        top_genres = sorted(genre_counts.keys(), key=lambda g: genre_counts[g], reverse=True)[:3]

        if self.lightfm_ready:
            recs, engine = self._lightfm_personalised(ratings, n, diversity_lambda)
            return recs, engine, top_genres

        recs, engine = self._weighted_content(ratings, n, diversity_lambda)
        return recs, engine, top_genres

    def _weighted_content(
        self,
        ratings: list[RatedMovie],
        n: int,
        diversity_lambda: float = 0.75,
    ) -> tuple[list[Movie], str]:
        """Personalized recommendations via user taste profile vector + MMR."""
        n_movies = len(self._movies_df)
        user_profile_scores = np.zeros(n_movies, dtype=np.float32)
        rated_indices: set[int] = set()

        for r in ratings:
            idx = self._id_map.get(r.movie_id)
            if idx is None:
                continue
            rated_indices.add(idx)
            # Centered rating weight (-1.0 to +1.0)
            weight = (r.rating - 5.5) / 4.5
            user_profile_scores += weight * self._similarity[idx]

        if len(rated_indices) == 0 or user_profile_scores.max() <= 0:
            return [], "no_known_movies"

        # Combine with Bayesian quality prior
        combined = (0.75 * user_profile_scores) + (0.25 * self._bayesian_scores)

        # Zero out already-rated movies
        for idx in rated_indices:
            combined[idx] = -float("inf")

        candidate_indices = [
            i for i in np.argsort(combined)[::-1][: max(30, n * 3)]
            if i not in rated_indices and combined[i] > -float("inf")
        ]

        selected_indices = _maximal_marginal_relevance(
            query_scores=combined,
            candidate_indices=candidate_indices,
            similarity_matrix=self._similarity,
            top_k=n,
            diversity_lambda=diversity_lambda,
        )

        results: list[Movie] = []
        for idx in selected_indices:
            row = self._movies_df.iloc[idx]
            match_pct = int(min(98, max(65, (combined[idx] / (user_profile_scores.max() or 1.0)) * 95)))
            m = self._row_to_movie(row)
            m.match_percentage = match_pct
            m.match_reason = f"Matches your taste profile ({', '.join(m.genres[:2])})"
            results.append(m)

        return results, "content_weighted_mmr"

    def _lightfm_personalised(
        self,
        ratings: list[RatedMovie],
        n: int,
        diversity_lambda: float = 0.75,
    ) -> tuple[list[Movie], str]:
        """LightFM matrix factorization with fallback to user profile vector."""
        try:
            from scipy.sparse import csr_matrix

            dataset = self._lightfm_dataset
            item_id_map: dict = dataset.mapping()[2]  # tmdb_id → internal item id
            n_items = len(item_id_map)

            rows, cols, data = [], [], []
            rated_set = {r.movie_id for r in ratings}

            for r in ratings:
                item_id = item_id_map.get(r.movie_id)
                if item_id is not None:
                    rows.append(0)
                    cols.append(item_id)
                    data.append(r.rating / 10.0)

            if not rows:
                return self._weighted_content(ratings, n, diversity_lambda)

            user_interactions = csr_matrix((data, (rows, cols)), shape=(1, n_items))
            scores = self._lightfm_model.predict(
                user_ids=0,
                item_ids=np.arange(n_items),
                user_features=user_interactions,
            )

            reverse_item_map = {v: k for k, v in item_id_map.items()}
            ranked_item_ids = np.argsort(-scores)

            results: list[Movie] = []
            for item_id in ranked_item_ids:
                if len(results) >= n:
                    break
                tmdb_id = reverse_item_map.get(int(item_id))
                if tmdb_id is None or tmdb_id in rated_set:
                    continue
                row_idx = self._id_map.get(tmdb_id)
                if row_idx is not None:
                    m = self._row_to_movie(self._movies_df.iloc[row_idx])
                    m.match_percentage = int(min(99, max(70, scores[item_id] * 20 + 75)))
                    m.match_reason = "Collaborative filtering affinity match"
                    results.append(m)

            return results, "lightfm_hybrid"
        except Exception as e:
            logger.warning("LightFM inference failed: %s; falling back to content-weighted.", e)
            return self._weighted_content(ratings, n, diversity_lambda)

    # ─────────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────────

    def _row_to_movie(self, row: pd.Series) -> Movie:
        def _to_str_list(val) -> list[str]:
            if isinstance(val, (list, tuple, np.ndarray, set)):
                return [str(x) for x in val if x is not None and str(x).strip()]
            return []

        genres = _to_str_list(row.get("genres", []))
        moods = _to_str_list(row.get("moods", []))
        cast = _to_str_list(row.get("cast", []))

        poster_path = str(row.get("poster_path", "") or "").strip()
        poster_url = f"https://image.tmdb.org/t/p/w500/{poster_path.lstrip('/')}" if poster_path and poster_path != "nan" else ""

        return Movie(
            id=int(row["movie_id"]),
            title=str(row["title"]).strip(),
            overview=str(row.get("overview", "")),
            tagline=str(row.get("tagline", "")),
            genres=genres,
            moods=moods,
            year=int(row["year"]) if pd.notna(row.get("year")) and row.get("year") else None,
            vote_average=float(row.get("vote_average", 0)),
            vote_count=int(row.get("vote_count", 0)),
            runtime=int(row["runtime"]) if pd.notna(row.get("runtime")) and row.get("runtime") else None,
            poster_url=poster_url,
            director=str(row.get("director", "")),
            writer=str(row.get("writer", "")),
            cast=cast,
            budget=int(row.get("budget", 0)) if str(row.get("budget", "")).isdigit() else 0,
            revenue=int(row.get("revenue", 0)) if str(row.get("revenue", "")).isdigit() else 0,
        )

    def _dict_to_movie(self, d: dict[str, Any]) -> Movie:
        def _to_str_list(val) -> list[str]:
            if isinstance(val, (list, tuple, np.ndarray, set)):
                return [str(x) for x in val if x is not None and str(x).strip()]
            return []

        return Movie(
            id=int(d["movie_id"]),
            title=str(d["title"]),
            overview=str(d.get("overview", "")),
            tagline=str(d.get("tagline", "")),
            genres=_to_str_list(d.get("genres", [])),
            moods=_to_str_list(d.get("moods", [])),
            year=d.get("year"),
            vote_average=float(d.get("vote_average", 0)),
            vote_count=int(d.get("vote_count", 0)),
            director=str(d.get("director", "")),
            writer=str(d.get("writer", "")),
            cast=_to_str_list(d.get("cast", [])),
            match_percentage=d.get("match_percentage"),
            match_reason=d.get("match_reason", ""),
        )


    def get_all_titles(self) -> list[dict]:
        """Return a lightweight list of all movies for search dropdown."""
        if not self.is_ready or self._movies_df is None:
            return []
        return [
            {
                "id": int(r["movie_id"]),
                "title": str(r["title"]),
                "year": int(r["year"]) if pd.notna(r.get("year")) and r.get("year") else None,
                "genres": r.get("genres", [])[:2] if isinstance(r.get("genres"), list) else [],
            }
            for _, r in self._movies_df.iterrows()
        ]


# Singleton instance
recommendation_service = RecommendationService()
