# RecLens — AI-Powered Movie Recommendation & Multi-Source Platform

RecLens is a multi-service movie recommendation and discovery platform. It combines an advanced **FastAPI ML-serving API**, a sleek **React + Vite + TypeScript web application**, a standalone **Streamlit AI Explorer (`streamlit_app.py`)**, a native **Jetpack Compose Android app**, and a production **Docker Compose** stack.

---

## 🚀 Advanced Recommendation Engine

RecLens serves recommendations using a multi-factor hybrid intelligence stack:

1. **Multi-Factor Semantic TF-IDF Vectorization**:
   - Sub-field weighting: Directors ($3\times$), Writers ($2\times$), Genres ($2\times$), Top Cast ($2\times$), Keywords ($2\times$), Overview, and Tagline.
   - N-gram feature mapping $(1, 2)$ with sublinear term frequency scaling.
2. **Bayesian Weighted Quality Score ($WR$)**:
   - Integrates the Bayesian rating formula $WR = \frac{v}{v+m} \cdot R + \frac{m}{v+m} \cdot C$ so highly rated matches are prioritized over obscure noise.
3. **Maximal Marginal Relevance (MMR) Diversity Re-Ranking**:
   - Re-ranks candidates ($\lambda=0.75$) to balance semantic similarity and genre diversity, preventing repetitive franchise clusters.
4. **Mood & Vibe Explorer**:
   - Curated vibes: *Mind-Bending & Sci-Fi, Dark & Gritty Thrillers, Heartwarming Comfort, Adrenaline & Action, Epic Fantasy, Emotional Drama*.
5. **Collaborative Filtering**:
   - Personalized hybrid recommendations powered by **LightFM Matrix Factorization** and User Taste Profile Vectors.
6. **Explainable AI Match Chips**:
   - Calculates match percentages and human-readable explanation reasons (*e.g., "96% Match · Directed by Christopher Nolan & Sci-Fi Theme"*).

---

## 🌐 Multi-Tier Movie Database & Context Engine

- **Tier 1 — TMDB API v3**: Live search, trending, YouTube trailer video embeds, high-res posters, backdrops, and full cast/crew.
- **Tier 2 — OMDb API**: Multi-source score aggregator providing Rotten Tomatoes Tomatometer, Metacritic, IMDb rating & votes, Box Office, and Awards.
- **Tier 3 — Wikipedia Context**: Direct IMDb and Wikipedia search links for plot trivia and production history.
- **Tier 4 — Enriched Local Database**: Complete local dataset with directors, cast, budget, revenue, moods, and keywords, enabling 100% offline functionality.
- **Dynamic Catalog Sync (`scripts/sync_tmdb.py`)**: One-command sync tool to fetch, ingest, and index new releases from TMDB.

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
├── tests/                  # Automated pytest test suite (API, Recommender, Preprocessing)
├── scripts/
│   ├── build_model.py      # TF-IDF model generator
│   ├── train_lightfm.py    # LightFM collaborative filtering training script
│   └── sync_tmdb.py        # Dynamic TMDB catalog synchronization tool
├── data/
│   ├── raw/                # TMDB & MovieLens datasets
│   └── processed/          # Pickled models (movies.pkl, similarity.pkl, lightfm_model.pkl)
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

# Build Content-Based TF-IDF Model
python scripts/build_model.py

# Train Hybrid Collaborative Model
python scripts/train_lightfm.py --epochs 8
```

### 2. Run Test Suite
```bash
pytest -v
```

### 3. Run FastAPI Backend
```bash
cd backend
uvicorn app.main:app --port 8000 --reload
```
Interactive Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Run React Web Client
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser.

### 5. Run Streamlit Explorer
```bash
streamlit run streamlit_app.py
```

---

## 🐳 Docker Deployment

```bash
cp .env.example .env
docker compose up -d --build
```
- **Web App**: [http://localhost/](http://localhost/)
- **API Docs**: [http://localhost/docs](http://localhost/docs)
- **Health Check**: [http://localhost/health](http://localhost/health)
