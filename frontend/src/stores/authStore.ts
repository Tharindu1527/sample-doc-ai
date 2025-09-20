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

// Use proxy URL in development
const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? '' // Use proxy in package.json
  : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

// Enhanced helper function to make authenticated requests
const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}) => {
  // Get the current token from the store
  const state = useAuthStore.getState();
  const token = state.accessToken;

  if (!token) {
    console.error('No access token available for authenticated request');
    throw new Error('Authentication required. Please log in again.');
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...((options.headers as Record<string, string>) || {}),
  };

  console.log(`Making authenticated request to: ${url}`);
  
  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    console.log(`Response status: ${response.status} ${response.statusText}`);

    // Handle token expiration
    if (response.status === 401) {
      console.log('Token expired, attempting refresh...');
      try {
        await state.refreshTokens();
        // Retry the request with new token
        const newState = useAuthStore.getState();
        const newToken = newState.accessToken;
        
        if (newToken) {
          headers['Authorization'] = `Bearer ${newToken}`;
          console.log('Retrying request with refreshed token');
          
          const retryResponse = await fetch(`${API_BASE_URL}${url}`, {
            ...options,
            headers,
          });
          
          if (!retryResponse.ok) {
            const errorData = await retryResponse.json().catch(() => ({ detail: 'An error occurred' }));
            throw new Error(errorData.detail || `HTTP ${retryResponse.status}: ${retryResponse.statusText}`);
          }
          
          return retryResponse.json();
        } else {
          throw new Error('Failed to refresh token');
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        // Force logout if refresh fails
        state.logout();
        window.location.href = '/login';
        throw new Error('Session expired. Please log in again.');
      }
    }

    if (response.status === 403) {
      throw new Error('Access denied. You do not have permission to perform this action.');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'An error occurred' }));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    console.error('Authenticated request failed:', error);
    throw error;
  }
};

// Create a version that doesn't require authentication for login/register
const makePublicRequest = async (url: string, options: RequestInit = {}) => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  console.log(`Making public request to: ${url}`);
  
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  console.log(`Response status: ${response.status} ${response.statusText}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
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

          const response = await makePublicRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
          });

          console.log('Login successful, user:', response.user);
          console.log('Access token received:', response.access_token ? 'Yes' : 'No');

          set({
            user: response.user,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          console.error('Login error:', errorMessage);
          set({
            error: { message: errorMessage },
            isLoading: false,
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null });

          const response = await makePublicRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
          });

          console.log('Registration response:', response);

          // After registration, automatically log in
          await get().login(data.email, data.password);
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed';
          console.error('Registration error:', errorMessage);
          set({
            error: { message: errorMessage },
            isLoading: false,
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
          });
          throw error;
        }
      },

      logout: () => {
        console.log('Logging out user');
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

          const response = await makePublicRequest('/api/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          set({
            accessToken: response.access_token,
            error: null,
          });
        } catch (error) {
          console.error('Token refresh error:', error);
          // If refresh fails, logout
          get().logout();
          throw error;
        }
      },

      updateUser: async (data: Partial<User>) => {
        try {
          const response = await makeAuthenticatedRequest('/api/auth/me', {
            method: 'PUT',
            body: JSON.stringify(data),
          });

          set((state) => ({
            user: state.user ? { ...state.user, ...response } : null,
          }));
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Update failed';
          set({
            error: { message: errorMessage },
          });
          throw error;
        }
      },

      changePassword: async (currentPassword: string, newPassword: string) => {
        try {
          await makeAuthenticatedRequest('/api/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
              current_password: currentPassword,
              new_password: newPassword,
            }),
          });

          set({ error: null });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Password change failed';
          set({
            error: { message: errorMessage },
          });
          throw error;
        }
      },

      checkAuth: async () => {
        try {
          const { accessToken } = get();
          if (!accessToken) {
            console.log('No access token available for auth check');
            set({ isAuthenticated: false });
            return;
          }

          const response = await makeAuthenticatedRequest('/api/auth/me', {
            method: 'GET',
          });

          console.log('Auth check successful, user:', response);

          set({
            user: response,
            isAuthenticated: true,
            error: null,
          });
        } catch (error) {
          console.log('Auth check failed:', error);
          // Clear authentication state
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
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

// Export the makeAuthenticatedRequest function for use in other parts of the app
export { makeAuthenticatedRequest };

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