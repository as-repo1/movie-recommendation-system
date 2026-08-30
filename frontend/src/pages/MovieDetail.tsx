import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Eye,
  Star,
  Clock,
  Calendar,
  ExternalLink,
  DollarSign,
  Play,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { useMovieStore } from '../store/useMovieStore';
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard';
import { RatingStars } from '../components/RatingStars';

const PLACEHOLDER = 'https://placehold.co/300x450/2e3440/88c0d0?text=No+Poster';

function RatingDialog({ onClose, onRate }: { onClose: () => void; onRate: (r: number) => void }) {
  const [rating, setRating] = useState(8);
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 500,
        background: 'rgba(0,0,0,0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backdropFilter: 'blur(6px)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1.5px solid var(--border)',
          borderRadius: 18,
          padding: 32,
          maxWidth: 420,
          width: '90%',
          boxShadow: '0 24px 80px rgba(0,0,0,0.7)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: 6, color: 'var(--text-primary)' }}>
          Rate this movie
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 24 }}>
          Your rating immediately refines your personalized AI recommendations.
        </p>

        <RatingStars value={rating} onChange={setRating} size={28} />

        <div style={{ display: 'flex', gap: 12, marginTop: 28 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '10px 0',
              borderRadius: 10,
              border: '1px solid var(--border)',
              background: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => onRate(rating)}
            style={{
              flex: 1,
              padding: '10px 0',
              borderRadius: 10,
              border: 'none',
              background: 'var(--accent)',
              color: 'var(--bg-primary)',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Save Rating
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
  const [showTrailerModal, setShowTrailerModal] = useState(false);

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
    queryFn: () => api.getSimilar(movieId, 12, true),
    enabled: !!movieId,
  });

  const handleRate = (rating: number) => {
    markWatched(movieId, rating);
    setShowRatingDialog(false);
  };

  const getYoutubeEmbedUrl = (url: string) => {
    const match = url.match(/(?:v=|youtu\.be\/)([\w-]+)/);
    return match ? `https://www.youtube.com/embed/${match[1]}?autoplay=1` : null;
  };

  if (isLoading) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
        <div className="skeleton" style={{ height: 380, borderRadius: 20, marginBottom: 32 }} />
        <div className="skeleton" style={{ height: 36, width: '45%', marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 140 }} />
      </div>
    );
  }

  if (!movie) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <p style={{ color: 'var(--text-muted)' }}>Movie not found in database.</p>
        <button
          onClick={() => navigate('/')}
          style={{
            marginTop: 16,
            padding: '8px 20px',
            borderRadius: 8,
            border: 'none',
            background: 'var(--accent)',
            color: 'var(--bg-primary)',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Return to Home
        </button>
      </div>
    );
  }

  return (
    <>
      {showRatingDialog && (
        <RatingDialog onClose={() => setShowRatingDialog(false)} onRate={handleRate} />
      )}

      {/* Trailer Modal */}
      {showTrailerModal && movie.trailer_url && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 600,
            background: 'rgba(0,0,0,0.88)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backdropFilter: 'blur(8px)',
          }}
          onClick={() => setShowTrailerModal(false)}
        >
          <div
            style={{ width: '90%', maxWidth: 900, aspectRatio: '16/9', background: '#000', borderRadius: 14, overflow: 'hidden' }}
            onClick={(e) => e.stopPropagation()}
          >
            <iframe
              src={getYoutubeEmbedUrl(movie.trailer_url) || ''}
              title="Movie Trailer"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          </div>
        </div>
      )}

      {/* Backdrop Header */}
      <div style={{ position: 'relative', height: 380, overflow: 'hidden' }}>
        <img
          src={movie.backdrop_url || movie.poster_url || PLACEHOLDER}
          alt={movie.title}
          style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'brightness(0.40)' }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(to bottom, transparent 30%, var(--bg-primary) 100%)',
          }}
        />
        <button
          onClick={() => navigate(-1)}
          style={{
            position: 'absolute',
            top: 20,
            left: 20,
            background: 'rgba(15, 23, 42, 0.75)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: '8px 16px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: '0.88rem',
            fontWeight: 600,
            backdropFilter: 'blur(6px)',
          }}
        >
          <ArrowLeft size={16} /> Back
        </button>
      </div>

      <div style={{ maxWidth: 1280, margin: '-130px auto 0', padding: '0 24px 64px', position: 'relative' }}>
        <div style={{ display: 'flex', gap: 36, flexWrap: 'wrap' }}>
          {/* Poster */}
          <div style={{ flexShrink: 0, alignSelf: 'flex-start' }}>
            <img
              src={movie.poster_url || PLACEHOLDER}
              alt={movie.title}
              style={{
                width: 220,
                borderRadius: 16,
                boxShadow: '0 24px 64px rgba(0,0,0,0.75)',
                border: '1.5px solid var(--border)',
              }}
              onError={(e) => {
                (e.target as HTMLImageElement).src = PLACEHOLDER;
              }}
            />
          </div>

          {/* Details */}
          <div style={{ flex: 1, minWidth: 280 }}>
            {movie.tagline && (
              <p style={{ color: 'var(--accent)', fontSize: '0.92rem', fontStyle: 'italic', fontWeight: 600, marginBottom: 6 }}>
                "{movie.tagline}"
              </p>
            )}

            <h1
              style={{
                fontSize: 'clamp(1.8rem, 4vw, 2.8rem)',
                fontWeight: 800,
                marginBottom: 12,
                letterSpacing: '-0.8px',
                lineHeight: 1.2,
              }}
            >
              {movie.title}
            </h1>

            {/* Multi-Source Ratings & Meta Row */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 20 }}>
              {movie.year && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  <Calendar size={15} /> {movie.year}
                </span>
              )}

              {movie.runtime && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  <Clock size={15} /> {movie.runtime} min
                </span>
              )}

              {/* TMDB Rating */}
              {movie.vote_average > 0 && (
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    background: 'rgba(245, 158, 11, 0.12)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    padding: '3px 10px',
                    borderRadius: 16,
                    color: '#fcd34d',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                  }}
                >
                  <Star size={14} fill="#f59e0b" color="#f59e0b" />
                  {movie.vote_average.toFixed(1)}/10
                </span>
              )}

              {/* Rotten Tomatoes */}
              {movie.rotten_tomatoes_score && (
                <span
                  style={{
                    background: 'rgba(239, 68, 68, 0.12)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    padding: '3px 10px',
                    borderRadius: 16,
                    color: '#f87171',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                  }}
                >
                  🍅 {movie.rotten_tomatoes_score}
                </span>
              )}

              {/* Metacritic */}
              {movie.metascore && (
                <span
                  style={{
                    background: 'rgba(34, 197, 94, 0.12)',
                    border: '1px solid rgba(34, 197, 94, 0.3)',
                    padding: '3px 10px',
                    borderRadius: 16,
                    color: '#4ade80',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                  }}
                >
                  Metascore {movie.metascore}
                </span>
              )}
            </div>

            {/* Genres & Mood Pills */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 22 }}>
              {movie.genres.map((g) => (
                <span key={g} className="genre-badge">
                  {g}
                </span>
              ))}
              {movie.moods?.map((m) => (
                <span
                  key={m}
                  style={{
                    background: 'rgba(180, 142, 173, 0.15)',
                    border: '1px solid rgba(180, 142, 173, 0.3)',
                    color: '#d8dee9',
                    padding: '3px 10px',
                    borderRadius: 8,
                    fontSize: '0.78rem',
                    fontWeight: 600,
                  }}
                >
                  ✨ {m.replace('-', ' ')}
                </span>
              ))}
            </div>

            {/* Overview Plot */}
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.75, marginBottom: 28, maxWidth: 680, fontSize: '0.95rem' }}>
              {movie.overview || 'No synopsis available.'}
            </p>

            {/* Filmmaker & Cast Details Card */}
            {(movie.director || movie.writer || (movie.cast && movie.cast.length > 0)) && (
              <div
                style={{
                  background: 'var(--bg-surface)',
                  border: '1.5px solid var(--border)',
                  borderRadius: 14,
                  padding: '18px 22px',
                  marginBottom: 28,
                  maxWidth: 680,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                }}
              >
                {movie.director && (
                  <div style={{ display: 'flex', gap: 10, fontSize: '0.9rem' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, width: 85, flexShrink: 0 }}>Director:</span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{movie.director}</span>
                  </div>
                )}
                {movie.writer && (
                  <div style={{ display: 'flex', gap: 10, fontSize: '0.9rem' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, width: 85, flexShrink: 0 }}>Writer:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{movie.writer}</span>
                  </div>
                )}
                {movie.cast && movie.cast.length > 0 && (
                  <div style={{ display: 'flex', gap: 10, fontSize: '0.9rem', flexWrap: 'wrap' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, width: 85, flexShrink: 0 }}>Cast:</span>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', flex: 1 }}>
                      {movie.cast.map((actor, idx) => (
                        <span
                          key={idx}
                          className="genre-badge"
                          style={{ fontSize: '0.8rem', padding: '2px 9px', borderRadius: 6 }}
                        >
                          {actor}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {((movie.budget && movie.budget > 0) || (movie.revenue && movie.revenue > 0)) && (
                  <div style={{ display: 'flex', gap: 10, fontSize: '0.85rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: 10 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <DollarSign size={13} /> Budget: ${ (movie.budget! / 1_000_000).toFixed(0) }M
                    </span>
                    {movie.revenue && movie.revenue > 0 && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: 2, marginLeft: 16 }}>
                        <DollarSign size={13} /> Box Office: ${ (movie.revenue / 1_000_000).toFixed(0) }M
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 28 }}>
              <button
                onClick={() => (inWatchlist ? removeFromWatchlist(movieId) : addToWatchlist(movieId))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '11px 22px',
                  borderRadius: 10,
                  cursor: 'pointer',
                  fontWeight: 700,
                  background: inWatchlist ? 'rgba(136,192,208,0.2)' : 'var(--bg-card)',
                  border: `1.5px solid ${inWatchlist ? 'var(--accent)' : 'var(--border)'}`,
                  color: inWatchlist ? 'var(--accent)' : 'var(--text-primary)',
                  transition: 'all 0.2s',
                }}
              >
                {inWatchlist ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
                {inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
              </button>

              <button
                onClick={() => setShowRatingDialog(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '11px 22px',
                  borderRadius: 10,
                  cursor: 'pointer',
                  fontWeight: 700,
                  background: watched ? 'rgba(34,197,94,0.15)' : 'var(--accent)',
                  border: watched ? '1.5px solid rgba(34,197,94,0.4)' : 'none',
                  color: watched ? '#4ade80' : 'var(--bg-primary)',
                  transition: 'all 0.2s',
                }}
              >
                <Eye size={18} />
                {watched ? (myRating !== null ? `Watched · ${myRating}/10` : 'Watched') : 'Mark as Watched'}
              </button>

              {movie.trailer_url && (
                <button
                  onClick={() => setShowTrailerModal(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '11px 20px',
                    borderRadius: 10,
                    cursor: 'pointer',
                    fontWeight: 700,
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1.5px solid rgba(239, 68, 68, 0.35)',
                    color: '#f87171',
                  }}
                >
                  <Play size={16} fill="#f87171" /> Watch Trailer
                </button>
              )}
            </div>

            {/* External Links */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', borderTop: '1px solid var(--border)', paddingTop: 20 }}>
              <a
                href={
                  movie.imdb_id
                    ? `https://www.imdb.com/title/${movie.imdb_id}/`
                    : `https://www.imdb.com/find?q=${encodeURIComponent(movie.title)}`
                }
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '7px 14px',
                  borderRadius: 8,
                  fontSize: '0.84rem',
                  fontWeight: 700,
                  textDecoration: 'none',
                  background: '#f5c518',
                  color: '#000000',
                }}
              >
                IMDb <ExternalLink size={13} />
              </a>

              <a
                href={`https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(
                  movie.title + (movie.year ? ` (${movie.year} film)` : ' (film)')
                )}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '7px 14px',
                  borderRadius: 8,
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  textDecoration: 'none',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                }}
              >
                Wikipedia <ExternalLink size={13} />
              </a>
            </div>
          </div>
        </div>

        {/* Similar Recommendations Section */}
        <section style={{ marginTop: 56 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Sparkles size={20} color="var(--accent)" />
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Recommended Similar Films
            </h2>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              (Ranked via Bayesian Quality + Diversity)
            </span>
          </div>

          {loadingSimilar ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 18 }}>
              {Array.from({ length: 6 }, (_, i) => <MovieCardSkeleton key={i} />)}
            </div>
          ) : similar?.recommendations && similar.recommendations.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 18 }}>
              {similar.recommendations.map((m) => (
                <MovieCard key={m.id} movie={m} />
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              No similar movies found in dataset.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
