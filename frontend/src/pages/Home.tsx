import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, Compass, Film } from 'lucide-react';
import { api } from '../services/api';
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard';
import { SearchBar } from '../components/SearchBar';
import { useMovieStore } from '../store/useMovieStore';

const MOODS = [
  { id: 'all', label: '🔥 All Popular' },
  { id: 'mind-bending', label: '🧠 Mind-Bending' },
  { id: 'dark-thriller', label: '🕵️ Dark Thrillers' },
  { id: 'feel-good', label: '🍿 Feel-Good' },
  { id: 'adrenaline-action', label: '⚡ Action & Adrenaline' },
  { id: 'epic-journey', label: '🏰 Epic Fantasy' },
  { id: 'emotional-drama', label: '❤️ Emotional Drama' },
];

export function Home() {
  const { getRatedMovies } = useMovieStore();
  const [selectedMood, setSelectedMood] = useState<string>('all');
  const rated = getRatedMovies();

  // Query popular
  const { data: popular, isLoading: loadingPopular } = useQuery({
    queryKey: ['popular'],
    queryFn: () => api.getPopular(),
  });

  // Query personalized recommendations
  const { data: personalised, isLoading: loadingPersonal } = useQuery({
    queryKey: ['personalised', rated.map(r => `${r.movie_id}:${r.rating}`).join(',')],
    queryFn: () => api.getPersonalisedDb(12),
    enabled: rated.length > 0,
    retry: false,
  });

  // Query mood recommendations
  const { data: moodData, isLoading: loadingMood } = useQuery({
    queryKey: ['mood', selectedMood],
    queryFn: () => api.getMoodRecommendations(selectedMood, 12),
    enabled: selectedMood !== 'all',
  });

  const activeMovies = selectedMood === 'all' ? (popular ?? []) : (moodData?.recommendations ?? []);
  const isLoadingActive = selectedMood === 'all' ? loadingPopular : loadingMood;

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
      {/* Hero Section */}
      <div
        style={{
          textAlign: 'center',
          marginBottom: 44,
          background: 'radial-gradient(ellipse at center top, rgba(136,192,208,0.18) 0%, transparent 70%)',
          padding: '48px 24px 12px',
          borderRadius: 24,
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--badge-bg)',
            border: '1px solid var(--badge-border)',
            padding: '4px 14px',
            borderRadius: 20,
            fontSize: '0.8rem',
            color: 'var(--accent)',
            fontWeight: 600,
            marginBottom: 16,
          }}
        >
          <Sparkles size={13} /> Multi-Model AI Engine · Bayesian Quality Scoring
        </div>

        <h1
          style={{
            fontSize: 'clamp(2.2rem, 5vw, 3.8rem)',
            fontWeight: 800,
            background: 'linear-gradient(135deg, #eceff4 20%, #88c0d0 60%, #b48ead 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            marginBottom: 12,
            letterSpacing: '-1.2px',
          }}
        >
          Discover Your Next<br />Favourite Film
        </h1>

        <p style={{ color: 'var(--text-muted)', fontSize: '1.02rem', marginBottom: 28, maxWidth: 540, margin: '0 auto 28px' }}>
          Personalized hybrid recommendations powered by semantic TF-IDF, LightFM, and rich movie context.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <SearchBar />
        </div>
      </div>

      {/* Personalised Recommendations Section */}
      {rated.length > 0 && (
        <section style={{ marginBottom: 48 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18, flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={20} color="var(--accent)" />
              <h2 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                Personalized For You
              </h2>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                ({rated.length} rating{rated.length > 1 ? 's' : ''})
              </span>
            </div>

            {personalised?.user_top_genres && personalised.user_top_genres.length > 0 && (
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Top genres:</span>
                {personalised.user_top_genres.map((g) => (
                  <span key={g} className="genre-badge" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                    {g}
                  </span>
                ))}
              </div>
            )}
          </div>

          {loadingPersonal ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 18 }}>
              {Array.from({ length: 6 }, (_, i) => <MovieCardSkeleton key={i} />)}
            </div>
          ) : personalised?.recommendations && personalised.recommendations.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 18 }}>
              {personalised.recommendations.map(m => <MovieCard key={m.id} movie={m} />)}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              Rate more movies to generate fine-tuned personalized recommendations.
            </p>
          )}
        </section>
      )}

      {/* Mood & Catalog Explorer */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18, flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Compass size={20} color="var(--accent)" />
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Explore by Vibe & Mood
            </h2>
          </div>
        </div>

        {/* Mood Pills */}
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 12, marginBottom: 20 }}>
          {MOODS.map((m) => {
            const active = selectedMood === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setSelectedMood(m.id)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 20,
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: `1.5px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                  background: active ? 'var(--badge-bg)' : 'var(--bg-card)',
                  color: active ? 'var(--accent)' : 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.18s ease',
                }}
              >
                {m.label}
              </button>
            );
          })}
        </div>

        {/* Movies Grid */}
        {isLoadingActive ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 18 }}>
            {Array.from({ length: 12 }, (_, i) => <MovieCardSkeleton key={i} />)}
          </div>
        ) : activeMovies.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 18 }}>
            {activeMovies.map(m => <MovieCard key={m.id} movie={m} />)}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
            <Film size={36} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
            <p>No movies found for this mood filter.</p>
          </div>
        )}
      </section>
    </div>
  );
}
