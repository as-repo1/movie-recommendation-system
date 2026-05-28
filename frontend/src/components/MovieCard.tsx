import { Link } from 'react-router-dom';
import { Star, Bookmark, BookmarkCheck } from 'lucide-react';
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
    <Link to={`/movie/${movie.id}`} style={{ textDecoration: 'none', display: 'block' }}>
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
        transition: 'transform 0.2s, box-shadow 0.2s',
        cursor: 'pointer',
        position: 'relative',
      }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--glow-purple)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
        }}
      >
        {/* Poster */}
        <div style={{ position: 'relative', aspectRatio: '2/3', overflow: 'hidden' }}>
          <img
            src={movie.poster_url || PLACEHOLDER}
            alt={movie.title}
            loading="lazy"
            onError={(e) => { (e.target as HTMLImageElement).src = PLACEHOLDER; }}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />

          {/* Watchlist button */}
          <button
            onClick={toggleWatchlist}
            style={{
              position: 'absolute', top: 8, right: 8,
              background: 'rgba(0,0,0,0.7)', border: 'none', borderRadius: 8,
              padding: 6, cursor: 'pointer', display: 'flex', alignItems: 'center',
              color: inWatchlist ? '#8b5cf6' : '#94a3b8',
              transition: 'color 0.2s, background 0.2s',
            }}
            title={inWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
          >
            {inWatchlist ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
          </button>

          {/* Watched overlay */}
          {watched && !showRating && (
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
              padding: '20px 8px 8px',
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <Star size={12} fill="#f59e0b" color="#f59e0b" />
              <span style={{ fontSize: '0.75rem', color: '#fcd34d', fontWeight: 600 }}>
                {rating?.toFixed(1)}
              </span>
            </div>
          )}
        </div>

        {/* Info */}
        <div style={{ padding: '10px 12px 12px' }}>
          <p style={{
            fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)',
            lineHeight: 1.3, marginBottom: 4,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {movie.title}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>
              {movie.year ?? ''}
            </span>
            {movie.vote_average > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                <Star size={11} fill="#f59e0b" color="#f59e0b" />
                <span style={{ fontSize: '0.73rem', color: '#fcd34d' }}>
                  {movie.vote_average.toFixed(1)}
                </span>
              </div>
            )}
          </div>

          {showRating && rating !== null && (
            <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Your rating:</span>
              <span style={{ fontSize: '0.78rem', color: '#a78bfa', fontWeight: 600 }}>
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
    <div style={{ borderRadius: 12, overflow: 'hidden', background: 'var(--bg-card)' }}>
      <div className="skeleton" style={{ aspectRatio: '2/3' }} />
      <div style={{ padding: '10px 12px 12px' }}>
        <div className="skeleton" style={{ height: 14, marginBottom: 6 }} />
        <div className="skeleton" style={{ height: 11, width: '60%' }} />
      </div>
    </div>
  );
}
