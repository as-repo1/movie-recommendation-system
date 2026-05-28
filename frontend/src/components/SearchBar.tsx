import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { api } from '../services/api';
import type { Movie } from '../services/api';

export interface SearchBarProps {
  compact?: boolean;
}

export function SearchBar({ compact = false }: SearchBarProps) {
  const [query, setQuery]     = useState('');
  const [results, setResults] = useState<Movie[]>([]);
  const [open, setOpen]       = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    try {
      const data = await api.search(q);
      setResults(data.movies.slice(0, 8));
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => doSearch(query), 300);
    return () => clearTimeout(t);
  }, [query, doSearch]);

  const pick = (movie: Movie) => {
    setOpen(false);
    setQuery('');
    navigate(`/movie/${movie.id}`);
  };

  return (
    <div style={{ position: 'relative', width: '100%', maxWidth: compact ? 320 : 560 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: compact ? 6 : 10,
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: compact ? 8 : 12, padding: compact ? '6px 12px' : '10px 16px',
        transition: 'border-color 0.2s',
        borderColor: open ? 'rgba(139,92,246,0.5)' : 'var(--border)',
        boxShadow: open ? 'var(--glow-purple)' : 'none',
      }}>
        <Search size={compact ? 15 : 18} color="#8b5cf6" />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Search movies…"
          style={{
            flex: 1, background: 'none', border: 'none', outline: 'none',
            color: 'var(--text-primary)', fontSize: compact ? '0.85rem' : '0.95rem',
          }}
        />
        {query && (
          <X size={compact ? 14 : 16} color="#475569" style={{ cursor: 'pointer' }}
            onClick={() => { setQuery(''); setResults([]); }} />
        )}
      </div>

      {/* Dropdown */}
      {open && (results.length > 0 || loading) && (
        <div style={{
          position: 'absolute', top: compact ? 'calc(100% + 4px)' : 'calc(100% + 8px)', left: 0, right: 0,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: compact ? 8 : 12, overflow: 'hidden', zIndex: 200,
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        }}>
          {loading && <div style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Searching…</div>}
          {results.map((m) => (
            <div key={m.id}
              onMouseDown={() => pick(m)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 16px', cursor: 'pointer',
                borderBottom: '1px solid var(--border)',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <img
                src={m.poster_url}
                alt={m.title}
                style={{ width: 36, height: 54, objectFit: 'cover', borderRadius: 4, flexShrink: 0 }}
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              <div>
                <p style={{ fontSize: '0.88rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: 2 }}>
                  {m.title}
                </p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {m.year ?? ''}{m.genres[0] ? ` · ${m.genres[0]}` : ''}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
