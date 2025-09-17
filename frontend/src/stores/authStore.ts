// frontend/src/stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, UserRole, LoginRequest, RegisterRequest, AuthError } from '../types/auth';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: AuthError | null;
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshTokens: () => Promise<void>;
  updateUser: (data: Partial<User>) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  checkAuth: () => Promise<void>;
}

type AuthStore = AuthState & AuthActions;

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Helper function to make authenticated requests
const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}, token?: string) => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(errorData.detail || 'Request failed');
  }

  return response.json();
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (email: string, password: string) => {
        try {
          set({ isLoading: true, error: null });

          const response = await makeAuthenticatedRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
          });

          set({
            user: response.user,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            error: { message: error instanceof Error ? error.message : 'Login failed' },
            isLoading: false,
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null });

          const response = await makeAuthenticatedRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
          });

          // After registration, automatically log in
          await get().login(data.email, data.password);
        } catch (error) {
          set({
            error: { message: error instanceof Error ? error.message : 'Registration failed' },
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshTokens: async () => {
        try {
          const { refreshToken } = get();
          if (!refreshToken) {
            throw new Error('No refresh token available');
          }

          const response = await makeAuthenticatedRequest('/api/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          set({
            accessToken: response.access_token,
            error: null,
          });
        } catch (error) {
          // If refresh fails, logout
          get().logout();
          throw error;
        }
      },

      updateUser: async (data: Partial<User>) => {
        try {
          const { accessToken } = get();
          if (!accessToken) {
            throw new Error('Not authenticated');
          }

          const response = await makeAuthenticatedRequest('/api/auth/me', {
            method: 'PUT',
            body: JSON.stringify(data),
          }, accessToken);

          set((state) => ({
            user: state.user ? { ...state.user, ...response } : null,
          }));
        } catch (error) {
          set({
            error: { message: error instanceof Error ? error.message : 'Update failed' },
          });
          throw error;
        }
      },

      changePassword: async (currentPassword: string, newPassword: string) => {
        try {
          const { accessToken } = get();
          if (!accessToken) {
            throw new Error('Not authenticated');
          }

          await makeAuthenticatedRequest('/api/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
              current_password: currentPassword,
              new_password: newPassword,
            }),
          }, accessToken);

          set({ error: null });
        } catch (error) {
          set({
            error: { message: error instanceof Error ? error.message : 'Password change failed' },
          });
          throw error;
        }
      },

      checkAuth: async () => {
        try {
          const { accessToken } = get();
          if (!accessToken) {
            return;
          }

          const response = await makeAuthenticatedRequest('/api/auth/me', {
            method: 'GET',
          }, accessToken);

          set({
            user: response,
            isAuthenticated: true,
            error: null,
          });
        } catch (error) {
          // Try to refresh token
          try {
            await get().refreshTokens();
            await get().checkAuth();
          } catch (refreshError) {
            get().logout();
          }
        }
      },

      clearError: () => set({ error: null }),

      setLoading: (loading: boolean) => set({ isLoading: loading }),
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

// Helper hooks
export const useAuth = () => {
  const authStore = useAuthStore();
  return authStore;
};

export const useUser = () => {
  const user = useAuthStore((state) => state.user);
  return user;
};

export const useIsAuthenticated = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated;
};

export const useUserRole = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role;
};

// Role checking utilities
export const hasRole = (user: User | null, roles: UserRole[]): boolean => {
  if (!user) return false;
  return roles.includes(user.role);
};

export const isAdmin = (user: User | null): boolean => {
  return hasRole(user, [UserRole.ADMIN]);
};

export const isDoctor = (user: User | null): boolean => {
  return hasRole(user, [UserRole.DOCTOR]);
};

export const isPatient = (user: User | null): boolean => {
  return hasRole(user, [UserRole.PATIENT]);
};

export const canAccessDoctorFeatures = (user: User | null): boolean => {
  return hasRole(user, [UserRole.DOCTOR, UserRole.ADMIN]);
};

export const canAccessPatientFeatures = (user: User | null): boolean => {
  return hasRole(user, [UserRole.PATIENT, UserRole.ADMIN]);
};

export const canAccessAdminFeatures = (user: User | null): boolean => {
  return hasRole(user, [UserRole.ADMIN]);
};