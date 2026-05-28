#!/usr/bin/env python3
"""
scripts/train_lightfm.py
=========================
Train a LightFM hybrid recommendation model on MovieLens data and serialise
the artefacts to ``data/processed/``.

Usage
-----
    python scripts/train_lightfm.py                     # uses ml-1m (fast)
    python scripts/train_lightfm.py --dataset ml-32m    # production (slow)
    python scripts/train_lightfm.py --epochs 30 --components 64

Output files (in data/processed/)
-----------------------------------
    lightfm_model.pkl      — trained LightFM model
    lightfm_dataset.pkl    — LightFM Dataset object (id mappings)
    lightfm_links.pkl      — movieId → tmdbId mapping from links.csv
"""

from __future__ import annotations

import argparse
import pickle
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_URLS = {
    "ml-1m":  "https://files.grouplens.org/datasets/movielens/ml-1m.zip",
    "ml-32m": "https://files.grouplens.org/datasets/movielens/ml-32m.zip",
}


# ─────────────────────────────────────────────────────────────────────────────
# Download helpers
# ─────────────────────────────────────────────────────────────────────────────


def _download(url: str, dest: Path) -> None:
    print(f"[INFO]  Downloading {url} …")
    dest.parent.mkdir(parents=True, exist_ok=True)

    def _progress(block, block_size, total):
        done = block * block_size
        pct = done * 100 // total if total > 0 else 0
        print(f"\r        {pct:3d}%  {done // 1_048_576} MB / {total // 1_048_576} MB", end="", flush=True)

    urlretrieve(url, dest, _progress)
    print()


def _ensure_dataset(dataset: str, raw_dir: Path) -> Path:
    """Download and unzip the requested MovieLens dataset if needed."""
    dataset_dir = raw_dir / dataset
    if dataset_dir.exists() and any(dataset_dir.iterdir()):
        print(f"[INFO]  Dataset already present: {dataset_dir}")
        return dataset_dir

    zip_path = raw_dir / f"{dataset}.zip"
    if not zip_path.exists():
        _download(DATASET_URLS[dataset], zip_path)

    print(f"[INFO]  Unzipping {zip_path.name} …")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(raw_dir)

    # Locate the extracted directory (name may vary)
    candidates = [p for p in raw_dir.iterdir() if p.is_dir() and dataset.split("-")[0] in p.name]
    if candidates:
        extracted = candidates[0]
        if extracted != dataset_dir:
            extracted.rename(dataset_dir)

    print(f"[INFO]  Dataset ready: {dataset_dir}")
    return dataset_dir


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────


def _load_ml1m(dataset_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load ratings and movies from MovieLens 1M (DAT format)."""
    ratings = pd.read_csv(
        dataset_dir / "ratings.dat",
        sep="::",
        names=["userId", "movieId", "rating", "timestamp"],
        engine="python",
        encoding="latin-1",
    )
    movies = pd.read_csv(
        dataset_dir / "movies.dat",
        sep="::",
        names=["movieId", "title", "genres"],
        engine="python",
        encoding="latin-1",
    )
    # 1M uses 1–5 scale → normalise to 0–1
    ratings["rating"] = ratings["rating"] / 5.0
    return ratings, movies


def _load_ml32m(dataset_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load ratings and movies from MovieLens 32M (CSV format)."""
    ratings = pd.read_csv(dataset_dir / "ratings.csv")
    movies  = pd.read_csv(dataset_dir / "movies.csv")
    # 32M uses 0.5–5.0 scale → normalise to 0–1
    ratings["rating"] = ratings["rating"] / 5.0
    return ratings, movies


def _load_links(dataset_dir: Path) -> pd.DataFrame | None:
    links_path = dataset_dir / "links.csv"
    if not links_path.exists():
        links_path = dataset_dir / "links.dat"
    if not links_path.exists():
        return None
    sep = "::" if links_path.suffix == ".dat" else ","
    try:
        return pd.read_csv(links_path, sep=sep, engine="python",
                           dtype={"movieId": int, "tmdbId": "str"})
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────────────


def train(
    dataset: str,
    raw_dir: Path,
    output_dir: Path,
    epochs: int,
    components: int,
    test_split: float,
) -> None:
    from lightfm import LightFM
    from lightfm.data import Dataset
    from lightfm.evaluation import auc_score, precision_at_k

    dataset_dir = _ensure_dataset(dataset, raw_dir)

    print("\n── Loading ratings ─────────────────────────────────────────────")
    if dataset == "ml-1m":
        ratings_df, movies_df = _load_ml1m(dataset_dir)
    else:
        ratings_df, movies_df = _load_ml32m(dataset_dir)

    links_df = _load_links(dataset_dir)

    print(f"[INFO]  {len(ratings_df):,} ratings | {ratings_df['userId'].nunique():,} users | {ratings_df['movieId'].nunique():,} movies")

    print("\n── Building LightFM dataset ────────────────────────────────────")
    lfm_dataset = Dataset()
    lfm_dataset.fit(
        users=ratings_df["userId"].unique(),
        items=ratings_df["movieId"].unique(),
    )

    # Build item features from genres
    genre_features = []
    for _, row in movies_df.iterrows():
        genres = str(row.get("genres", "")).split("|")
        genre_features.append((row["movieId"], genres))

    lfm_dataset.fit_partial(item_features=[g for _, genres in genre_features for g in genres])

    item_features = lfm_dataset.build_item_features(genre_features)

    # Train/test split
    from lightfm.cross_validation import random_train_test_split

    (interactions, weights) = lfm_dataset.build_interactions(
        [(r.userId, r.movieId, r.rating) for r in ratings_df.itertuples()]
    )
    train_inter, test_inter = random_train_test_split(interactions, test_percentage=test_split)

    print(f"[INFO]  Interaction matrix shape: {interactions.shape}")

    print(f"\n── Training LightFM ({epochs} epochs, {components} components, WARP loss) ──")
    model = LightFM(
        no_components=components,
        loss="warp",
        learning_rate=0.05,
        item_alpha=1e-6,
        user_alpha=1e-6,
        random_state=42,
    )

    for epoch in range(1, epochs + 1):
        model.fit_partial(
            train_inter,
            item_features=item_features,
            num_threads=4,
            epochs=1,
        )
        if epoch % 5 == 0 or epoch == epochs:
            prec = precision_at_k(model, test_inter, item_features=item_features, k=10, num_threads=4).mean()
            print(f"  Epoch {epoch:>3}/{epochs}  precision@10 = {prec:.4f}")

    print("\n── Saving artefacts ────────────────────────────────────────────")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "lightfm_model.pkl", "wb") as f:
        pickle.dump(model, f)

    with open(output_dir / "lightfm_dataset.pkl", "wb") as f:
        pickle.dump(lfm_dataset, f)

    # Save MovieLens movieId → TMDB movie_id mapping (from links.csv)
    if links_df is not None:
        links_map = dict(zip(links_df["movieId"].astype(int),
                             pd.to_numeric(links_df["tmdbId"], errors="coerce").fillna(0).astype(int)))
        with open(output_dir / "lightfm_links.pkl", "wb") as f:
            pickle.dump(links_map, f)
        print(f"[INFO]  Saved links map ({len(links_map):,} entries)")

    print(f"\n✅  LightFM model saved to {output_dir}")
    print("    lightfm_model.pkl")
    print("    lightfm_dataset.pkl")
    if links_df is not None:
        print("    lightfm_links.pkl")
    print("\n    Restart the API to load the new model.\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LightFM recommendation model on MovieLens data.")
    parser.add_argument("--dataset", choices=["ml-1m", "ml-32m"], default="ml-1m",
                        help="MovieLens dataset to use (default: ml-1m ~30s train; ml-32m ~production)")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs (default: 20)")
    parser.add_argument("--components", type=int, default=64, help="Latent dimensions (default: 64)")
    parser.add_argument("--test-split", type=float, default=0.05, help="Test split fraction (default: 0.05)")
    parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "processed")
    args = parser.parse_args()

    train(
        dataset=args.dataset,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        components=args.components,
        test_split=args.test_split,
    )


if __name__ == "__main__":
    main()
