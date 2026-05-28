# RecLens REST API Specification

This document details the REST API specifications for the **RecLens API** served by the FastAPI backend on port `8000`.

---

## 1. Global Request Configurations

### 1.1 Headers
All requests tracking user list configurations (Watchlist / Ratings) must supply a session identifier:
- **`X-Session-ID`** (String, Required for stateful endpoints): Unique session UUID used to track client data before logging in.
- **`Authorization`** (String, Optional): Bearer token received after successful authentication (`Bearer <JWT_TOKEN>`).

---

## 2. API Endpoints

### 2.1 Movie Catalog & Search

#### `GET /api/movies/popular`
Fetches popular movies sorted by rating count.
- **Query Parameters**:
  - `page` (Integer, Optional, default `1`): Pagination page.
- **Response**: Array of Movie objects.
  ```json
  [
    {
      "id": 19995,
      "title": "Avatar",
      "overview": "In the 22nd century, a paraplegic Marine is dispatched...",
      "poster_url": "https://image.tmdb.org/t/p/w500/kyeqWiccfx4ZRHOFty5yZns7X22.jpg",
      "backdrop_url": "https://image.tmdb.org/t/p/original/amY0NIxFcy64Gwx2cwBRNyGZj7C.jpg",
      "genres": ["Action", "Adventure", "Fantasy", "Science Fiction"],
      "year": 2009,
      "vote_average": 7.2,
      "vote_count": 11800,
      "runtime": 162,
      "imdb_id": "tt0499549"
    }
  ]
  ```

#### `GET /api/movies/search`
Searches for movies matching the query term. Uses a 3-tier fallback strategy:
1. Local Dataset TMDB match
2. TMDB Web API search (if key exists)
3. OMDb Web API search (if TMDB fails)
- **Query Parameters**:
  - `q` (String, Required): Search query term.
  - `page` (Integer, Optional, default `1`): Pagination page.
- **Response**:
  ```json
  {
    "movies": [ ... ],
    "total": 1,
    "page": 1,
    "query": "Avatar"
  }
  ```

#### `GET /api/movies/{id}`
Fetches detail parameters of a specific movie, including extended directors and cast listings.
- **Path Parameters**:
  - `id` (Integer, Required): TMDB movie ID.
- **Response**: Detailed Movie object.

---

### 2.2 Recommendation Engine

#### `GET /api/recommendations/similar/{id}`
Fetches structurally similar recommendations using the Content-Based TF-IDF cosine similarity matrix.
- **Path Parameters**:
  - `id` (Integer, Required): Target TMDB movie ID.
- **Query Parameters**:
  - `n` (Integer, Optional, default `10`): Number of recommendations to return.
- **Response**:
  ```json
  {
    "source_movie": { "id": 19995, "title": "Avatar", ... },
    "recommendations": [ ... ],
    "engine": "content_based"
  }
  ```

#### `POST /api/recommendations/personalised`
Generates personalized recommendations. Generates collaborative predictions via the LightFM model if ratings are present; falls back to Content-Based seeds or Trending popular movies if the user profile is cold.
- **Request Body**:
  ```json
  {
    "ratings": [
      { "movie_id": 19995, "rating": 9.0 }
    ],
    "n": 10
  }
  ```
- **Response**:
  ```json
  {
    "recommendations": [ ... ],
    "engine": "collaborative"
  }
  ```

---

### 2.3 User Authentication & Registration

#### `POST /api/auth/register`
Registers a new user account and migrates historical session data.
- **Request Body**:
  ```json
  {
    "username": "johndoe",
    "password": "securepassword123",
    "anonymous_session_id": "3b687f54-d890-410a-8bf8-2a1c22ff3a5d"
  }
  ```
- **Response**:
  ```json
  {
    "message": "User registered successfully",
    "user_id": 1
  }
  ```

#### `POST /api/auth/token`
Logs in a user, returning a JSON Web Token (JWT) along with session migration triggers.
- **Request Body** (Form-Data URL Encoded):
  - `username` (String): User login name.
  - `password` (String): User password.
  - `anonymous_session_id` (String, Optional): Source anonymous session ID.
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

---

### 2.4 User Lists (Watchlist & Watched Ratings)

#### `GET /api/watchlist`
Retrieves the user's active watchlist. Requires `X-Session-ID` and/or `Authorization` headers.
- **Response**: List of watchlist item entries.

#### `POST /api/watchlist`
Adds a movie to the watchlist.
- **Request Body**:
  ```json
  {
    "movie_id": 19995
  }
  ```

#### `DELETE /api/watchlist/{movie_id}`
Removes a movie from the watchlist.

#### `GET /api/watched`
Retrieves movies marked as watched by the user, alongside their ratings.

#### `POST /api/watched`
Marks a movie as watched, rating it between 1.0 and 10.0. Automatically removes it from the user's active watchlist in a single database transaction.
- **Request Body**:
  ```json
  {
    "movie_id": 19995,
    "rating": 8.5
  }
  ```
