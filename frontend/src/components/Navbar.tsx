import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Film, Home, Bookmark, CheckCircle, LogIn, LogOut, UserCircle2 } from 'lucide-react';
import { useMovieStore } from '../store/useMovieStore';
import { useAuthStore } from '../store/useAuthStore';
import { SearchBar } from './SearchBar';
import { AuthModal } from './AuthModal';

const navItems = [
  { to: '/',          icon: Home,        label: 'Home'      },
  { to: '/watchlist', icon: Bookmark,    label: 'Watchlist' },
  { to: '/watched',   icon: CheckCircle, label: 'Watched'   },
];

export function Navbar() {
  const location = useLocation();
  const { watchlist, watched, initStore } = useMovieStore();
  const { isLoggedIn, user, logout } = useAuthStore();
  const [showAuth, setShowAuth] = useState(false);

  const handleLogout = async () => {
    logout();
    // Re-sync store to anonymous session data
    await initStore();
  };

  return (
    <>
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'var(--bg-nav)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border)',
        padding: '0 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        height: 64,
        gap: '16px',
      }}>
        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', flexShrink: 0 }}>
          <Film size={24} color="var(--accent)" />
          <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.5px' }}>
            Rec<span style={{ color: 'var(--accent)' }}>Lens</span>
          </span>
        </Link>

        {/* Global Search */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', maxWidth: 380, margin: '0 8px' }}>
          <SearchBar compact={true} />
        </div>

        {/* Right side: Nav links + Auth */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          {navItems.map(({ to, icon: Icon, label }) => {
            const active = location.pathname === to;
            const count = to === '/watchlist' ? watchlist.length : to === '/watched' ? Object.keys(watched).length : 0;
            return (
              <Link
                key={to}
                to={to}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '7px 13px', borderRadius: 8,
                  textDecoration: 'none', fontSize: '0.87rem', fontWeight: 500,
                  color: active ? 'var(--accent)' : 'var(--text-muted)',
                  background: active ? 'var(--badge-bg)' : 'transparent',
                  transition: 'all 0.18s',
                  position: 'relative',
                }}
                onMouseEnter={(e) => { if (!active) (e.currentTarget as HTMLAnchorElement).style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { if (!active) (e.currentTarget as HTMLAnchorElement).style.color = 'var(--text-muted)'; }}
              >
                <Icon size={15} />
                {label}
                {count > 0 && (
                  <span style={{
                    background: 'var(--accent)', color: 'var(--bg-primary)',
                    fontSize: '0.62rem', fontWeight: 700,
                    padding: '1px 5px', borderRadius: 10,
                    minWidth: 16, textAlign: 'center',
                  }}>
                    {count}
                  </span>
                )}
              </Link>
            );
          })}

          {/* Divider */}
          <div style={{ width: 1, height: 24, background: 'var(--border)', margin: '0 6px' }} />

          {/* Auth area */}
          {isLoggedIn && user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {/* User chip */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '6px 12px', borderRadius: 20,
                background: 'var(--badge-bg)',
                border: '1px solid var(--badge-border)',
                fontSize: '0.82rem', fontWeight: 600,
                color: 'var(--accent)',
              }}>
                <UserCircle2 size={14} />
                {user.username}
              </div>
              {/* Sign out */}
              <button
                onClick={handleLogout}
                title="Sign out"
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '7px 12px', borderRadius: 8,
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontSize: '0.82rem', fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.18s',
                  fontFamily: 'var(--font-body)',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--nord-red)';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--nord-red)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
                }}
              >
                <LogOut size={14} /> Sign out
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuth(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '7px 16px', borderRadius: 8,
                background: 'var(--accent)',
                border: 'none',
                color: 'var(--bg-primary)',
                fontSize: '0.85rem', fontWeight: 700,
                cursor: 'pointer',
                transition: 'filter 0.18s',
                fontFamily: 'var(--font-body)',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.filter = 'brightness(1.12)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.filter = 'none'; }}
            >
              <LogIn size={15} /> Sign In
            </button>
          )}
        </div>
      </nav>

      {/* Auth Modal */}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </>
  );
}
