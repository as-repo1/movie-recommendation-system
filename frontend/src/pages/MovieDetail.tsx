import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Bookmark, BookmarkCheck, Eye, Star, Clock, Calendar, ExternalLink } from 'lucide-react';
import { api } from '../services/api';
import { useMovieStore } from '../store/useMovieStore';
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard';
import { RatingStars } from '../components/RatingStars';

const PLACEHOLDER = 'https://placehold.co/300x450/2e3440/88c0d0?text=No+Poster';

function RatingDialog({ onClose, onRate }: { onClose: () => void; onRate: (r: number) => void }) {
  const [rating, setRating] = useState(7);
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 500,
      background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 16, padding: 32, maxWidth: 400, width: '90%',
      }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 8 }}>Rate this movie</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 24 }}>
          Your rating helps personalise your recommendations.
        </p>
        <RatingStars value={rating} onChange={setRating} size={28} />
        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <button onClick={onClose}
            style={{ flex: 1, padding: '10px 0', borderRadius: 8, border: '1px solid var(--border)', background: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            Cancel
          </button>
          <button onClick={() => onRate(rating)}
            style={{ flex: 1, padding: '10px 0', borderRadius: 8, border: 'none', background: '#8b5cf6', color: 'white', fontWeight: 600, cursor: 'pointer' }}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export function MovieDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const movieId = Number(id);
  const [showRatingDialog, setShowRatingDialog] = useState(false);

  const { isInWatchlist, addToWatchlist, removeFromWatchlist, markWatched, isWatched, getRating } = useMovieStore();
  const inWatchlist = isInWatchlist(movieId);
  const watched = isWatched(movieId);
  const myRating = getRating(movieId);

  const { data: movie, isLoading } = useQuery({
    queryKey: ['movie', movieId],
    queryFn: () => api.getMovie(movieId),
    enabled: !!movieId,
  });

  const { data: similar, isLoading: loadingSimilar } = useQuery({
    queryKey: ['similar', movieId],
    queryFn: () => api.getSimilar(movieId, 8),
    enabled: !!movieId,
  });

  const handleRate = (rating: number) => {
    markWatched(movieId, rating);
    setShowRatingDialog(false);
  };

  if (isLoading) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
        <div className="skeleton" style={{ height: 400, borderRadius: 16, marginBottom: 32 }} />
        <div className="skeleton" style={{ height: 32, width: '40%', marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 120 }} />
      </div>
    );
  }

  if (!movie) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <p style={{ color: 'var(--text-muted)' }}>Movie not found.</p>
      </div>
    );
  }

  return (
    <>
      {showRatingDialog && (
        <RatingDialog
          onClose={() => setShowRatingDialog(false)}
          onRate={handleRate}
        />
      )}

      {/* Backdrop */}
      <div style={{ position: 'relative', height: 360, overflow: 'hidden' }}>
        <img
          src={movie.backdrop_url || movie.poster_url || PLACEHOLDER}
          alt={movie.title}
          style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'brightness(0.45)' }}
        />
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(to bottom, transparent 30%, var(--bg-primary) 100%)',
        }} />
        <button onClick={() => navigate(-1)} style={{
          position: 'absolute', top: 20, left: 20,
          background: 'rgba(0,0,0,0.6)', border: 'none', borderRadius: 8,
          padding: '8px 14px', color: 'white', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.88rem',
        }}>
          <ArrowLeft size={16} /> Back
        </button>
      </div>

      <div style={{ maxWidth: 1280, margin: '-120px auto 0', padding: '0 24px 48px', position: 'relative' }}>
        <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          {/* Poster */}
          <img
            src={movie.poster_url || PLACEHOLDER}
            alt={movie.title}
            style={{ width: 200, borderRadius: 12, flexShrink: 0, boxShadow: '0 20px 60px rgba(0,0,0,0.6)', alignSelf: 'flex-start' }}
            onError={(e) => { (e.target as HTMLImageElement).src = PLACEHOLDER; }}
          />

          {/* Info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <h1 style={{ fontSize: 'clamp(1.5rem, 4vw, 2.5rem)', fontWeight: 800, marginBottom: 8, letterSpacing: '-0.5px' }}>
              {movie.title}
            </h1>

            {/* Meta row */}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 16, color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              {movie.year && <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Calendar size={14} />{movie.year}</span>}
              {movie.runtime && <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Clock size={14} />{movie.runtime} min</span>}
              {movie.vote_average > 0 && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Star size={14} fill="#f59e0b" color="#f59e0b" />
                  {movie.vote_average.toFixed(1)}/10
                </span>
              )}
            </div>

            {/* Genres */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
              {movie.genres.map(g => <span key={g} className="genre-badge">{g}</span>)}
            </div>

            {/* Overview */}
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: 28, maxWidth: 640 }}>
              {movie.overview || 'No overview available.'}
            </p>

            {/* Additional Details (Director, Writer, Cast) */}
            {(movie.director || movie.writer || (movie.cast && movie.cast.length > 0)) && (
              <div style={{
                background: 'var(--bg-surface)',
                border: '1.5px solid var(--border)',
                borderRadius: 12,
                padding: '16px 20px',
                marginBottom: 28,
                maxWidth: 640,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}>
                {movie.director && (
                  <div style={{ display: 'flex', gap: 8, fontSize: '0.9rem' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, width: 80, flexShrink: 0 }}>Director:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{movie.director}</span>
                  </div>
                )}
                {movie.writer && (
                  <div style={{ display: 'flex', gap: 8, fontSize: '0.9rem' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, width: 80, flexShrink: 0 }}>Writer:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{movie.writer}</span>
                  </div>
                )}
                {movie.cast && movie.cast.length > 0 && (
                  <div style={{ display: 'flex', gap: 8, fontSize: '0.9rem', flexWrap: 'wrap' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, width: 80, flexShrink: 0 }}>Cast:</span>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', flex: 1 }}>
                      {movie.cast.map((actor, idx) => (
                        <span key={idx} className="genre-badge" style={{
                          fontSize: '0.78rem',
                          padding: '2px 8px',
                          borderRadius: 6,
                        }}>
                          {actor}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Your rating */}
            {watched && myRating !== null && (
              <div style={{ marginBottom: 20 }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 6 }}>Your rating</p>
                <RatingStars value={myRating} readonly size={18} />
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button
                onClick={() => inWatchlist ? removeFromWatchlist(movieId) : addToWatchlist(movieId)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '10px 20px', borderRadius: 8, cursor: 'pointer', fontWeight: 600,
                  background: inWatchlist ? 'rgba(139,92,246,0.2)' : 'var(--bg-card)',
                  border: `1px solid ${inWatchlist ? '#8b5cf6' : 'var(--border)'}`,
                  color: inWatchlist ? '#a78bfa' : 'var(--text-primary)',
                  transition: 'all 0.2s',
                }}
              >
                {inWatchlist ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                {inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
              </button>

              <button
                onClick={() => setShowRatingDialog(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '10px 20px', borderRadius: 8, cursor: 'pointer', fontWeight: 600,
                  background: watched ? 'rgba(34,197,94,0.15)' : '#8b5cf6',
                  border: watched ? '1px solid rgba(34,197,94,0.4)' : 'none',
                  color: watched ? '#4ade80' : 'white',
                  transition: 'all 0.2s',
                }}
              >
                <Eye size={16} />
                {watched ? (myRating !== null ? `Watched · ${myRating}/10` : 'Watched') : 'Mark as Watched'}
              </button>
            </div>

            {/* External Links */}
            <div style={{ display: 'flex', gap: 12, marginTop: 24, flexWrap: 'wrap', borderTop: '1px solid var(--border)', paddingTop: 20 }}>
              <a
                href={movie.imdb_id ? `https://www.imdb.com/title/${movie.imdb_id}/` : `https://www.imdb.com/find?q=${encodeURIComponent(movie.title)}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  padding: '8px 16px', borderRadius: 8, fontSize: '0.85rem', fontWeight: 600,
                  textDecoration: 'none', background: '#f5c518', color: '#000000',
                  transition: 'opacity 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.9'; }}
                onMouseLeave={(e) => { e.currentTarget.style.opacity = '1'; }}
              >
                🎬 IMDb <ExternalLink size={14} />
              </a>

              <a
                href={`https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(movie.title + (movie.year ? ' (' + movie.year + ' film)' : ' (film)'))}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  padding: '8px 16px', borderRadius: 8, fontSize: '0.85rem', fontWeight: 600,
                  textDecoration: 'none', background: 'var(--bg-card)', border: '1px solid var(--border)',
                  color: 'var(--text-primary)', transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
              >
                🌐 Wikipedia <ExternalLink size={14} />
              </a>
            </div>
          </div>
        </div>

        {/* Similar Movies */}
        <section style={{ marginTop: 48 }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 20 }}>Similar Movies</h2>
          {loadingSimilar ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 16 }}>
              {Array.from({ length: 6 }, (_, i) => <MovieCardSkeleton key={i} />)}
            </div>
          ) : similar?.recommendations && similar.recommendations.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 16 }}>
              {similar.recommendations.map(m => <MovieCard key={m.id} movie={m} />)}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              No similar movies found in the dataset.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
