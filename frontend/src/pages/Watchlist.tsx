import { useQueries } from '@tanstack/react-query';
import { Bookmark, Trash2 } from 'lucide-react';
import { useMovieStore } from '../store/useMovieStore';
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard';
import { api } from '../services/api';

export function Watchlist() {
  const { watchlist, removeFromWatchlist } = useMovieStore();

  // useQueries — the correct React-safe way to run N parallel queries
  const results = useQueries({
    queries: watchlist.map((id) => ({
      queryKey: ['movie', id],
      queryFn: () => api.getMovie(id),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const loading = results.some((r) => r.isLoading);

  if (watchlist.length === 0) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 32, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Bookmark size={22} color="#8b5cf6" /> Watchlist
        </h1>
        <div style={{ textAlign: 'center', padding: '80px 24px' }}>
          <div style={{ fontSize: '4rem', marginBottom: 16 }}>🎬</div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>Your watchlist is empty</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            Open any movie and click "Add to Watchlist".
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Bookmark size={22} color="#8b5cf6" /> Watchlist
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: 28 }}>
        {watchlist.length} movie{watchlist.length !== 1 ? 's' : ''} saved
      </p>

      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
          {watchlist.map((id) => <MovieCardSkeleton key={id} />)}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
          {results.map((result) => {
            const movie = result.data;
            if (!movie) return null;
            return (
              <div key={movie.id} style={{ position: 'relative' }}>
                <MovieCard movie={movie} />
                <button
                  onClick={() => removeFromWatchlist(movie.id)}
                  title="Remove from watchlist"
                  style={{
                    position: 'absolute', bottom: 56, right: 8,
                    background: 'rgba(239,68,68,0.85)', border: 'none', borderRadius: 6,
                    padding: 5, cursor: 'pointer', color: 'white', display: 'flex',
                  }}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
