#!/usr/bin/env python3
"""
scripts/build_model.py
======================
CLI script that runs the full preprocessing pipeline and serialises
``movies.pkl`` and ``similarity.pkl`` into ``data/processed/``.

Usage
-----
From the project root::

    python scripts/build_model.py

Options
-------
--raw-dir       Path to directory containing unzipped TMDB CSV files.
                Default: data/raw
--output-dir    Path to write the generated pickle files.
                Default: data/processed
--max-features  Maximum vocabulary size for CountVectorizer.
                Default: 5000

Notes
-----
* The script will **unzip** the dataset archives automatically if the CSV
  files are not yet present in *raw-dir*.
* On first run, NLTK's ``punkt`` tokeniser data is downloaded automatically.
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
import zipfile
from pathlib import Path

# ── Make sure the project root is on the path so ``src`` is importable ──────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.preprocessing import build_tags_dataframe


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _maybe_unzip(raw_dir: Path) -> None:
    """Unzip dataset archives if the CSVs are not already present."""
    archives = {
        "tmdb_5000_movies.csv":   "tmdb_5000_movies.csv.zip",
        "tmdb_5000_credits.csv":  "tmdb_5000_credits.csv.zip",
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
# Main
# ─────────────────────────────────────────────────────────────────────────────


def build(raw_dir: Path, output_dir: Path, max_features: int) -> None:
    print("\n── Step 1/4  Unzip datasets ────────────────────────────────────")
    _maybe_unzip(raw_dir)

    print("\n── Step 2/4  Preprocess & build tags ──────────────────────────")
    df = build_tags_dataframe(raw_dir)
    print(f"[INFO]  Dataset shape: {df.shape}")

    print("\n── Step 3/4  Vectorise with CountVectorizer ───────────────────")
    cv = CountVectorizer(max_features=max_features, stop_words="english")
    vectors = cv.fit_transform(df["tags"]).toarray()
    print(f"[INFO]  Vector shape: {vectors.shape}")

    print("\n── Step 4/4  Compute cosine similarity & save ─────────────────")
    similarity = cosine_similarity(vectors)
    print(f"[INFO]  Similarity matrix shape: {similarity.shape}")

    output_dir.mkdir(parents=True, exist_ok=True)
    _save_pickle(df, output_dir / "movies.pkl")
    _save_pickle(similarity, output_dir / "similarity.pkl")

    print("\n✅  Model built successfully!")
    print(f"    movies.pkl      → {output_dir / 'movies.pkl'}")
    print(f"    similarity.pkl  → {output_dir / 'similarity.pkl'}")
    print("\n    Run the app with:  streamlit run app.py\n")


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
        default=5000,
        help="Maximum vocabulary size for CountVectorizer (default: 5000).",
    )
    args = parser.parse_args()
    build(args.raw_dir, args.output_dir, args.max_features)


if __name__ == "__main__":
    main()
