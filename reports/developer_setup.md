# RecLens Developer Setup & Contribution Guide

This guide outlines steps for developers to configure, develop, train models, and test the **RecLens** full-stack recommendation engine.

---

## 1. Prerequisites & Host Configuration

Ensure your local development machine has the following packages installed:
- **Python 3.10+** (with `pip` and virtual environment support)
- **Node.js v20+** (with `npm`)
- **Java Development Kit (JDK) 17+** (for Android build tools)
- **Docker & Docker Compose** (for containerized stack runs)

---

## 2. Environment Variables Configuration

Copy [.env.example](file:///home/chaos/coding/old-github/movie-recommendation-system/.env.example) to `.env` in the project root:
```bash
cp .env.example .env
```

### Key Configuration Values
- `TMDB_API_KEY`: Used by the backend to fetch up-to-date posters and missing movie items.
- `OMDB_API_KEY`: Fallback key used for retrieving detailed directors, writers, and full cast lists.
- `JWT_SECRET_KEY`: Random security key used by the backend token signer.
- `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`: Production database credentials.

---

## 3. Pipeline Development & Model Training

The recommendation engines rely on pre-calculated models.

### 3.1 Building the Portable Recommendation Model
The Content-Based filtering uses feature-weighted TF-IDF matrices and Top-K sparse indexing:
```bash
# Option A: Ingest full 1.23M TMDB dataset into ultra-portable Top-K index
python scripts/ingest_tmdb_daily.py data/TMDB_all_movies.csv --top-k 100 --min-votes 20 --top-n 15000

# Option B: Run standard build from TMDB 5000
python scripts/build_model.py --top-k 100
```
This cleans and sanitizes raw datasets, extracts moods, profit, and runtime classes, vectorizes movie text tags, and outputs:
- `data/processed/movies.pkl` (Cleaned DataFrame containing rich metadata)
- `data/processed/similarity.pkl` (Ultra-portable 8.58MB Top-K sparse float16 index)
- `data/processed/movies_clean.parquet` (Snappy-compressed columnar database for high-speed catalog querying)

### 3.2 Training the Hybrid Collaborative Model
Collaborative recommendations are computed using LightFM trained on the MovieLens dataset:
```bash
# Run training script
python scripts/train_lightfm.py --epochs 8
```
This outputs user-item latent parameters and bias weights supporting real-time hybrid predictions.

---

## 4. Full-Stack Local Execution

### 4.1 FastAPI Backend (SQLite Mode)
When run locally outside Docker, the backend defaults to SQLite (`data/db.sqlite`):
```bash
PYTHONPATH=backend:. uvicorn app.main:app --reload --port 8001
```
API Documentation is served at `http://localhost:8001/docs`.

### 4.2 React Web Client (Vite Dev Server)
```bash
cd frontend
npm install
npm run dev
```
Served locally at `http://localhost:5173`.


---

## 5. Docker Orchestration

To verify multi-container PostgreSQL linkages:
```bash
# Start all containers in the background with auto-rebuilds
docker compose up -d --build

# Inspect status of health-checks
docker compose ps

# View backend application logs
docker compose logs -f backend
```

---

## 6. Android Mobile App Diagnostics

### 6.1 Device Connection
Verify a physical or emulated Android device is connected to your host via Android Debug Bridge (ADB):
```bash
adb devices
```

### 6.2 Network Port Reversing
If testing the Android application on a physical device connected via USB, reverse the backend port so requests to `localhost:8000` inside the mobile client route correctly to your host's backend API service:
```bash
adb reverse tcp:8000 tcp:8000
```

### 6.3 Gradle Release Compilation
Compile and package the release APK:
```bash
cd android
./gradlew clean assembleRelease
```
The output APK is generated at:
`android/app/build/outputs/apk/release/app-release-unsigned.apk`
