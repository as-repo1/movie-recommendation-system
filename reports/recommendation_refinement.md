# RecLens — Technical Proposal: Recommendation Refinement & Dynamic Catalog Synchronization

This document proposes methodologies and architectural enhancements to solve two key challenges in **RecLens**:
1. **Dynamic Catalog Updating**: How to automatically ingest and index the latest movie releases.
2. **Recommendation Fine-Tuning**: How to enhance recommendation accuracy using semantic embeddings, implicit user feedback, and real-time inference.

---

## 1. Dynamic Catalog Synchronization (Ingesting Latest Releases)

Currently, the local movie database is a static representation stored in `movies.pkl` (processed from a Kaggle dataset). To dynamically index newly released movies, we recommend implementing a **Dual-Path Sync Strategy** consisting of an **Offline Cron Sync** for popular releases and an **On-the-Fly Dynamic Resolver** for user search requests.

```
                          Dynamic Catalog Updates
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
     Offline Sync (Cron)                               Runtime Resolver
 ingests trending/new releases                        resolves niche/new searches
     daily via TMDB API                                  directly from TMDB
           │                                                   │
           └─────────────────────────┬─────────────────────────┘
                                     ▼
                          Normalized Vector Store
                        (Appended & Re-indexed)
```

### 1.1 Daily Cron Sync Service
We can build a lightweight scheduler task that runs daily inside the backend stack. The sync loop:
1. Calls the TMDB API `/movie/now_playing` and `/discover/movie` endpoints to fetch movies released in the last 30 days.
2. Filters out entries without posters or with extremely low popularity scores.
3. Fetches each movie's corresponding credits (cast/director) and keywords.
4. Preprocesses and stems their text tags using our existing `src/preprocessing.py` logic.
5. Appends the new rows to the existing `movies_df`, runs the CountVectorizer to update features, and computes the new cosine similarity vectors.

### 1.2 On-Demand Runtime Indexing
If a user searches for a brand new movie that is not yet in our precomputed catalog:
1. The search fallback queries the TMDB API directly and returns the movie info to the user.
2. If the user adds this movie to their watchlist or rates it, the backend triggers an **asynchronous worker task** (e.g. via background tasks or Celery).
3. The worker downloads the movie metadata, transforms its text into a vector, and appends it to our matrix mapping in memory, ensuring that similarity queries for this new movie become instantly available.

---

## 2. Advanced Recommendation Refinements

To advance the quality of recommendations, we propose upgrading the algorithms from basic sparse frequency bag-of-words to dense semantic spaces and hybrid interactions.

### 2.1 Upgrade to Dense Semantic Embeddings (SentenceTransformers)
*Current approach*: CountVectorizer extracts raw term frequencies. If a movie overview uses the word "spacecraft" and another uses "spaceship", they share no root similarity unless mapped by the stemmer.
*Refinement*: Replace CountVectorizer with a pre-trained **SentenceTransformer** model (such as `all-MiniLM-L6-v2` or `multi-qa-MiniLM-L6-cos-v1`).
- These models map movie overviews and tag lines into a 384-dimensional dense vector space where distance represents **semantic meaning** rather than word match.
- This allows the system to recognize that "cosmic voyage" and "space expedition" are closely related, resolving the semantic gap.

```python
# Conceptual implementation
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")
# Encode all movie metadata tags into dense vectors
embeddings = model.encode(df["tags"].tolist(), show_progress_bar=True)
similarity = cosine_similarity(embeddings)
```

### 2.2 Implicit Feedback Signals
*Current approach*: The recommendation engine relies entirely on explicit ratings (1–10 stars) or watchlist items.
*Refinement*: Ingest implicit user feedback signals. These are highly abundant and require zero user effort:
- **Click-Through Rate (CTR)**: Tracks which movies a user clicks on from list carousels.
- **Detail View Duration**: Time spent reading a movie's overview.
- **Search Term Matching**: Query strings the user typed.
- **Dwell Time**: If a user immediately exits a movie detail page, it indicates negative feedback.

These signals can be added as fractional values to the user-item interaction matrix, reinforcing collaborative filtering mappings.

### 2.3 Two-Tower Retrieval Architecture
For larger catalogs (over 100,000 movies), matrix multiplication becomes a bottleneck. We can implement a **Two-Tower Neural Network** using PyTorch or TensorFlow:
- **User Tower**: Embeds user histories, session features, and demographics (device, time of day).
- **Item Tower**: Embeds movie metadata (genres, cast, keywords, overview).
- Both towers project their outputs into a shared latent space. Retrieval is executed via **Approximate Nearest Neighbors (ANN)** libraries like Faiss or HNSWLib, completing recommendation lookups across millions of movies in `< 10 milliseconds`.

---

## 3. Recommended Implementation Roadmap

If you decide to execute these refinements, we recommend starting with the following phases:

| Phase | Task | Effort | Impact |
|---|---|---|---|
| **Phase 1** | **Dynamic TMDB Syncer**: Build a daily sync script `scripts/sync_tmdb.py` to pull trending movies and append them to `movies.pkl`. | Low | High (Keeps list fresh) |
| **Phase 2** | **Dense Embeddings**: Swap `CountVectorizer` for `sentence-transformers` in `build_model.py`. | Medium | High (Better semantic search) |
| **Phase 3** | **Implicit Signals**: Log click states to the database and use them to boost similar recommendations. | Medium | Medium (Personalization) |
