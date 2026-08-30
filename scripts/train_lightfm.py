#!/usr/bin/env python3
"""
scripts/train_lightfm.py
=========================
Train a LightFM hybrid recommendation model on MovieLens or local Kaggle data
and serialise the artefacts to ``data/processed/``.
"""

from __future__ import annotations

import argparse
import pickle
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

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

    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
    except Exception:
        # Fallback without SSL verification if host cert is expired
        r = requests.get(url, stream=True, timeout=30, verify=False)
        r.raise_for_status()

    total_size = int(r.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = downloaded * 100 // total_size
                    print(
                        f"\r        {pct:3d}%  {downloaded // 1_048_576} MB / {total_size // 1_048_576} MB",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"\r        {downloaded // 1_048_576} MB downloaded", end="", flush=True)
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
    movies = pd.read_csv(dataset_dir / "movies.csv")
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
        return pd.read_csv(
            links_path,
            sep=sep,
            engine="python",
            dtype={"movieId": int, "tmdbId": "str"},
        )
    except Exception:
        return None


def _load_kaggle(archive_path: Path, use_small: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load ratings and movies metadata directly from local Kaggle zip archive."""
    import ast

    print(f"[INFO]  Loading Kaggle dataset from {archive_path.name} ...")
    with zipfile.ZipFile(archive_path) as z:
        # Load links map
        with z.open("links.csv") as f:
            links = pd.read_csv(f)
        # Load ratings
        ratings_file = "ratings_small.csv" if use_small else "ratings.csv"
        with z.open(ratings_file) as f:
            ratings = pd.read_csv(f)
        # Load movies
        with z.open("movies_metadata.csv") as f:
            movies_meta = pd.read_csv(f, low_memory=False)

    print("[INFO]  Cleaning and mapping IDs...")
    # Clean links mappings
    links = links.dropna(subset=["tmdbId"])
    links["tmdbId"] = pd.to_numeric(links["tmdbId"], errors="coerce").fillna(0).astype(int)
    links = links[links["tmdbId"] > 0]
    links_map = dict(zip(links["movieId"].astype(int), links["tmdbId"]))

    # Clean movies_meta IDs
    movies_meta = movies_meta[movies_meta["id"].astype(str).str.isdigit() == True]
    movies_meta["id"] = movies_meta["id"].astype(int)

    # Parse genres
    def parse_genres(text):
        if not isinstance(text, str):
            return ""
        try:
            parsed = ast.literal_eval(text)
            return "|".join([g["name"] for g in parsed if isinstance(g, dict)])
        except Exception:
            return ""

    movies_meta["genres"] = movies_meta["genres"].apply(parse_genres)

    # Build movies_df using TMDB IDs directly as 'movieId'
    movies_df = (
        pd.DataFrame({
            "movieId": movies_meta["id"],
            "title": movies_meta["title"],
            "genres": movies_meta["genres"],
        })
        .drop_duplicates(subset=["movieId"])
        .reset_index(drop=True)
    )

    # Map ratings MovieLens movieId → TMDB ID
    ratings["tmdbId"] = ratings["movieId"].map(links_map)
    ratings = ratings.dropna(subset=["tmdbId"])
    ratings["tmdbId"] = ratings["tmdbId"].astype(int)

    # Align column name
    ratings = ratings.rename(columns={"movieId": "old_movieId", "tmdbId": "movieId"})
    ratings = ratings[["userId", "movieId", "rating", "timestamp"]]

    # Keep ratings only for movies in our catalog list
    valid_movie_ids = set(movies_df["movieId"])
    ratings = ratings[ratings["movieId"].isin(valid_movie_ids)].reset_index(drop=True)

    # Normalise rating scale to 0.0 - 1.0
    ratings["rating"] = ratings["rating"] / 5.0

    return ratings, movies_df


# ─────────────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────────────


def train(
    dataset: str,
    raw_dir: Path,
    output_dir: Path,
    epochs: int = 15,
    components: int = 48,
    test_split: float = 0.05,
    archive_path: Path | None = None,
) -> None:
    from lightfm import LightFM
    from lightfm.data import Dataset
    from lightfm.evaluation import precision_at_k
    from lightfm.cross_validation import random_train_test_split

    print("\n── Loading ratings ─────────────────────────────────────────────")
    links_df = None
    if dataset.startswith("kaggle"):
        if archive_path is None:
            archive_path = PROJECT_ROOT / "more-datasets" / "archive.zip"
        ratings_df, movies_df = _load_kaggle(archive_path, use_small=(dataset == "kaggle-small"))
    else:
        dataset_dir = _ensure_dataset(dataset, raw_dir)
        if dataset == "ml-1m":
            ratings_df, movies_df = _load_ml1m(dataset_dir)
        else:
            ratings_df, movies_df = _load_ml32m(dataset_dir)
        links_df = _load_links(dataset_dir)

    print(
        f"[INFO]  {len(ratings_df):,} ratings | {ratings_df['userId'].nunique():,} users |"
        f" {ratings_df['movieId'].nunique():,} movies"
    )

    print("\n── Building LightFM dataset ────────────────────────────────────")
    lfm_dataset = Dataset()
    lfm_dataset.fit(
        users=ratings_df["userId"].unique(),
        items=movies_df["movieId"].unique(),
    )

    # Build item features from genres
    genre_features = []
    for _, row in movies_df.iterrows():
        genres = str(row.get("genres", "")).split("|")
        genre_features.append((row["movieId"], [g.strip() for g in genres if g.strip()]))

    all_genre_tokens = [g for _, genres in genre_features for g in genres]
    if all_genre_tokens:
        lfm_dataset.fit_partial(item_features=all_genre_tokens)
        item_features = lfm_dataset.build_item_features(genre_features)
    else:
        item_features = None

    (interactions, weights) = lfm_dataset.build_interactions(
        [(int(r.userId), int(r.movieId), float(r.rating)) for r in ratings_df.itertuples()]
    )
    train_inter, test_inter = random_train_test_split(interactions, test_percentage=test_split, random_state=42)

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
            try:
                prec = precision_at_k(
                    model, test_inter, item_features=item_features, k=10, num_threads=4
                ).mean()
                print(f"  Epoch {epoch:>3}/{epochs}  precision@10 = {prec:.4f}")
            except Exception:
                print(f"  Epoch {epoch:>3}/{epochs} completed")

    print("\n── Saving artefacts ────────────────────────────────────────────")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "lightfm_model.pkl", "wb") as f:
        pickle.dump(model, f)

    with open(output_dir / "lightfm_dataset.pkl", "wb") as f:
        pickle.dump(lfm_dataset, f)

    # Save mapping (identity map for Kaggle datasets, otherwise MovieLens links)
    if dataset.startswith("kaggle"):
        links_map = {int(mid): int(mid) for mid in ratings_df["movieId"].unique()}
        with open(output_dir / "lightfm_links.pkl", "wb") as f:
            pickle.dump(links_map, f)
        print(f"[INFO]  Saved Kaggle links map ({len(links_map):,} entries)")
    elif links_df is not None:
        links_map = dict(
            zip(
                links_df["movieId"].astype(int),
                pd.to_numeric(links_df["tmdbId"], errors="coerce").fillna(0).astype(int),
            )
        )
        with open(output_dir / "lightfm_links.pkl", "wb") as f:
            pickle.dump(links_map, f)
        print(f"[INFO]  Saved links map ({len(links_map):,} entries)")

    print(f"\n✅  LightFM model saved to {output_dir}")
    print(f"    lightfm_model.pkl    → {output_dir / 'lightfm_model.pkl'}")
    print(f"    lightfm_dataset.pkl  → {output_dir / 'lightfm_dataset.pkl'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train LightFM recommendation model on MovieLens or local Kaggle data."
    )
    parser.add_argument(
        "--dataset",
        choices=["ml-1m", "ml-32m", "kaggle-small", "kaggle-full"],
        default="ml-1m",
        help="Dataset source: ml-1m, ml-32m, kaggle-small (100k), kaggle-full (26M)",
    )
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs (default: 10)")
    parser.add_argument("--components", type=int, default=48, help="Latent dimensions (default: 48)")
    parser.add_argument(
        "--test-split", type=float, default=0.05, help="Test split fraction (default: 0.05)"
    )
    parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "processed")
    parser.add_argument(
        "--archive-path", type=Path, default=PROJECT_ROOT / "more-datasets" / "archive.zip"
    )
    args = parser.parse_args()

    train(
        dataset=args.dataset,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        components=args.components,
        test_split=args.test_split,
        archive_path=args.archive_path,
    )


if __name__ == "__main__":
    main()
