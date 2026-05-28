# RecLens — AI-Powered Movie Recommendation System

RecLens is a premium, multi-service movie recommendation platform. It combines a high-performance **FastAPI ML-serving API**, a sleek **React + Vite + TypeScript web application**, a native **Jetpack Compose Android app**, and a production-ready **Docker Compose** orchestration stack.

Recommendations are served using a hybrid engine:
1. **Content-Based Filtering**: TF-IDF vectorization and cosine similarity over movie metadata (genres, keywords, overview, cast, and crew).
2. **Collaborative Filtering**: Personalized recommendations using user rating histories powered by **LightFM**.

---

## Key Features

- 🔍 **Instant Global Search**: Debounced search-as-you-type header component with TMDB, OMDb, and fallback local dataset resolution.
- 🎬 **Premium Detail Views**: Nord-themed details cards featuring Director, Writer, actor chips, and dynamic TMDB/OMDb posters.
- 📋 **Tracking Lists**: Local/database-backed watchlists and watched ratings (interactive 1-10 stars).
- 🔑 **Authentication & Migration**: Secure JWT-based registration and login, with seamless migration of anonymous user sessions to account storage.
- 🐳 **Docker-First Deployment**: Single-command orchestration combining Nginx proxying, PostgreSQL, static web serving, and backend health validation.
- 📱 **Native Mobile Experience**: Android client featuring bottom navigation tabs, Coil image loading, and SharedPreferences storage.

---

## Project Structure

```
movie-recommendation-system/
├── backend/                # FastAPI ML Serving API (RecLens API)
│   ├── app/
│   │   ├── core/           # Configuration, Database engine initialization, Schema migrations
│   │   ├── models/         # SQLAlchemy DB ORM schemas (Users, Watchlist, Watched list)
│   │   ├── schemas/        # Pydantic request & response models
│   │   ├── services/       # Movie lookup resolver (TMDB/OMDb/Local) & Recommender logic
│   │   └── api/            # API Route handlers (Auth, Movies, Recommendations, Watchlist, Watched)
│   ├── ml/                 # Saved model binaries
│   └── Dockerfile
├── frontend/               # React + Vite + TypeScript Single-Page App (RecLens Web)
│   ├── src/
│   │   ├── components/     # UI elements (Navbar with Search, MovieCard, Skeletons, RatingStars)
│   │   ├── pages/          # Home, MovieDetail, Watchlist, Watched pages
│   │   ├── store/          # Zustand global stores (movie tracking & user authentication)
│   │   └── services/api.ts # API client with dynamic anonymous/authenticated header injection
│   └── Dockerfile
├── android/                # Native Jetpack Compose App (CineMatch)
│   ├── app/src/main/       # Manifest, resources, and Kotlin sources
│   │   └── java/
│   │       └── ui/         # Composable screens (Home, Search, Detail, Watchlist, Watched)
│   └── build.gradle.kts
├── nginx/
│   └── nginx.conf          # Nginx reverse proxy configuration for docker
├── data/
│   ├── raw/                # TMDB 5000 movies datasets
│   └── processed/          # Saved model pickles (movies.pkl, similarity.pkl)
├── docker-compose.yml       # Production Compose file (Postgres + Backend + Frontend + Nginx)
├── docker-compose.dev.yml   # Hot-reloading development overrides
└── .env.example             # Environment variable template
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

---

## 🐳 Docker Deployment (Recommended)

Docker Compose is the easiest way to launch the entire stack (FastAPI, React served via `serve`, PostgreSQL, and Nginx proxy). 

### 1. Build local datasets
Before running containers, you must unzip the TMDB datasets and generate the pickle model binaries:
```bash
pip install -r requirements.txt
python scripts/build_model.py
```

### 2. Configure Environment
Copy the configuration template:
```bash
cp .env.example .env
```
*(Optional: Add your `TMDB_API_KEY` or `OMDB_API_KEY` to `.env` to enable online metadata and posters).*

### 3. Launch the Stack
```bash
docker compose up -d --build
```
This automatically sets up the PostgreSQL database and starts the services.

### Access Points
- **Web Application Portal**: [http://localhost/](http://localhost/) (Port 80)
- **FastAPI Interactive Documentation**: [http://localhost/docs](http://localhost/docs)
- **API Health Check**: [http://localhost/health](http://localhost/health)

---

## 🔧 Local Development Setup

To run services locally (outside of Docker), the backend defaults to a zero-configuration SQLite database (`data/db.sqlite`), removing the need for a running DB engine.

### 1. Backend Server
```bash
# Set up model datasets
pip install -r requirements.txt
python scripts/build_model.py

# Run FastAPI backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

### 2. Frontend Server
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser. API requests are automatically proxied to port 8000.

### 3. Native Android Client
Import the `android/` directory into Android Studio. The app's `CineMatchApi` points to the emulator loopback `http://10.0.2.2:8000` by default.

---

## ⚙️ How Recommendation Engine Works

1. **Content-Based Filtering**:
   - Compiles movie attributes (`genres`, `keywords`, `overview`, `cast`, `crew`) into a unified string.
   - Stemming is applied via Porter Stemmer.
   - Vectorized using `CountVectorizer` (5000 features).
   - Generates an $N \times N$ cosine similarity matrix (pickled to `similarity.pkl`).

2. **Collaborative Filtering**:
   - Utilizes `LightFM` hybrid matrix factorization.
   - Tailors recommendations using user ratings (1-10) combined with metadata features.

---

## 🛡️ Security & Sessions

- **Anonymous Sessions**: Assigns a persistent UUID to visitors (`reclens-session-id`). List updates are saved against this session ID.
- **User Authentication**: Secure signup and login using JWT tokens and bcrypt hashing.
- **Session Migration**: Upon user login, anonymous sessions are merged automatically into the registered user's account records.
- **Git Exclusions**: Database state files (`.sqlite`, `.db`) are explicitly excluded in `.gitignore` to prevent leaking session states.
