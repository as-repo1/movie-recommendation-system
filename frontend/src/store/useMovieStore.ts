import { create } from 'zustand';
import { api } from '../services/api';

interface WatchedEntry {
  rating: number;
  addedAt: string;
}

interface MovieStore {
  sessionId: string;
  watchlist: number[];
  watched: Record<number, WatchedEntry>;
  loading: boolean;
  error: string | null;

  initStore: () => Promise<void>;
  addToWatchlist: (id: number) => Promise<void>;
  removeFromWatchlist: (id: number) => Promise<void>;
  isInWatchlist: (id: number) => boolean;

  markWatched: (id: number, rating: number) => Promise<void>;
  updateRating: (id: number, rating: number) => Promise<void>;
  removeWatched: (id: number) => Promise<void>;
  isWatched: (id: number) => boolean;
  getRating: (id: number) => number | null;

  getRatedMovies: () => { movie_id: number; rating: number }[];
}

function getOrGenerateSessionId(): string {
  let sid = localStorage.getItem('reclens-session-id');
  if (!sid) {
    sid = crypto.randomUUID 
      ? crypto.randomUUID() 
      : Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('reclens-session-id', sid);
  }
  return sid;
}

export const useMovieStore = create<MovieStore>((set, get) => ({
  sessionId: getOrGenerateSessionId(),
  watchlist: [],
  watched: {},
  loading: false,
  error: null,

  initStore: async () => {
    set({ loading: true, error: null });
    try {
      const watchlist = await api.getWatchlist();
      const watched = await api.getWatched();
      set({ watchlist, watched, loading: false });
    } catch (e) {
      console.error("Failed to sync store with database:", e);
      set({ error: "Failed to sync with server.", loading: false });
    }
  },

  addToWatchlist: async (id) => {
    try {
      const list = await api.addToWatchlist(id);
      set({ watchlist: list });
    } catch (e) {
      console.error("Failed to add to watchlist:", e);
    }
  },

  removeFromWatchlist: async (id) => {
    try {
      const list = await api.removeFromWatchlist(id);
      set({ watchlist: list });
    } catch (e) {
      console.error("Failed to remove from watchlist:", e);
    }
  },

  isInWatchlist: (id) => get().watchlist.includes(id),

  markWatched: async (id, rating) => {
    try {
      const watched = await api.markWatched(id, rating);
      set((s) => ({
        watched,
        watchlist: s.watchlist.filter((x) => x !== id),
      }));
    } catch (e) {
      console.error("Failed to mark movie as watched:", e);
    }
  },

  updateRating: async (id, rating) => {
    try {
      const watched = await api.updateRating(id, rating);
      set({ watched });
    } catch (e) {
      console.error("Failed to update rating:", e);
    }
  },

  removeWatched: async (id) => {
    try {
      const watched = await api.removeWatched(id);
      set({ watched });
    } catch (e) {
      console.error("Failed to remove from watched:", e);
    }
  },

  isWatched: (id) => id in get().watched,

  getRating: (id) => get().watched[id]?.rating ?? null,

  getRatedMovies: () =>
    Object.entries(get().watched).map(([id, entry]) => ({
      movie_id: Number(id),
      rating: entry.rating,
    })),
}));
