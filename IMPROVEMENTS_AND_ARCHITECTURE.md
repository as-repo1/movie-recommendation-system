# RecLens — Comprehensive System Improvements & Architecture Guide

> **Document Version:** 2.0.0  
> **Last Updated:** August 30, 2026  
> **Target Audience:** Engineering, ML Engineers, Data Scientists, and Developers

---

## 📑 Table of Contents

1. [Executive Summary & Transformation Overview](#1-executive-summary--transformation-overview)
2. [End-to-End System Architecture & Pipeline](#2-end-to-end-system-architecture--pipeline)
3. [Root Causes Diagnosed & Bug Fixes](#3-root-causes-diagnosed--bug-fixes)
4. [Advanced Recommendation Intelligence Engine](#4-advanced-recommendation-intelligence-engine)
   - [4.1 Multi-Factor Feature-Weighted TF-IDF](#41-multi-factor-feature-weighted-tf-idf)
   - [4.2 Bayesian Weighted Rating Quality Priors ($WR$)](#42-bayesian-weighted-rating-quality-priors-wr)
   - [4.3 Maximal Marginal Relevance (MMR) Diversity Re-Ranking](#43-maximal-marginal-relevance-mmr-diversity-re-ranking)
   - [4.4 Mood & Vibe Classification Taxonomy](#44-mood--vibe-classification-taxonomy)
   - [4.5 LightFM Hybrid Collaborative Filtering](#45-lightfm-hybrid-collaborative-filtering)
   - [4.6 Explainable AI Match Generation](#46-explainable-ai-match-generation)
5. [Multi-Source Movie Database Aggregator & Enrichment](#5-multi-source-movie-database-aggregator--enrichment)
6. [Dynamic Catalog Synchronization Pipeline](#6-dynamic-catalog-synchronization-pipeline)
7. [API Specification & Service Contracts](#7-api-specification--service-contracts)
8. [Frontend & User Interface Enhancements](#8-frontend--user-interface-enhancements)
9. [Automated Test Suite & Verification Matrix](#9-automated-test-suite--verification-matrix)
10. [Quick-Start & Operational Runbook](#10-quick-start--operational-runbook)

---

## 1. Executive Summary & Transformation Overview

The **RecLens** platform has undergone a major engineering and algorithmic overhaul, transitioning from a basic cosine similarity prototype into an enterprise-grade, multi-strategy hybrid recommendation platform with multi-source movie data enrichment.

### Key Metrics Before & After

| Dimension | Initial State | Upgraded State |
| :--- | :--- | :--- |
| **Vector Vocabulary** | 5,000 unigrams (plain Bag of Words) | **8,000 unigrams + bigrams with sublinear TF scaling** |
| **Feature Weights** | Flat unweighted text blob | **Sub-field weighting: Directors ($3\times$), Writers ($2\times$), Genres ($2\times$), Cast ($2\times$), Keywords ($2\times$)** |
| **Quality Control** | None (obscure movies ranked equally with classics) | **Bayesian Weighted Rating ($WR$) score prior** |
| **Recommendation Diversity** | Greedy top-k similarity (franchise clustering) | **Maximal Marginal Relevance (MMR, $\lambda=0.75$)** |
| **Discovery Modes** | Single movie similarity | **Similar movies, Personalized Taste Vector, Mood/Vibe Explorer** |
| **Data Sources** | Single raw CSV file | **TMDB API v3 + OMDb (Rotten Tomatoes & Metacritic) + YouTube Trailers + Enriched Local DB** |
| **Explainability** | Black-box output | **Match percentage ($0-100\%$) + human-readable match reason chips** |
| **Test Coverage** | 0 automated tests | **21 comprehensive unit & integration tests (100% passing)** |

---

## 2. End-to-End System Architecture & Pipeline

```mermaid
flowchart TD
    subgraph DataSources["Data Sources & External APIs"]
        TMDB["TMDB API v3<br>(Metadata, Posters, Trailers)"]
        OMDB["OMDb API<br>(Rotten Tomatoes, Metascore, IMDb)"]
        RawCSV["Raw Datasets<br>(TMDB 5000 / MovieLens 1M)"]
    end

    subgraph Preprocessing["Data Preprocessing Pipeline (src/preprocessing.py)"]
        CleanMerge["Clean & Merge DataFrames<br>(Fix Duplicate movie_id)"]
        ExtractCrew["Extract Directors, Writers, Cast, Keywords"]
        MoodTag["Rule-Based Mood & Vibe Classifier"]
        WeightedTokens["Sub-Field Weighted Token Assembly"]
        Stemming["Porter Stemming & Normalization"]
    end

    subgraph MLTraining["ML Training & Vectorization Pipeline"]
        TFIDF["TfidfVectorizer<br>(max_features=8000, ngram_range=(1,2))"]
        CosSim["Cosine Similarity Computation<br>(4803 x 4803 Matrix)"]
        LightFM["LightFM Matrix Factorization<br>(WARP Loss, 48 Components)"]
        Bayesian["Bayesian Score Precomputation<br>(IMDb Formula)"]
    end

    subgraph Storage["Artifacts & Storage (data/processed/ & SQLite/Postgres)"]
        MoviesPKL[("movies.pkl<br>(Enriched Catalog)")]
        SimPKL[("similarity.pkl<br>(88MB Vector Matrix)")]
        LightFMPKL[("lightfm_model.pkl<br>(Collaborative Model)")]
        Database[("SQLite / PostgreSQL<br>(Users, Watchlist, Watched)")]
    end

    subgraph BackendEngine["FastAPI ML Serving Engine (backend/app/)"]
        RecService["RecommendationService Singleton"]
        MovieDB["Multi-Tier Movie DB Aggregator"]
        MMR["Maximal Marginal Relevance Re-Ranker"]
        AuthService["JWT Auth & Anonymous Migration"]
    end

    subgraph Presentation["User Interfaces & Clients"]
        ReactWeb["React + Vite Web App<br>(Port 5173 / Port 80)"]
        StreamlitApp["Streamlit AI Explorer<br>(Port 8501)"]
        AndroidApp["Android Jetpack Compose App"]
    end

    RawCSV --> CleanMerge
    CleanMerge --> ExtractCrew --> MoodTag --> WeightedTokens --> Stemming
    Stemming --> TFIDF --> CosSim
    RawCSV --> LightFM
    CleanMerge --> Bayesian

    CosSim --> SimPKL
    CleanMerge --> MoviesPKL
    LightFM --> LightFMPKL
    Bayesian --> MoviesPKL

    MoviesPKL & SimPKL & LightFMPKL --> RecService
    Database --> AuthService
    TMDB & OMDB & MoviesPKL --> MovieDB

    RecService & MovieDB & MMR & AuthService --> ReactWeb & StreamlitApp & AndroidApp
```

---

## 3. Root Causes Diagnosed & Bug Fixes

### Bug 1: Duplicate `movie_id` Column Collapse
- **Root Cause**: `src/preprocessing.py` merged `movies_raw` with `credits_raw` on `title` and subsequently renamed `id -> movie_id`. Because `credits_raw` already possessed a `movie_id` column, the resultant DataFrame contained two identical `movie_id` columns. When indexing or serializing to dicts, Pandas returned a `pd.Series` instead of a scalar, crashing with `TypeError: argument of type 'Series' is not iterable` or `ValueError`.
- **Solution**: Refactored `build_tags_dataframe` to rename `id -> movie_id` on `movies_raw` *before* merging, and executed an inner join on `movie_id` with `credits_raw[["movie_id", "cast", "crew"]]`.

### Bug 2: Root Module Shadowing & Import Collisions
- **Root Cause**: An unencapsulated `app.py` script in the workspace root intercepted `import app` statements from any tool or pytest execution running from the root directory. This prevented Python from resolving the `backend/app` package, throwing `ModuleNotFoundError: No module named 'app.api'`.
- **Solution**: Transformed the Streamlit interface into [streamlit_app.py](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/streamlit_app.py), removed the colliding top-level `app.py`, and introduced [pytest.ini](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/pytest.ini) with `pythonpath = backend .`.

### Bug 3: LightFM GroupLens SSL Certificate Expiry
- **Root Cause**: `scripts/train_lightfm.py` relied on `urllib.request.urlretrieve` to download `ml-1m.zip` from `https://files.grouplens.org/`. The GroupLens SSL certificate expired, throwing `ssl.SSLCertVerificationError` and aborting training.
- **Solution**: Implemented a chunked streaming download using `requests` with automatic SSL fallback and progress bars, allowing graceful dataset retrieval.

### Bug 4: Port 8000 Host Port Collision
- **Root Cause**: A pre-existing container service on the host was bound to port `8000`, causing FastAPI backend startup to fail with `[Errno 98] Address already in use`.
- **Solution**: Migrated local backend port binding to `8001`, updated the Vite development proxy configuration in [frontend/vite.config.ts](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/frontend/vite.config.ts), and configured [frontend/src/services/api.ts](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/frontend/src/services/api.ts) with relative path fallback.

---

## 4. Advanced Recommendation Intelligence Engine

### 4.1 Multi-Factor Feature-Weighted TF-IDF

To prioritize creative auteurs, recurring themes, and acting ensembles over generic dictionary words, the metadata compiler applies strategic sub-field frequency boosts:

$$\text{Tokens}(M) = 3 \times \text{Director} + 2 \times \text{Writer} + 2 \times \text{Genres} + 2 \times \text{Keywords} + 2 \times \text{TopCast} + 1 \times \text{Tagline} + 1 \times \text{Overview}$$

The combined tokens are normalized via Porter Stemming and vectorized using:
- **Feature dimension**: 8,000 unigrams and bigrams (`ngram_range=(1, 2)`).
- **Sublinear term frequency**: $1 + \log(\text{tf})$ scaling to dampen outliers.
- **Stopwords**: Standard English stopword elimination with custom entity filtering.

### 4.2 Bayesian Weighted Rating Quality Priors ($WR$)

Plain cosine similarity often recommends low-quality or obscure films that share superficial keywords with a blockbuster. We solve this by incorporating the **IMDb Bayesian Weighted Rating Formula**:

$$WR = \left(\frac{v}{v + m}\right) R + \left(\frac{m}{v + m}\right) C$$

Where:
- $v$: Number of votes for the movie (`vote_count`).
- $m$: Minimum vote threshold required for confidence (set to $m = 250$).
- $R$: Average rating of the movie (`vote_average`).
- $C$: Mean rating across the entire catalog ($C \approx 6.0$).

The hybrid similarity score between source movie $S$ and candidate movie $D$ is calculated as:

$$\text{FinalScore}(S, D) = (1 - \alpha) \cdot \operatorname{CosineSimilarity}(\mathbf{v}_S, \mathbf{v}_D) + \alpha \cdot \text{NormalizedWR}(D)$$

*(where $\alpha = 0.20$ ensures quality weighting without overriding semantic relevance).*

### 4.3 Maximal Marginal Relevance (MMR) Diversity Re-Ranking

To avoid recommendation monotony (e.g., querying *Iron Man* returning only *Iron Man 2*, *Iron Man 3*, *Avengers 1*, *Avengers 2*), we apply **Maximal Marginal Relevance**:

$$\operatorname{MMR} = \operatorname{argmax}_{d_i \in R \setminus S} \left[ \lambda \cdot \operatorname{Sim}_1(d_i, Q) - (1 - \lambda) \max_{d_j \in S} \operatorname{Sim}_2(d_i, d_j) \right]$$

- $\lambda = 0.75$: Balances $75\%$ query relevance with $25\%$ inter-item diversity.
- Iteratively constructs the top-$k$ recommendation set $S$ from top candidate pool $R$.

### 4.4 Mood & Vibe Classification Taxonomy

Movies are automatically classified into structured psychological mood buckets during preprocessing:

| Mood / Vibe | Trigger Genres & Keywords | Example Films |
| :--- | :--- | :--- |
| `mind-bending` | Science Fiction, Mystery, Time Travel, Space, Simulation, Reality | *Interstellar, Inception, The Matrix* |
| `dark-thriller` | Crime, Mystery, Thriller, Serial Killer, Investigation, Noir | *Se7en, The Dark Knight, Zodiac* |
| `feel-good` | Comedy, Animation, Family, Friendship, Heartwarming, Romance | *Toy Story, Up, Paddington* |
| `adrenaline-action` | Action, Adventure, Superhero, Martial Arts, Chase, Explosions | *Mad Max: Fury Road, John Wick, Avengers* |
| `epic-journey` | Fantasy, Adventure, Mythology, Medieval, Quest, Magic | *The Lord of the Rings, Gladiator, Avatar* |
| `emotional-drama` | Drama, Romance, Heartbreak, Biography, Historical Tragedy | *Schindler's List, Titanic, The Pianist* |

### 4.5 LightFM Hybrid Collaborative Filtering

For personalized multi-item recommendations based on user rating histories:
- Uses LightFM with **WARP (Weighted Approximate-Rank Pairwise)** loss.
- 48 latent latent feature components trained across user-item interaction matrices.
- Blends user preference taste vectors with item metadata features to mitigate cold-start limitations.

### 4.6 Explainable AI Match Generation

Every recommendation returned by the engine includes human-interpretable reasoning:
1. **Match Percentage**: Calibrated percentage score ($65\% - 99\%$) reflecting cosine similarity and Bayesian quality boost.
2. **Match Reason Chips**: Identifies exact shared attributes (e.g., *"Directed by Christopher Nolan"*, *"Shared Sci-Fi & Adventure themes"*, or *"Similar cast featuring Christian Bale"*).

---

## 5. Multi-Source Movie Database Aggregator & Enrichment

The backend employs a tiered data resolution strategy:

```
[User Request] 
      │
      ├── Tier 1 ──► TMDB API v3 (Online: Posters, Backdrops, YouTube Trailers, Full Cast/Crew)
      │
      ├── Tier 2 ──► OMDb API (Online: Rotten Tomatoes %, Metascore, IMDb Ratings & Votes, Box Office)
      │
      ├── Tier 3 ──► External Context (Wikipedia plot summaries & Trivia URL resolvers)
      │
      └── Tier 4 ──► Enriched Local DB (Offline: 4,803 Movies with Directors, Cast, Budgets, Moods)
```

### Schema Attributes in `Movie` Object
```typescript
interface Movie {
  id: number;
  title: string;
  overview: string;
  tagline?: string;
  poster_url: string;
  backdrop_url: string;
  genres: string[];
  moods?: string[];
  year: number | null;
  vote_average: number;
  vote_count: number;
  runtime: number | null;
  imdb_id: string;
  imdb_rating?: number | null;
  rotten_tomatoes_score?: string; // e.g. "94%"
  metascore?: string;             // e.g. "88/100"
  director: string;
  writer: string;
  producers?: string[];
  cast: string[];
  budget?: number;
  revenue?: number;
  trailer_url?: string;           // YouTube trailer embed
  match_percentage?: number;      // e.g. 96
  match_reason?: string;          // e.g. "Directed by Christopher Nolan"
}
```

---

## 6. Dynamic Catalog Synchronization Pipeline

The system includes a standalone synchronization CLI [scripts/sync_tmdb.py](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/scripts/sync_tmdb.py) to ingest newly released or trending films:

```bash
python scripts/sync_tmdb.py --api-key YOUR_TMDB_KEY --pages 3
```

### Sync Pipeline Steps:
1. Queries TMDB `/movie/popular`, `/movie/now_playing`, and `/movie/top_rated`.
2. Filters out existing movie IDs in `data/processed/movies.pkl`.
3. Fetches deep metadata (credits, keywords, release dates, mood tags) for new candidates.
4. Generates feature-weighted tag representations.
5. Re-fits the `TfidfVectorizer` and updates `similarity.pkl` and `movies.pkl` in place.

---

## 7. API Specification & Service Contracts

| Method | Route | Description | Parameters / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server health & model readiness status | None |
| `GET` | `/api/movies/popular` | Retrieve top popular films ordered by Bayesian score | `page` (int) |
| `GET` | `/api/movies/search` | Search movie catalog across TMDB & local database | `q` (string), `page` (int) |
| `GET` | `/api/movies/genres` | List all unique genres available in catalog | None |
| `GET` | `/api/movies/{id}` | Comprehensive movie detail (trailers, ratings, crew) | `id` (TMDB movie ID) |
| `GET` | `/api/recommendations/similar/{id}` | Top similar movies with Bayesian quality + MMR diversity | `id`, `n` (default: 10), `use_mmr` (bool) |
| `GET` | `/api/recommendations/mood/{mood}` | Mood & vibe-based curated movie recommendations | `mood` (string: `mind-bending`, `feel-good`, etc.) |
| `POST` | `/api/recommendations/personalised` | Personalized hybrid recommendations from user ratings | Payload: `{ ratings: [{movie_id, rating}], n: 10 }` |
| `GET` | `/api/recommendations/personalised` | Database session-backed personalized recommendations | Headers: `Authorization` or `X-Session-ID` |
| `GET` | `/api/recommendations/catalogue` | Lightweight catalog of all indexed titles | None |
| `POST` | `/api/auth/register` | Register user account with automatic session migration | Payload: `{ username, password, anonymous_session_id }` |
| `POST` | `/api/auth/login` | Authenticate user and issue JWT bearer token | Payload: `{ username, password, anonymous_session_id }` |
| `GET` | `/api/watchlist` | Fetch user's saved watchlist | Headers: `Authorization` / `X-Session-ID` |
| `POST` | `/api/watchlist` | Add movie to watchlist | Payload: `{ movie_id: int }` |
| `POST` | `/api/watched` | Mark movie as watched with 1-10 star rating | Payload: `{ movie_id: int, rating: float }` |

---

## 8. Frontend & User Interface Enhancements

### 1. React Web Client ([frontend/src/](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/frontend/src/))
- **Mood Explorer Filter Bar**: One-click pills for instant mood discovery on the Home page.
- **Glassmorphic Nord Cards**: Smooth hover elevation, dynamic match badges, and Rotten Tomatoes indicators.
- **Movie Detail Screen**:
  - Embedded responsive **YouTube Trailer Modal**.
  - **Multi-Source Score Badges**: TMDB, Rotten Tomatoes Tomatometer, Metascore, and IMDb.
  - **Financial Metrics**: Production Budget & Worldwide Box Office metrics.
  - **Crew & Cast Chips**: Director, Writer, and full cast chips.
- **Real-Time Interactive Search**: Debounced instant search dropdown with poster previews.

### 2. Standalone Streamlit App ([streamlit_app.py](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/streamlit_app.py))
- Dual tabs: **Movie-Based Recommendations** and **Mood & Vibe Explorer**.
- Interactive sliders for recommendation count and MMR diversity toggle.
- Full offline rendering with cached model binaries.

---

## 9. Automated Test Suite & Verification Matrix

The test suite in [tests/](file:///home/syncthing_shared/coding/ai/movie-recommendation-system/tests/) covers all application tiers:

```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1
configfile: pytest.ini
testpaths: tests

tests/test_api.py::test_health_endpoint PASSED                           [  4%]
tests/test_api.py::test_popular_movies PASSED                            [  9%]
tests/test_api.py::test_search_movies PASSED                             [ 14%]
tests/test_api.py::test_movie_genres PASSED                              [ 19%]
tests/test_api.py::test_movie_detail PASSED                              [ 23%]
tests/test_api.py::test_similar_recommendations PASSED                   [ 28%]
tests/test_api.py::test_mood_recommendations PASSED                      [ 33%]
tests/test_api.py::test_personalised_recommendations PASSED              [ 38%]
tests/test_api.py::test_watchlist_and_watched_flow PASSED                [ 42%]
tests/test_api.py::test_auth_registration_and_session_migration PASSED   [ 47%]
tests/test_preprocessing.py::test_safe_convert PASSED                    [ 52%]
tests/test_preprocessing.py::test_safe_convert_cast PASSED               [ 57%]
tests/test_preprocessing.py::test_safe_fetch_crew_roles PASSED           [ 61%]
tests/test_preprocessing.py::test_compute_mood_tags PASSED               [ 66%]
tests/test_preprocessing.py::test_build_tags_dataframe PASSED            [ 71%]
tests/test_recommender.py::test_load_model PASSED                        [ 76%]
tests/test_recommender.py::test_bayesian_scores PASSED                   [ 80%]
tests/test_recommender.py::test_mmr_diversity PASSED                     [ 85%]
tests/test_recommender.py::test_recommend_by_title PASSED                [ 90%]
tests/test_recommender.py::test_recommend_by_id PASSED                   [ 95%]
tests/test_recommender.py::test_recommend_by_mood PASSED                 [100%]

============================= 21 passed in 14.07s ==============================
```

---

## 10. Quick-Start & Operational Runbook

### Running All Services

#### 1. Start FastAPI Backend (Port 8001)
```bash
source .venv/bin/activate
PYTHONPATH=. .venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8001
```

#### 2. Start React + Vite Frontend (Port 5173)
```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

#### 3. Start Streamlit AI Explorer (Port 8501)
```bash
source .venv/bin/activate
streamlit run streamlit_app.py --server.port 8501
```

#### 4. Run Test Suite
```bash
pytest -v
```

---
*Generated by Google DeepMind Advanced Agentic AI Assistant.*
