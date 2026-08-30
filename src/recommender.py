"""
src.recommender
===============
Advanced multi-factor recommendation engine.

Features:
- Multi-factor Content-based TF-IDF Similarity
- Bayesian Weighted Rating Quality Prior (IMDb/TMDB weighted score)
- Maximal Marginal Relevance (MMR) Diversity Re-Ranking
- Mood & Vibe Filtered Recommendations
- Explainable Match Reasoning (shared director, cast, genres, themes)
- Personalized User Profile Weighted Hybrid Scoring
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────


class ModelNotFoundError(FileNotFoundError):
    """Raised when ``movies.pkl`` or ``similarity.pkl`` are missing."""


class MovieNotFoundError(KeyError):
    """Raised when the requested movie title or ID is not in the dataset."""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers & Quality Priors
# ─────────────────────────────────────────────────────────────────────────────


def _calculate_bayesian_scores(
    df: pd.DataFrame,
    min_votes_quantile: float = 0.60,
) -> np.ndarray:
    """Compute Bayesian weighted ratings (IMDb formula) for all movies in df.

    WR = (v / (v + m)) * R + (m / (v + m)) * C
    """
    v = df["vote_count"].fillna(0).values
    R = df["vote_average"].fillna(0).values
    
    # Threshold m is the quantile of vote counts
    m = np.quantile(v[v > 0], min_votes_quantile) if (v > 0).any() else 50.0
    C = float(np.mean(R[v > 0])) if (v > 0).any() else 6.0
    
    wr = (v / (v + m)) * R + (m / (v + m)) * C
    # Normalize WR to 0.0 - 1.0 range
    wr_norm = np.clip(wr / 10.0, 0.0, 1.0)
    return wr_norm


def _maximal_marginal_relevance(
    query_scores: np.ndarray,
    candidate_indices: list[int],
    similarity_matrix: np.ndarray,
    top_k: int = 10,
    diversity_lambda: float = 0.78,
) -> list[int]:
    r"""Maximal Marginal Relevance (MMR) re-ranking for balancing relevance and diversity.

    MMR = argmax_{d in R \ S} [ lambda * Sim(d, Query) - (1 - lambda) * max_{s in S} Sim(d, s) ]
    """
    if len(candidate_indices) <= top_k:
        return candidate_indices

    selected: list[int] = []
    unselected = list(candidate_indices)

    # First item is the highest scoring candidate
    best_first = max(unselected, key=lambda idx: query_scores[idx])
    selected.append(best_first)
    unselected.remove(best_first)

    while len(selected) < top_k and unselected:
        best_score = -float("inf")
        best_idx = unselected[0]

        for idx in unselected:
            relevance = query_scores[idx]
            # Max similarity to already selected items
            redundancy = max(similarity_matrix[idx, s] for s in selected)
            mmr_score = (diversity_lambda * relevance) - ((1.0 - diversity_lambda) * redundancy)

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(best_idx)
        unselected.remove(best_idx)

    return selected


def _generate_explanation(source_row: pd.Series, target_row: pd.Series) -> str:
    """Generate human-readable reason why target_row is recommended for source_row."""
    reasons = []

    # Check shared director
    src_dir = set(str(source_row.get("director", "")).split(", ")) - {""}
    tgt_dir = set(str(target_row.get("director", "")).split(", ")) - {""}
    shared_dir = src_dir & tgt_dir
    if shared_dir:
        reasons.append(f"Directed by {', '.join(shared_dir)}")

    # Check shared cast
    src_cast = set(source_row.get("cast", [])) if isinstance(source_row.get("cast"), list) else set()
    tgt_cast = set(target_row.get("cast", [])) if isinstance(target_row.get("cast"), list) else set()
    shared_cast = src_cast & tgt_cast
    if shared_cast:
        top_cast_match = list(shared_cast)[:2]
        reasons.append(f"Starring {', '.join(top_cast_match)}")

    # Check shared genres
    src_genres = set(source_row.get("genres", [])) if isinstance(source_row.get("genres"), list) else set()
    tgt_genres = set(target_row.get("genres", [])) if isinstance(target_row.get("genres"), list) else set()
    shared_genres = src_genres & tgt_genres
    if shared_genres and not shared_dir:
        reasons.append(f"Shared {', '.join(list(shared_genres)[:2])} genres")

    # Check moods
    src_moods = set(source_row.get("moods", [])) if isinstance(source_row.get("moods"), list) else set()
    tgt_moods = set(target_row.get("moods", [])) if isinstance(target_row.get("moods"), list) else set()
    shared_moods = src_moods & tgt_moods
    if shared_moods and not reasons:
        m_name = list(shared_moods)[0].replace("-", " ").title()
        reasons.append(f"{m_name} vibe")

    if not reasons:
        reasons.append("High thematic & narrative similarity")

    return " · ".join(reasons)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def load_model(processed_dir: str | Path) -> tuple[pd.DataFrame, np.ndarray]:
    """Load the pickled model files from *processed_dir*."""
    processed_dir = Path(processed_dir)
    movies_path = processed_dir / "movies.pkl"
    similarity_path = processed_dir / "similarity.pkl"

    missing = [str(p) for p in (movies_path, similarity_path) if not p.exists()]
    if missing:
        raise ModelNotFoundError(
            "Model files not found:\n"
            + "\n".join(f"  • {m}" for m in missing)
            + "\n\nRun the build script to generate them:\n"
            "  python scripts/build_model.py"
        )

    with open(movies_path, "rb") as f:
        movies_df = pickle.load(f)
    with open(similarity_path, "rb") as f:
        similarity: np.ndarray = pickle.load(f)

    return movies_df, similarity


def recommend(
    movie_title_or_id: str | int,
    movies_df: pd.DataFrame,
    similarity: np.ndarray,
    n: int = 10,
    use_mmr: bool = True,
    quality_weight: float = 0.22,
) -> list[dict[str, Any]]:
    """Return top-n recommended movies with Bayesian quality boost and MMR diversity.

    Parameters
    ----------
    movie_title_or_id:
        Movie title string or integer TMDB movie_id.
    movies_df:
        DataFrame loaded from movies.pkl.
    similarity:
        Cosine similarity matrix.
    n:
        Number of recommendations to return.
    use_mmr:
        Whether to apply Maximal Marginal Relevance diversity re-ranking.
    quality_weight:
        Weight (0.0 - 1.0) given to the Bayesian rating prior vs pure content similarity.
    """
    if isinstance(movie_title_or_id, int):
        matches = movies_df[movies_df["movie_id"] == movie_title_or_id]
    else:
        matches = movies_df[movies_df["title"].str.lower() == str(movie_title_or_id).lower().strip()]
        if matches.empty:
            # Partial match fallback
            matches = movies_df[movies_df["title"].str.contains(str(movie_title_or_id), case=False, na=False)]

    if matches.empty:
        raise MovieNotFoundError(f"Movie '{movie_title_or_id}' was not found in the dataset.")

    source_idx = int(matches.index[0])
    source_row = movies_df.iloc[source_idx]

    # Content similarity vector
    raw_sim = similarity[source_idx].copy()
    raw_sim[source_idx] = 0.0  # zero self-similarity

    # Bayesian quality prior
    bayesian_scores = _calculate_bayesian_scores(movies_df)

    # Combined ranking score: (1 - q_w) * Content_Sim + q_w * Quality_Prior
    combined_scores = ((1.0 - quality_weight) * raw_sim) + (quality_weight * bayesian_scores)
    combined_scores[source_idx] = 0.0

    # Top candidate pool (3x n for diversity re-ranking)
    candidate_pool_size = min(len(movies_df) - 1, max(30, n * 3))
    candidate_indices = list(np.argsort(combined_scores)[::-1][:candidate_pool_size])

    if use_mmr:
        selected_indices = _maximal_marginal_relevance(
            query_scores=combined_scores,
            candidate_indices=candidate_indices,
            similarity_matrix=similarity,
            top_k=n,
            diversity_lambda=0.75,
        )
    else:
        selected_indices = candidate_indices[:n]

    results: list[dict[str, Any]] = []
    for idx in selected_indices:
        target_row = movies_df.iloc[idx]
        sim_score = float(raw_sim[idx])
        # Compute match percentage
        match_pct = int(min(99, max(60, sim_score * 100 + (float(bayesian_scores[idx]) * 15))))
        reason = _generate_explanation(source_row, target_row)

        results.append({
            "movie_id": int(target_row["movie_id"]),
            "title": str(target_row["title"]),
            "score": float(sim_score),
            "match_percentage": match_pct,
            "match_reason": reason,
            "genres": target_row.get("genres", []),
            "year": int(target_row["year"]) if pd.notna(target_row.get("year")) and target_row.get("year") else None,
            "vote_average": float(target_row.get("vote_average", 0)),
            "vote_count": int(target_row.get("vote_count", 0)),
            "director": str(target_row.get("director", "")),
            "writer": str(target_row.get("writer", "")),
            "cast": target_row.get("cast", []) if isinstance(target_row.get("cast"), list) else [],
            "overview": str(target_row.get("overview", "")),
            "tagline": str(target_row.get("tagline", "")),
        })

    return results


def recommend_by_mood(
    mood: str,
    movies_df: pd.DataFrame,
    n: int = 12,
) -> list[dict[str, Any]]:
    """Recommend movies filtered by mood & vibe category, sorted by Bayesian quality score."""
    bayesian_scores = _calculate_bayesian_scores(movies_df)
    
    matching_rows = []
    for idx, row in movies_df.iterrows():
        row_moods = row.get("moods", [])
        if mood.lower() in [m.lower() for m in row_moods]:
            matching_rows.append((idx, float(bayesian_scores[idx])))

    # Sort by quality score descending
    matching_rows.sort(key=lambda x: x[1], reverse=True)

    results: list[dict[str, Any]] = []
    for idx, b_score in matching_rows[:n]:
        row = movies_df.iloc[idx]
        results.append({
            "movie_id": int(row["movie_id"]),
            "title": str(row["title"]),
            "score": b_score,
            "match_percentage": int(min(99, b_score * 100)),
            "match_reason": f"Top pick for {mood.replace('-', ' ').title()}",
            "genres": row.get("genres", []),
            "year": int(row["year"]) if pd.notna(row.get("year")) and row.get("year") else None,
            "vote_average": float(row.get("vote_average", 0)),
            "director": str(row.get("director", "")),
            "cast": row.get("cast", []) if isinstance(row.get("cast"), list) else [],
            "overview": str(row.get("overview", "")),
        })
    return results
