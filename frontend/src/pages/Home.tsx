import { useQuery } from '@tanstack/react-query';
import { Sparkles, TrendingUp } from 'lucide-react';
import { api } from '../services/api';
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard';
import { SearchBar } from '../components/SearchBar';
import { useMovieStore } from '../store/useMovieStore';


export function Home() {
  const { getRatedMovies } = useMovieStore();
  const rated = getRatedMovies();

  const { data: popular, isLoading: loadingPopular } = useQuery({
    queryKey: ['popular'],
    queryFn: () => api.getPopular(),
  });

  const { data: personalised, isLoading: loadingPersonal } = useQuery({
    queryKey: ['personalised', rated.map(r => r.movie_id).join(',')],
    queryFn: () => api.getPersonalisedDb(12),
    enabled: rated.length > 0,
    retry: false,
  });

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
      {/* Hero */}
      <div style={{
        textAlign: 'center', marginBottom: 48,
        background: 'radial-gradient(ellipse at center top, rgba(139,92,246,0.15) 0%, transparent 70%)',
        padding: '48px 24px 0',
        borderRadius: 24,
      }}>
        <h1 style={{
          fontSize: 'clamp(2rem, 5vw, 3.5rem)', fontWeight: 800,
          background: 'linear-gradient(135deg, #e2e8f0 30%, #a78bfa 70%)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          backgroundClip: 'text', marginBottom: 12, letterSpacing: '-1px',
        }}>
          Discover Your Next<br />Favourite Film
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem', marginBottom: 32 }}>
          AI-powered recommendations based on what you love
        </p>
        <SearchBar />
      </div>

      {/* Personalised section */}
      {rated.length > 0 && (
        <section style={{ marginBottom: 48 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Sparkles size={20} color="#8b5cf6" />
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Recommended For You
            </h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 4 }}>
              based on {rated.length} rating{rated.length > 1 ? 's' : ''}
            </span>
          </div>
          {loadingPersonal ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
              {Array.from({ length: 6 }, (_, i) => <MovieCardSkeleton key={i} />)}
            </div>
          ) : personalised?.recommendations && personalised.recommendations.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
              {personalised.recommendations.map(m => <MovieCard key={m.id} movie={m} />)}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              Rate more movies to get personalised recommendations.
            </p>
          )}
        </section>
      )}

      {/* Popular */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <TrendingUp size={20} color="#3b82f6" />
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Popular Movies
          </h2>
        </div>
        {loadingPopular ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
            {Array.from({ length: 12 }, (_, i) => <MovieCardSkeleton key={i} />)}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 16 }}>
            {(popular ?? []).map(m => <MovieCard key={m.id} movie={m} />)}
          </div>
        )}
      </section>
    </div>
  );
}
