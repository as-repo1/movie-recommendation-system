#!/usr/bin/env python3
"""
scripts/build_model.py
======================
CLI script that runs the full preprocessing pipeline and serialises
``movies.pkl`` and ``similarity.pkl`` into ``data/processed/``.
Uses TF-IDF vectorizer with sublinear term frequency scaling and bi-grams
for high-precision semantic recommendation similarity.
"""

from __future__ import annotations

import argparse
import pickle
import sys
import zipfile
from pathlib import Path

# ── Make sure the project root is on the path so ``src`` is importable ──────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.preprocessing import build_tags_dataframe


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
            if not zip_path.exists():
                print(
                    f"[ERROR] Neither {csv_path} nor {zip_path} found.\n"
                    f"        Please place the dataset archives in: {raw_dir}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"[INFO]  Unzipping {zip_name} …")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(raw_dir)
            print(f"[INFO]  Extracted → {csv_path}")


def _save_pickle(obj: object, path: Path) -> None:
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    size_mb = path.stat().st_size / 1_048_576
    print(f"[INFO]  Saved {path.name} ({size_mb:.1f} MB)")


# ─────────────────────────────────────────────────────────────────────────────
# Main Build Routine
# ─────────────────────────────────────────────────────────────────────────────


def build(
    raw_dir: Path,
    output_dir: Path,
    max_features: int = 8000,
    vectorizer_type: str = "tfidf",
    dataset: str = "tmdb5000",
    archive_path: Path | None = None,
    vote_threshold: int = 30,
) -> None:
    print("\n── Step 1/4  Check datasets ────────────────────────────────────")
    if dataset == "tmdb5000":
        _maybe_unzip(raw_dir)

    print("\n── Step 2/4  Preprocess & build rich metadata tags ─────────────")
    df = build_tags_dataframe(
        raw_dir=raw_dir,
        dataset=dataset,
        archive_path=archive_path,
        vote_threshold=vote_threshold,
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

    print("\n── Step 4/4  Compute cosine similarity & save ─────────────────")
    similarity = cosine_similarity(vectors).astype("float32")
    print(f"[INFO]  Similarity matrix shape: {similarity.shape}")

    output_dir.mkdir(parents=True, exist_ok=True)
    _save_pickle(df, output_dir / "movies.pkl")
    _save_pickle(similarity, output_dir / "similarity.pkl")

    print("\n✅  Model built successfully!")
    print(f"    movies.pkl      → {output_dir / 'movies.pkl'}")
    print(f"    similarity.pkl  → {output_dir / 'similarity.pkl'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the recommendation model (movies.pkl + similarity.pkl)."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Directory containing the TMDB CSV files or ZIP archives.",
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
        default=8000,
        help="Maximum vocabulary size for vectorizer (default: 8000).",
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
        choices=["tmdb5000", "kaggle"],
        default="tmdb5000",
        help="Dataset to build from: tmdb5000 or kaggle (default: tmdb5000).",
    )
    parser.add_argument(
        "--archive-path",
        type=Path,
        default=PROJECT_ROOT / "more-datasets" / "archive.zip",
        help="Path to Kaggle archive zip file.",
    )
    parser.add_argument(
        "--vote-threshold",
        type=int,
        default=30,
        help="Minimum vote count for Kaggle movies (default: 30).",
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
    )


if __name__ == "__main__":
    main()
