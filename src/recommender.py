"""
src.recommender
===============
Model loading and recommendation logic.

The serialised model consists of two pickle files:
- ``movies.pkl``     — the preprocessed DataFrame (movie_id, title, tags)
- ``similarity.pkl`` — the NxN cosine-similarity matrix

Public API
----------
load_model(processed_dir)                        →  (movies_df, similarity)
recommend(movie_title, movies_df, similarity, n) →  list[dict]
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
    """Raised when the requested movie title is not in the dataset."""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def load_model(processed_dir: str | Path) -> tuple[pd.DataFrame, np.ndarray]:
    """Load the pickled model files from *processed_dir*.

    Parameters
    ----------
    processed_dir:
        Directory containing ``movies.pkl`` and ``similarity.pkl``.

    Returns
    -------
    (movies_df, similarity_matrix)

    Raises
    ------
    ModelNotFoundError
        If either pickle file is missing.
    """
    processed_dir = Path(processed_dir)
    movies_path    = processed_dir / "movies.pkl"
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
        movies_dict = pickle.load(f)
    with open(similarity_path, "rb") as f:
        similarity: np.ndarray = pickle.load(f)

    movies_df = pd.DataFrame(movies_dict) if isinstance(movies_dict, dict) else movies_dict
    return movies_df, similarity


def recommend(
    movie_title: str,
    movies_df: pd.DataFrame,
    similarity: np.ndarray,
    n: int = 5,
) -> list[dict[str, Any]]:
    """Return the top-*n* movies most similar to *movie_title*.

    Parameters
    ----------
    movie_title:
        Exact title string as it appears in the dataset.
    movies_df:
        DataFrame returned by :func:`load_model`.
    similarity:
        Cosine-similarity matrix returned by :func:`load_model`.
    n:
        Number of recommendations to return.

    Returns
    -------
    List of dicts, each with keys ``title`` and ``movie_id``,
    ordered from most to least similar.

    Raises
    ------
    MovieNotFoundError
        If *movie_title* is not present in *movies_df*.
    """
    matches = movies_df[movies_df["title"] == movie_title]
    if matches.empty:
        raise MovieNotFoundError(
            f"Movie '{movie_title}' was not found in the dataset. "
            "Try a different title."
        )

    movie_index = int(matches.index[0])
    distances = similarity[movie_index]

    # Sort descending; skip index 0 (the movie itself)
    ranked = sorted(enumerate(distances), key=lambda x: x[1], reverse=True)

    results: list[dict[str, Any]] = []
    for idx, score in ranked[1 : n + 1]:
        row = movies_df.iloc[idx]
        results.append(
            {
                "title":    str(row["title"]),
                "movie_id": int(row["movie_id"]),
                "score":    float(score),
            }
        )
    return results
