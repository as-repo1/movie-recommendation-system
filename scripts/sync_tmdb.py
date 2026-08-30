#!/usr/bin/env python3
"""
scripts/sync_tmdb.py
====================
Dynamic catalog synchronization tool.
Fetches latest trending and now-playing movies from TMDB API and adds/updates them in the local dataset.
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing import _safe_convert, _safe_convert_cast, _safe_fetch_crew_roles, _compute_mood_tags, _collapse, _stem
from scripts.build_model import build

TMDB_BASE = "https://api.themoviedb.org/3"


def sync(api_key: str, pages: int = 2) -> None:
    if not api_key:
        print("[ERROR] TMDB_API_KEY is required to sync new movies.", file=sys.stderr)
        sys.exit(1)

    print(f"\n── Fetching trending and popular movies from TMDB (pages={pages}) ──")
    new_movies = []
    
    for endpoint in ["/movie/popular", "/movie/now_playing", "/movie/top_rated"]:
        for page in range(1, pages + 1):
            url = f"{TMDB_BASE}{endpoint}"
            try:
                r = requests.get(url, params={"api_key": api_key, "page": page}, timeout=10)
                r.raise_for_status()
                results = r.json().get("results", [])
                for m in results:
                    m_id = m.get("id")
                    if m_id and m.get("overview"):
                        new_movies.append(m)
            except Exception as e:
                print(f"[WARN] Failed fetching {endpoint} page {page}: {e}")

    print(f"[INFO] Fetched {len(new_movies)} movie candidates from TMDB API.")

    processed_dir = PROJECT_ROOT / "data" / "processed"
    movies_pkl = processed_dir / "movies.pkl"
    
    if not movies_pkl.exists():
        print("[INFO] No existing movies.pkl found. Running build_model first...")
        build(PROJECT_ROOT / "data" / "raw", processed_dir)

    with open(movies_pkl, "rb") as f:
        existing_df = pickle.load(f)

    existing_ids = set(existing_df["movie_id"].astype(int))
    added_count = 0

    new_rows = []
    for m in new_movies:
        mid = int(m["id"])
        if mid in existing_ids:
            continue

        # Fetch full movie details with credits
        detail_url = f"{TMDB_BASE}/movie/{mid}"
        try:
            r = requests.get(detail_url, params={"api_key": api_key, "append_to_response": "credits,keywords"}, timeout=8)
            r.raise_for_status()
            data = r.json()
        except Exception:
            continue

        genres = [g["name"] for g in data.get("genres", [])]
        keywords = [k["name"] for k in data.get("keywords", {}).get("keywords", [])]
        cast = [c["name"] for c in data.get("credits", {}).get("cast", [])[:6]]
        
        director, writer = "", ""
        for cr in data.get("credits", {}).get("crew", []):
            if cr.get("job") == "Director" and not director:
                director = cr.get("name", "")
            elif cr.get("job") in ("Writer", "Screenplay") and not writer:
                writer = cr.get("name", "")

        rel_date = data.get("release_date", "") or ""
        year = int(rel_date[:4]) if len(rel_date) >= 4 and rel_date[:4].isdigit() else None
        overview = data.get("overview", "")
        tagline = data.get("tagline", "")
        moods = _compute_mood_tags(genres, keywords, overview)

        # Build weighted tag
        director_tokens = _collapse([d for d in director.split(", ") if d.strip()])
        writer_tokens = _collapse([w for w in writer.split(", ") if w.strip()])
        genres_tokens = _collapse(genres)
        keywords_tokens = _collapse(keywords)
        cast_tokens = _collapse(cast[:4])

        tokens = (
            director_tokens * 3
            + writer_tokens * 2
            + genres_tokens * 2
            + keywords_tokens * 2
            + cast_tokens * 2
            + overview.split()
            + tagline.split()
        )
        tag_str = _stem(" ".join(tokens).lower())

        new_rows.append({
            "movie_id": mid,
            "title": data.get("title", ""),
            "overview": overview,
            "tagline": tagline,
            "genres": genres,
            "keywords": keywords,
            "cast": cast,
            "director": director,
            "writer": writer,
            "producers": [],
            "moods": moods,
            "year": year,
            "vote_average": data.get("vote_average", 0.0),
            "vote_count": data.get("vote_count", 0),
            "runtime": data.get("runtime"),
            "poster_path": data.get("poster_path", ""),
            "backdrop_path": data.get("backdrop_path", ""),
            "release_date": rel_date,
            "budget": data.get("budget", 0),
            "revenue": data.get("revenue", 0),
            "tags": tag_str,
        })
        existing_ids.add(mid)
        added_count += 1

    if added_count > 0:
        print(f"[INFO] Adding {added_count} new movies to dataset and updating similarity model...")
        updated_df = pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vec = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        vectors = vec.fit_transform(updated_df["tags"])
        similarity = cosine_similarity(vectors).astype("float32")

        with open(movies_pkl, "wb") as f:
            pickle.dump(updated_df, f)
        with open(processed_dir / "similarity.pkl", "wb") as f:
            pickle.dump(similarity, f)

        print(f"✅ Successfully synced and indexed {added_count} new movies! Total movies: {len(updated_df)}")
    else:
        print("✅ Dataset is already up to date with latest TMDB entries.")


def main():
    parser = argparse.ArgumentParser(description="Sync latest movies from TMDB API into RecLens database.")
    parser.add_argument("--api-key", type=str, default=os.environ.get("TMDB_API_KEY", ""), help="TMDB API key")
    parser.add_argument("--pages", type=int, default=2, help="Number of pages to fetch per category (default: 2)")
    args = parser.parse_args()
    sync(args.api_key, args.pages)


if __name__ == "__main__":
    main()
