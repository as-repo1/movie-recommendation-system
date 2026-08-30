# RecLens — AI-Powered Movie Recommendation & Multi-Source Discovery Platform

RecLens is an enterprise-grade movie recommendation and discovery platform. It combines an ultra-fast **FastAPI ML-serving backend**, a modern **React + Vite + TypeScript web application**, a standalone **Streamlit AI Explorer (`streamlit_app.py`)**, a native **Jetpack Compose Android app**, and a production **Docker Compose** stack.

---

## ⚡ Performance & Efficiency Highlights

| Metric | Dense Matrix Baseline | RecLens Portable Index | Optimization |
| :--- | :--- | :--- | :--- |
| **Similarity Artifact Size** | `576.0 MB` (`float32` dense) | **`8.58 MB`** (`float16` Top-K sparse) | **98.5% reduction** 📉 |
| **Model Startup Load Time** | $\approx 450\text{ms} - 1200\text{ms}$ | **`46.48 ms`** | **$15\times - 25\times$ faster** ⚡ |
| **Recommendation Latency** | $\approx 25\text{ms} - 45\text{ms}$ | **`5.71 ms`** (P95: `6.05 ms`) | **$5\times - 8\times$ faster** 🏎️ |
| **Clean Catalog Storage** | Uncompressed CSV | **`12.48 MB` Snappy Parquet** | High-speed columnar query 📊 |
| **Cleaned Movies Retained** | Unfiltered raw (1.23M) | **`63,948` valid movies** | Enterprise noise & dupes purged 🛡️ |

---

## 🚀 Advanced Recommendation Engine

RecLens serves recommendations using a multi-factor hybrid intelligence stack:

1. **Enterprise Data Cleaning & Multi-Key Deduplication**:
   - Purges placeholder titles (`"untitled"`, `"test"`, `"null"`, `"n/a"`), corrupted entries, and unreleased/cancelled status.
   - Multi-key deduplication on TMDB ID, IMDb ID, and canonical `(normalized_title, release_year)`.
   - Text sanitization: HTML unescaping (`&amp;` $\to$ `&`), tag stripping, and Unicode NFKC normalization.
2. **Multi-Factor Sub-Field Weighted Vectorization**:
   - Sub-field weighting: Directors ($3\times$), Writers ($2\times$), Genres ($2\times$), Top Cast ($2\times$), Keywords ($2\times$), Overview, and Tagline.
   - N-gram feature mapping $(1, 2)$ with sublinear term frequency scaling.
3. **Ultra-Portable Top-K Sparse Similarity Index**:
   - Stores Top-100 float16 nearest neighbors per movie in a compact index structure (`TopKSimilarityIndex`), enabling $O(1)$ memory lookups and $<9\text{MB}$ total file size.
4. **Bayesian Weighted Quality Score ($WR$)**:
   - Precomputes and dynamically weights the Bayesian rating formula $WR = \frac{v}{v+m} \cdot R + \frac{m}{v+m} \cdot C$ so highly rated matches are prioritized over obscure noise.
5. **Maximal Marginal Relevance (MMR) Diversity Re-Ranking**:
   - Re-ranks candidates ($\lambda=0.75$) to balance semantic similarity and diversity, preventing repetitive franchise clustering.
6. **Rich Semantic Enrichment**:
   - **Mood/Vibe Taxonomy**: 6 curated categories (*Mind-Bending, Dark Thriller, Feel-Good, Adrenaline Action, Epic Journey, Emotional Drama*).
   - **Financial Analytics**: `profit = revenue - budget` and `roi` tracking.
   - **Runtime Classification**: `Short` ($< 45\text{m}$), `Feature` ($45 - 150\text{m}$), and `Epic` ($> 150\text{m}$).
7. **Collaborative Filtering & Personalization**:
   - Hybrid recommendations powered by **LightFM Matrix Factorization** and User Taste Profile Vectors.
8. **Explainable AI Match Chips**:
   - Calculates calibrated match percentages and human-readable explanation reasons (*e.g., "96% Match · Directed by Christopher Nolan & Sci-Fi Theme"*).

---

## 🌐 Multi-Tier Movie Database & Context Engine

- **Tier 1 — TMDB API v3**: Live search, trending, YouTube trailer video embeds, high-res posters, backdrops, and full cast/crew.
- **Tier 2 — OMDb API**: Multi-source score aggregator providing Rotten Tomatoes Tomatometer, Metacritic, IMDb rating & votes, Box Office, and Awards.
- **Tier 3 — Wikipedia Context**: Direct IMDb and Wikipedia search links for plot trivia and production history.
- **Tier 4 — Enriched Local Database**: Complete local dataset (`movies_clean.parquet` & `movies.pkl`) with directors, cast, budget, revenue, moods, and keywords, enabling 100% offline functionality.
- **Ingestion & Sync Pipelines**:
  - `scripts/ingest_tmdb_daily.py`: Full ingestion pipeline for the 1.23M+ TMDB dataset.
  - `scripts/build_model.py`: Fast model builder with Top-K sparse index serialization.
  - `scripts/sync_tmdb.py`: One-command sync tool to fetch and index new releases from TMDB.

---

## 📁 Project Structure

```
movie-recommendation-system/
├── backend/                # FastAPI ML Serving API (RecLens API)
│   ├── app/
│   │   ├── core/           # Configuration, Database engine, Schema migrations
│   │   ├── models/         # SQLAlchemy DB ORM schemas (Users, Watchlist, Watched)
│   │   ├── schemas/        # Pydantic request & response models
│   │   ├── services/       # Multi-source movie aggregator & Recommendation engine
│   │   └── api/            # API Route handlers (Auth, Movies, Recommendations, Watchlist, Watched)
│   ├── ml/                 # Saved model binaries
│   └── Dockerfile
├── frontend/               # React + Vite + TypeScript Single-Page App (RecLens Web)
│   ├── src/
│   │   ├── components/     # UI elements (Navbar with Search, MovieCard, Skeletons, RatingStars, AuthModal)
│   │   ├── pages/          # Home (Mood Explorer), MovieDetail (Trailers & Multi-scores), Watchlist, Watched
│   │   ├── store/          # Zustand global stores (movies, auth, theme)
│   │   └── services/api.ts # API client with dynamic auth/session injection
│   └── Dockerfile
├── streamlit_app.py        # Standalone Streamlit CineMatch interface
├── tests/                  # Automated pytest test suite (API, Recommender, Preprocessing - 25 tests)
├── src/
│   ├── preprocessing.py    # Enterprise data cleaning, sanitization & feature enrichment
│   ├── recommender.py      # Top-K sparse recommender, Bayesian priors, MMR & explainability
│   └── poster.py           # Poster resolver with fallbacks
├── scripts/
│   ├── ingest_tmdb_daily.py # 1.23M TMDB daily updates ingestion & portable model builder
│   ├── build_model.py      # Standalone TF-IDF & Top-K sparse model generator
│   ├── train_lightfm.py    # LightFM collaborative filtering training script
│   └── sync_tmdb.py        # Dynamic TMDB catalog synchronization tool
├── data/
│   ├── raw/                # TMDB 5000 & MovieLens datasets
│   └── processed/          # Pickled models (movies.pkl, similarity.pkl, movies_clean.parquet)
├── docker-compose.yml       # Production Compose file (Postgres + Backend + Frontend + Nginx)
└── .env.example             # Environment variable template
```

---

## 🔧 Quick Start & Local Setup

### 1. Build Datasets & ML Models
```bash
# Setup virtualenv and install dependencies
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt -r backend/requirements.txt

# Option A: Ingest full 1.23M TMDB dataset into portable Top-K format
python scripts/ingest_tmdb_daily.py data/TMDB_all_movies.csv --top-k 100 --min-votes 20 --top-n 15000

# Option B: Build standard model from TMDB 5000
python scripts/build_model.py --top-k 100

# Train Hybrid Collaborative Model
python scripts/train_lightfm.py --epochs 8
```

### 2. Run Test Suite
```bash
python -m pytest -v
```

### 3. Run FastAPI Backend
```bash
PYTHONPATH=backend:. uvicorn app.main:app --port 8001 --reload
```
Interactive Swagger Documentation: [http://localhost:8001/docs](http://localhost:8001/docs)

### 4. Run React Web Client
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser.

### 5. Run Streamlit Explorer
```bash
streamlit run streamlit_app.py --server.port 8501
```
Open [http://localhost:8501/](http://localhost:8501/) in your browser.

---

## 🐳 Docker Deployment

```bash
cp .env.example .env
docker compose up -d --build
```
- **Web App**: [http://localhost/](http://localhost/)
- **API Docs**: [http://localhost/docs](http://localhost/docs)
- **Health Check**: [http://localhost/health](http://localhost/health)

