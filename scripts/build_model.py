#!/usr/bin/env python3
"""
scripts/build_model.py
======================
CLI script that runs the full cleaning and preprocessing pipeline and serialises
``movies.pkl`` and ``similarity.pkl`` into ``data/processed/``.
Supports Top-K Portable Sparse Indexing for minimal memory consumption.
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
import zipfile
from pathlib import Path

# ── Make sure the project root is on the path so ``src`` is importable ──────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import normalize

from src.preprocessing import build_tags_dataframe
from src.recommender import TopKSimilarityIndex


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _maybe_unzip(raw_dir: Path) -> None:
    """Unzip dataset archives if the CSVs are not already present."""
    archives = {
        "tmdb_5000_movies.csv":  "tmdb_5000_movies.csv.zip",
        "tmdb_5000_credits.csv": "tmdb_5000_credits.csv.zip",
    }
    for csv_name, zip_name in archives.items():
        csv_path = raw_dir / csv_name
        zip_path = raw_dir / zip_name
        if not csv_path.exists():
            if zip_path.exists():
                print(f"[INFO]  Unzipping {zip_name} …")
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(raw_dir)
                print(f"[INFO]  Extracted → {csv_path}")


def _save_pickle(obj: object, path: Path) -> None:
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=5)
    size_mb = path.stat().st_size / 1_048_576
    print(f"[INFO]  Saved {path.name} ({size_mb:.1f} MB)")


def compute_topk_similarity(
    vectors,
    k: int = 100,
    batch_size: int = 1000,
) -> TopKSimilarityIndex:
    """Compute top-K cosine similarity neighbors in memory-efficient batches."""
    n = vectors.shape[0]
    actual_k = min(k, n - 1)
    all_indices = np.zeros((n, actual_k), dtype=np.int32)
    all_scores = np.zeros((n, actual_k), dtype=np.float16)

    norm_vectors = normalize(vectors, norm="l2")
    start_time = time.time()

    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch = norm_vectors[start:end]
        sim_batch = (batch @ norm_vectors.T).toarray() if hasattr(batch, "toarray") else batch @ norm_vectors.T

        for i, row in enumerate(sim_batch):
            row_idx = start + i
            row[row_idx] = -1.0

            if n > actual_k:
                top_part = np.argpartition(row, -actual_k)[-actual_k:]
                top_sorted = top_part[np.argsort(row[top_part])[::-1]]
            else:
                top_sorted = np.argsort(row)[::-1][:actual_k]

            all_indices[row_idx] = top_sorted
            all_scores[row_idx] = row[top_sorted].astype(np.float16)

    return TopKSimilarityIndex(all_indices, all_scores, n_movies=n, k=actual_k)


# ─────────────────────────────────────────────────────────────────────────────
# Main Build Routine
# ─────────────────────────────────────────────────────────────────────────────


def build(
    raw_dir: Path,
    output_dir: Path,
    max_features: int = 10000,
    vectorizer_type: str = "tfidf",
    dataset: str = "auto",
    archive_path: Path | None = None,
    vote_threshold: int = 15,
    top_n: int | None = None,
    top_k: int = 100,
    dense_matrix: bool = False,
) -> None:
    print("\n── Step 1/4  Check datasets ────────────────────────────────────")
    if dataset in ("auto", "tmdb5000") and (raw_dir / "tmdb_5000_movies.csv.zip").exists():
        _maybe_unzip(raw_dir)

    print("\n── Step 2/4  Preprocess, clean & build rich metadata tags ─────")
    df = build_tags_dataframe(
        raw_dir=raw_dir,
        dataset=dataset,
        archive_path=archive_path,
        vote_threshold=vote_threshold,
        top_n=top_n,
    )
    print(f"[INFO]  Dataset shape: {df.shape}")
    print(f"[INFO]  Columns: {df.columns.tolist()}")

    print(f"\n── Step 3/4  Vectorise with {vectorizer_type.upper()} (max_features={max_features}) ──")
    if vectorizer_type.lower() == "tfidf":
        vec = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
    else:
        vec = CountVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=(1, 2),
        )

    vectors = vec.fit_transform(df["tags"])
    print(f"[INFO]  Vector matrix shape: {vectors.shape}")

    print("\n── Step 4/4  Compute similarity index & serialise ─────────────")
    if dense_matrix:
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_obj = cosine_similarity(vectors).astype("float32")
    else:
        similarity_obj = compute_topk_similarity(vectors, k=top_k, batch_size=1000)

    output_dir.mkdir(parents=True, exist_ok=True)
    _save_pickle(df, output_dir / "movies.pkl")
    _save_pickle(similarity_obj, output_dir / "similarity.pkl")

    try:
        parquet_path = output_dir / "movies_clean.parquet"
        df.to_parquet(parquet_path, index=False, compression="snappy")
        print(f"[INFO]  Saved {parquet_path.name} ({parquet_path.stat().st_size / 1_048_576:.1f} MB)")
    except Exception as e:
        print(f"[WARN]  Could not save Parquet: {e}")

    print("\n✅  Model built successfully!")
    print(f"    movies.pkl           → {output_dir / 'movies.pkl'}")
    print(f"    similarity.pkl       → {output_dir / 'similarity.pkl'} [⚡ Portable]")
    print(f"    movies_clean.parquet → {output_dir / 'movies_clean.parquet'}")


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Build the recommendation model (movies.pkl + similarity.pkl)."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Directory containing the CSV files or dataset archives.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Directory to write movies.pkl and similarity.pkl.",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=10000,
        help="Maximum vocabulary size for vectorizer (default: 10000).",
    )
    parser.add_argument(
        "--vectorizer",
        type=str,
        choices=["tfidf", "count"],
        default="tfidf",
        help="Vectorizer algorithm to use (default: tfidf).",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["auto", "tmdb5000", "tmdb_daily", "kaggle"],
        default="auto",
        help="Dataset to build from (default: auto).",
    )
    parser.add_argument(
        "--archive-path",
        type=Path,
        default=None,
        help="Optional path to archive zip or CSV file.",
    )
    parser.add_argument(
        "--vote-threshold",
        type=int,
        default=15,
        help="Minimum vote count threshold (default: 15).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Limit model indexing to top N movies (e.g. 25000).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Top K nearest neighbors for portable sparse index (default: 100).",
    )
    parser.add_argument(
        "--dense",
        action="store_true",
        help="Store as dense N x N float32 matrix instead of compact Top-K index.",
    )
    args = parser.parse_args()
    build(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        max_features=args.max_features,
        vectorizer_type=args.vectorizer,
        dataset=args.dataset,
        archive_path=args.archive_path,
        vote_threshold=args.vote_threshold,
        top_n=args.top_n,
        top_k=args.top_k,
        dense_matrix=args.dense,
    )


if __name__ == "__main__":
    main()
