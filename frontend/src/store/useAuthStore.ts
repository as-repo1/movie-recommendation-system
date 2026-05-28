import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthUser } from '../services/api';
import { api } from '../services/api';

interface AuthStore {
  token: string | null;
  user: AuthUser | null;
  isLoggedIn: boolean;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isLoggedIn: false,

      login: async (username, password) => {
        const sid = localStorage.getItem('reclens-session-id') ?? undefined;
        const res = await api.login(username, password, sid);
        // Persist token so api.ts picks it up on next request
        localStorage.setItem('reclens-token', res.access_token);
        set({ token: res.access_token, user: res.user, isLoggedIn: true });
      },

      register: async (username, password) => {
        const sid = localStorage.getItem('reclens-session-id') ?? undefined;
        const res = await api.register(username, password, sid);
        localStorage.setItem('reclens-token', res.access_token);
        set({ token: res.access_token, user: res.user, isLoggedIn: true });
      },

      logout: () => {
        localStorage.removeItem('reclens-token');
        set({ token: null, user: null, isLoggedIn: false });
      },
    }),
    {
      name: 'reclens-auth',
      partialize: (s) => ({ token: s.token, user: s.user, isLoggedIn: s.isLoggedIn }),
      onRehydrateStorage: () => (state) => {
        // Re-sync token into localStorage so api.ts always has it
        if (state?.token) {
          localStorage.setItem('reclens-token', state.token);
        }
      },
    }
  )
);
