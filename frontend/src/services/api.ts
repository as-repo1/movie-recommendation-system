// Centralised API client for RecLens
const BASE_URL = import.meta.env.VITE_API_URL || '';

export interface Movie {
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
  rotten_tomatoes_score?: string;
  metascore?: string;
  director: string;
  writer: string;
  producers?: string[];
  cast: string[];
  budget?: number;
  revenue?: number;
  certification?: string;
  trailer_url?: string;
  match_percentage?: number | null;
  match_reason?: string;
}

export interface SearchResponse {
  movies: Movie[];
  total: number;
  page: number;
  query: string;
}

export interface SimilarResponse {
  source_movie: Movie;
  recommendations: Movie[];
  engine: string;
}

export interface PersonalisedResponse {
  recommendations: Movie[];
  engine: string;
  user_top_genres?: string[];
}

export interface MoodRecommendationsResponse {
  mood: string;
  recommendations: Movie[];
  total: number;
}

export interface RatedMovie {
  movie_id: number;
  rating: number;
}

export interface AuthUser {
  id: number;
  username: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

// ── Auth header injection ─────────────────────────────────────────────────────
function getHeaders(contentType = true): Record<string, string> {
  const headers: Record<string, string> = {};
  if (contentType) headers['Content-Type'] = 'application/json';

  // Prefer Bearer token if logged in, otherwise anonymous session ID
  const token = localStorage.getItem('reclens-token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Always send X-Session-ID so anonymous data can be migrated on login
  const sid = localStorage.getItem('reclens-session-id');
  if (sid) headers['X-Session-ID'] = sid;

  return headers;
}

// ── HTTP helpers ──────────────────────────────────────────────────────────────
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { headers: getHeaders(false) });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}: ${path}`);
  }
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'PUT',
    headers: getHeaders(true),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'DELETE',
    headers: getHeaders(false),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

// ── Public API ────────────────────────────────────────────────────────────────
export const api = {
  // Movies
  getPopular: (page = 1) =>
    get<Movie[]>(`/api/movies/popular?page=${page}`),
  search: (q: string, page = 1) =>
    get<SearchResponse>(`/api/movies/search?q=${encodeURIComponent(q)}&page=${page}`),
  getMovie: (id: number) =>
    get<Movie>(`/api/movies/${id}`),
  getGenres: () =>
    get<string[]>('/api/movies/genres'),

  // Recommendations
  getSimilar: (id: number, n = 10, useMmr = true) =>
    get<SimilarResponse>(`/api/recommendations/similar/${id}?n=${n}&use_mmr=${useMmr}`),
  getMoodRecommendations: (mood: string, n = 12) =>
    get<MoodRecommendationsResponse>(`/api/recommendations/mood/${encodeURIComponent(mood)}?n=${n}`),
  getPersonalised: (ratings: RatedMovie[], n = 10) =>
    post<PersonalisedResponse>('/api/recommendations/personalised', { ratings, n }),
  getCatalogue: () =>
    get<{ id: number; title: string; year?: number; genres?: string[] }[]>('/api/recommendations/catalogue'),

  // Watchlist & Watched
  getWatchlist: () =>
    get<number[]>('/api/watchlist'),
  addToWatchlist: (movieId: number) =>
    post<number[]>('/api/watchlist', { movie_id: movieId }),
  removeFromWatchlist: (movieId: number) =>
    del<number[]>(`/api/watchlist/${movieId}`),
  getWatched: () =>
    get<Record<number, { rating: number; addedAt: string }>>('/api/watched'),
  markWatched: (movieId: number, rating: number) =>
    post<Record<number, { rating: number; addedAt: string }>>('/api/watched', { movie_id: movieId, rating }),
  updateRating: (movieId: number, rating: number) =>
    put<Record<number, { rating: number; addedAt: string }>>(`/api/watched/${movieId}`, { rating }),
  removeWatched: (movieId: number) =>
    del<Record<number, { rating: number; addedAt: string }>>(`/api/watched/${movieId}`),
  getPersonalisedDb: (n = 10) =>
    get<PersonalisedResponse>(`/api/recommendations/personalised?n=${n}`),

  // Authentication
  register: (username: string, password: string, anonymousSessionId?: string) =>
    post<AuthResponse>('/api/auth/register', { username, password, anonymous_session_id: anonymousSessionId }),
  login: (username: string, password: string, anonymousSessionId?: string) =>
    post<AuthResponse>('/api/auth/login', { username, password, anonymous_session_id: anonymousSessionId }),
  getMe: () =>
    get<AuthUser>('/api/auth/me'),
};
