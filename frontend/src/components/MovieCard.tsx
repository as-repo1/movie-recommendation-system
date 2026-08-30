import { Link } from 'react-router-dom';
import { Star, Bookmark, BookmarkCheck, Sparkles } from 'lucide-react';
import type { Movie } from '../services/api';
import { useMovieStore } from '../store/useMovieStore';

interface MovieCardProps {
  movie: Movie;
  showRating?: boolean;
}

const PLACEHOLDER = 'https://placehold.co/300x450/2e3440/88c0d0?text=No+Poster';

export function MovieCard({ movie, showRating = false }: MovieCardProps) {
  const { isInWatchlist, addToWatchlist, removeFromWatchlist, getRating, isWatched } = useMovieStore();
  const inWatchlist = isInWatchlist(movie.id);
  const rating = getRating(movie.id);
  const watched = isWatched(movie.id);

  const toggleWatchlist = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    inWatchlist ? removeFromWatchlist(movie.id) : addToWatchlist(movie.id);
  };

  return (
    <Link to={`/movie/${movie.id}`} style={{ textDecoration: 'none', display: 'block', height: '100%' }}>
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          overflow: 'hidden',
          transition: 'transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s ease, border-color 0.22s ease',
          cursor: 'pointer',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-5px)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 16px 36px rgba(136, 192, 208, 0.16)';
          (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--accent)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
          (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)';
        }}
      >
        {/* Poster Container */}
        <div style={{ position: 'relative', aspectRatio: '2/3', overflow: 'hidden', background: '#1a1c23' }}>
          <img
            src={movie.poster_url || PLACEHOLDER}
            alt={movie.title}
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).src = PLACEHOLDER;
            }}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />

          {/* Match percentage pill */}
          {movie.match_percentage && (
            <div
              style={{
                position: 'absolute',
                top: 8,
                left: 8,
                background: 'rgba(15, 23, 42, 0.82)',
                border: '1px solid var(--accent)',
                color: 'var(--accent)',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 20,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                backdropFilter: 'blur(6px)',
              }}
            >
              <Sparkles size={11} /> {movie.match_percentage}%
            </div>
          )}

          {/* Watchlist button */}
          <button
            onClick={toggleWatchlist}
            style={{
              position: 'absolute',
              top: 8,
              right: 8,
              background: 'rgba(15, 23, 42, 0.75)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              padding: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: inWatchlist ? 'var(--accent)' : '#94a3b8',
              backdropFilter: 'blur(6px)',
              transition: 'color 0.2s, background 0.2s',
            }}
            title={inWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
          >
            {inWatchlist ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
          </button>

          {/* Watched overlay */}
          {watched && !showRating && (
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                background: 'linear-gradient(transparent, rgba(15, 23, 42, 0.9))',
                padding: '20px 8px 8px',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Star size={12} fill="#f59e0b" color="#f59e0b" />
              <span style={{ fontSize: '0.75rem', color: '#fcd34d', fontWeight: 600 }}>
                {rating?.toFixed(1)}/10
              </span>
            </div>
          )}
        </div>

        {/* Info */}
        <div style={{ padding: '10px 12px 12px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <p
              style={{
                fontSize: '0.85rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: 1.3,
                marginBottom: 4,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={movie.title}
            >
              {movie.title}
            </p>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                {movie.year ?? ''}
              </span>
              {movie.vote_average > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                  <Star size={11} fill="#f59e0b" color="#f59e0b" />
                  <span style={{ fontSize: '0.74rem', color: '#fcd34d', fontWeight: 600 }}>
                    {movie.vote_average.toFixed(1)}
                  </span>
                </div>
              )}
            </div>

            {/* Match explanation reason */}
            {movie.match_reason && (
              <p
                style={{
                  fontSize: '0.71rem',
                  color: 'var(--text-muted)',
                  lineHeight: 1.25,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {movie.match_reason}
              </p>
            )}
          </div>

          {showRating && rating !== null && (
            <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 4, borderTop: '1px solid var(--border)', paddingTop: 6 }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>My Rating:</span>
              <span style={{ fontSize: '0.78rem', color: 'var(--accent)', fontWeight: 700 }}>
                {rating.toFixed(1)}/10
              </span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

/* Skeleton card */
export function MovieCardSkeleton() {
  return (
    <div style={{ borderRadius: 14, overflow: 'hidden', background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
      <div className="skeleton" style={{ aspectRatio: '2/3' }} />
      <div style={{ padding: '10px 12px 12px' }}>
        <div className="skeleton" style={{ height: 14, marginBottom: 6 }} />
        <div className="skeleton" style={{ height: 11, width: '60%' }} />
      </div>
    </div>
  );
}
