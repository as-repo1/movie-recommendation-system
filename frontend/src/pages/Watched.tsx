import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { CheckCircle, SortAsc, Trash2 } from 'lucide-react';
import { useMovieStore } from '../store/useMovieStore';
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard';
import { api } from '../services/api';

type SortBy = 'date' | 'rating';

export function Watched() {
  const { watched, removeWatched } = useMovieStore();
  const [sortBy, setSortBy] = useState<SortBy>('date');

  const entries = Object.entries(watched) as [string, { rating: number; addedAt: string }][];

  const sorted = [...entries].sort(([, a], [, b]) =>
    sortBy === 'rating'
      ? b.rating - a.rating
      : new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime()
  );

  const ids = sorted.map(([id]) => Number(id));

  // useQueries — proper parallel queries without hooks-in-loop
  const results = useQueries({
    queries: ids.map((id) => ({
      queryKey: ['movie', id],
      queryFn: () => api.getMovie(id),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const loading = results.some((r) => r.isLoading);

  if (ids.length === 0) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 32, display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle size={22} color="#22c55e" /> Watched
        </h1>
        <div style={{ textAlign: 'center', padding: '80px 24px' }}>
          <div style={{ fontSize: '4rem', marginBottom: 16 }}>✅</div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>No watched movies yet</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            Mark movies as watched from the detail page and rate them.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 12 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle size={22} color="#22c55e" /> Watched
        </h1>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SortAsc size={16} color="var(--text-muted)" />
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Sort by:</span>
          {(['date', 'rating'] as SortBy[]).map((s) => (
            <button key={s}
              onClick={() => setSortBy(s)}
              style={{
                padding: '4px 12px', borderRadius: 6, cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500,
                background: sortBy === s ? 'rgba(139,92,246,0.2)' : 'var(--bg-card)',
                border: `1px solid ${sortBy === s ? '#8b5cf6' : 'var(--border)'}`,
                color: sortBy === s ? '#a78bfa' : 'var(--text-muted)',
              }}
            >
              {s === 'date' ? 'Date Added' : 'My Rating'}
            </button>
          ))}
        </div>
      </div>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: 28 }}>
        {ids.length} movie{ids.length !== 1 ? 's' : ''} watched
      </p>

      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
          {ids.map((id) => <MovieCardSkeleton key={id} />)}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
          {results.map((result, i) => {
            const movie = result.data;
            if (!movie) return null;
            return (
              <div key={ids[i]} style={{ position: 'relative' }}>
                <MovieCard movie={movie} showRating />
                <button
                  onClick={() => removeWatched(ids[i])}
                  title="Remove from watched"
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
