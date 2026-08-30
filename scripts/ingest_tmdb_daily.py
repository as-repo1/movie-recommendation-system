#!/usr/bin/env python3
"""
scripts/ingest_tmdb_daily.py
============================
Clean, preprocess, and build a portable, high-performance recommendation model
from Alan Vourch's TMDB Movies Daily Updates Dataset (1.2M+ Movies).

Features:
- Multi-key deduplication and data sanitization
- Feature-weighted TF-IDF vectorization
- Portable Top-K Sparse Similarity Indexing (98%+ file size compression)
- Export to both Parquet and Pickled formats
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing import build_tags_dataframe
from src.recommender import TopKSimilarityIndex


def find_candidate_files() -> list[Path]:
    """Search common download locations for TMDB daily update files."""
    search_dirs = [
        PROJECT_ROOT / "data" / "raw",
        PROJECT_ROOT / "data",
        PROJECT_ROOT,
        Path.home() / "Downloads",
        Path("/tmp"),
    ]
    candidates = []
    patterns = [
        "TMDB_all_movies*.csv",
        "TMDB_movie*.csv",
        "TMDB_movies*.csv",
        "*tmdb*daily*.zip",
        "movies.csv",
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        for p in patterns:
            candidates.extend(d.glob(p))

    filtered = [
        c for c in candidates
        if "tmdb_5000" not in c.name and not c.name.startswith(".")
    ]
    return list(set(filtered))


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

    print(f"[INFO]  Normalizing TF-IDF matrix ({n:,} x {vectors.shape[1]:,}) ...")
    norm_vectors = normalize(vectors, norm="l2")

    print(f"[INFO]  Computing Top-{actual_k} nearest neighbors in batches of {batch_size} ...")
    start_time = time.time()

    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch = norm_vectors[start:end]
        
        # Dense dot product for this batch against all vectors
        sim_batch = (batch @ norm_vectors.T).toarray() if hasattr(batch, "toarray") else batch @ norm_vectors.T

        for i, row in enumerate(sim_batch):
            row_idx = start + i
            row[row_idx] = -1.0  # Exclude self-similarity

            if n > actual_k:
                top_part = np.argpartition(row, -actual_k)[-actual_k:]
                top_sorted = top_part[np.argsort(row[top_part])[::-1]]
            else:
                top_sorted = np.argsort(row)[::-1][:actual_k]

            all_indices[row_idx] = top_sorted
            all_scores[row_idx] = row[top_sorted].astype(np.float16)

        pct = end * 100 // n
        elapsed = time.time() - start_time
        print(f"\r        Progress: {pct:3d}% ({end:,}/{n:,} movies) in {elapsed:.1f}s", end="", flush=True)

    print(f"\n[INFO]  Top-{actual_k} sparse index constructed in {time.time() - start_time:.2f} seconds.")
    return TopKSimilarityIndex(all_indices, all_scores, n_movies=n, k=actual_k)


def ingest(
    source_path: Path | None = None,
    output_dir: Path = PROJECT_ROOT / "data" / "processed",
    min_votes: int = 15,
    top_n: int = 25000,
    max_features: int = 10000,
    top_k: int = 100,
    dense_matrix: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if source_path is None:
        candidates = find_candidate_files()
        if not candidates:
            print(
                "\n[ERROR] No TMDB Daily update file found in data/ or ~/Downloads/.\n"
                "Please specify path: `python scripts/ingest_tmdb_daily.py /path/to/TMDB_all_movies.csv`",
                file=sys.stderr,
            )
            sys.exit(1)
        source_path = candidates[0]

    source_path = Path(source_path)
    if not source_path.exists():
        print(f"[ERROR] Specified file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    print("================================================================")
    print("🎬 Clean & Ingest Alan Vourch TMDB Movies Dataset")
    print(f"   Source File : {source_path}")
    print(f"   Min Votes   : {min_votes}")
    print(f"   Top-N Model : {top_n:,} movies")
    print(f"   Top-K Index : {top_k} nearest neighbors (Portable Mode)")
    print("================================================================\n")

    # ── Step 1: Clean & Preprocess ─────────────────────────────────────────────
    print("── Step 1/4: Data cleaning, deduplication, and feature enrichment ──")
    df = build_tags_dataframe(
        raw_dir=source_path.parent,
        dataset="tmdb_daily",
        archive_path=source_path,
        vote_threshold=min_votes,
        top_n=top_n,
    )
    print(f"[INFO]  Cleaned DataFrame shape: {df.shape}")
    print(f"[INFO]  Columns: {list(df.columns)}")
    print(f"[INFO]  Year range: {df['year'].min()} - {df['year'].max()}")

    # ── Step 2: TF-IDF Vectorization ──────────────────────────────────────────
    print(f"\n── Step 2/4: Sub-field weighted TF-IDF vectorization (max_features={max_features}) ──")
    tfidf = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    vectors = tfidf.fit_transform(df["tags"])
    print(f"[INFO]  Vector matrix shape: {vectors.shape}")

    # ── Step 3: Compute Similarity Index ──────────────────────────────────────
    print(f"\n── Step 3/4: Constructing similarity index ──")
    if dense_matrix:
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_obj = cosine_similarity(vectors).astype("float32")
    else:
        similarity_obj = compute_topk_similarity(vectors, k=top_k, batch_size=1000)

    # ── Step 4: Serialise Portable Artifacts ───────────────────────────────────
    print(f"\n── Step 4/4: Serialising portable model artifacts ──")
    movies_pkl = output_dir / "movies.pkl"
    similarity_pkl = output_dir / "similarity.pkl"
    parquet_path = output_dir / "movies_clean.parquet"

    with open(movies_pkl, "wb") as f:
        pickle.dump(df, f, protocol=5)
    print(f"[INFO]  Saved {movies_pkl.name} ({movies_pkl.stat().st_size / 1_048_576:.1f} MB)")

    with open(similarity_pkl, "wb") as f:
        pickle.dump(similarity_obj, f, protocol=5)
    print(f"[INFO]  Saved {similarity_pkl.name} ({similarity_pkl.stat().st_size / 1_048_576:.1f} MB) [⚡ Ultra-Portable]")

    try:
        # Save compressed Parquet for high-speed columnar filtering
        df.to_parquet(parquet_path, index=False, compression="snappy")
        print(f"[INFO]  Saved {parquet_path.name} ({parquet_path.stat().st_size / 1_048_576:.1f} MB)")
    except Exception as e:
        print(f"[WARN]  Could not save Parquet: {e}")

    print("\n✅  Ingestion & portable model build completed successfully!")
    print(f"    Total movies indexed : {len(df):,}")
    print(f"    Artifact directory   : {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean and build portable model from Alan Vourch's TMDB Daily dataset."
    )
    parser.add_argument(
        "source_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to TMDB_all_movies.csv or zip archive (auto-detected if omitted)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Directory to save model pickles and parquet",
    )
    parser.add_argument(
        "--min-votes",
        type=int,
        default=15,
        help="Minimum vote count threshold to eliminate unrated noise (default: 15)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25000,
        help="Top N most notable films to index for active recommendation (default: 25000)",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=10000,
        help="Max TF-IDF features (default: 10000)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Top-K nearest neighbors per movie for portable sparse index (default: 100)",
    )
    parser.add_argument(
        "--dense",
        action="store_true",
        help="Store as dense N x N matrix instead of compact Top-K sparse index",
    )
    args = parser.parse_args()

    ingest(
        source_path=args.source_path,
        output_dir=args.output_dir,
        min_votes=args.min_votes,
        top_n=args.top_n,
        max_features=args.max_features,
        top_k=args.top_k,
        dense_matrix=args.dense,
    )


if __name__ == "__main__":
    main()
