import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import apiClient from '@/lib/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
  mfa_enabled: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<{ mfaRequired?: boolean; mfaToken?: string }>;
  validateMfa: (mfaToken: string, code: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, organizationName: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  clearError: () => void;
  init: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          // Use form data format for OAuth2PasswordRequestForm
          const formData = new URLSearchParams();
          formData.append('username', email);
          formData.append('password', password);

          const response = await apiClient.post('/auth/login-mfa', formData, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          });
          const data = response.data;

          // Check if MFA is required
          if (data.mfa_required) {
            set({ isLoading: false });
            return { mfaRequired: true, mfaToken: data.mfa_token };
          }

          // Login successful
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          set({
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });

          return {};
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Login failed';
          set({ isLoading: false, error: message });
          throw error;
        }
      },

      validateMfa: async (mfaToken: string, code: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.post('/auth/mfa/validate', {
            mfa_token: mfaToken,
            code,
          });
          const data = response.data;

          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          set({
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'MFA validation failed';
          set({ isLoading: false, error: message });
          throw error;
        }
      },

      register: async (email: string, password: string, fullName: string, organizationName: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.post('/auth/register', {
            email,
            password,
            full_name: fullName,
            organization_name: organizationName,
          });
          const data = response.data;

          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          set({
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Registration failed';
          set({ isLoading: false, error: message });
          throw error;
        }
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) {
          get().logout();
          return;
        }

        try {
          const response = await apiClient.post('/auth/refresh', {
            refresh_token: refreshToken,
          });
          const data = response.data;

          localStorage.setItem('access_token', data.access_token);

          set({
            accessToken: data.access_token,
          });
        } catch {
          get().logout();
        }
      },

      clearError: () => set({ error: null }),

      init: () => {
        // Check if we have tokens in localStorage
        const accessToken = localStorage.getItem('access_token');
        const refreshToken = localStorage.getItem('refresh_token');

        if (accessToken && refreshToken) {
          // Tokens exist - consider authenticated (validated on first API call)
          set({
            accessToken,
            refreshToken,
            isAuthenticated: true,
          });
        } else {
          // No tokens - explicitly reset auth state to prevent stale persisted
          // isAuthenticated: true from causing an infinite /login <-> /dashboard loop
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
