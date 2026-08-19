import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'restaurant' | 'ngo';
  status: 'active' | 'pending' | 'suspended' | 'rejected' | 'deactivated';
  organization?: {
    id: number;
    name: string;
    description?: string;
    address: string;
    latitude?: number;
    longitude?: number;
    website?: string;
    verification_status: 'pending' | 'approved' | 'rejected';
    is_verified: boolean;
  };
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  register: (data: any) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      const response = await api.get('/users/profile');
      setUser(response.data);
    } catch (error) {
      // Clear token if profile fetch fails (invalid token)
      logoutState();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchProfile();
    } else {
      setLoading(false);
    }

    // Listener for session expiration from API client
    const handleExpiredSession = () => {
      logoutState();
      window.location.href = '/login?expired=true';
    };

    window.addEventListener('auth_session_expired', handleExpiredSession);
    return () => {
      window.removeEventListener('auth_session_expired', handleExpiredSession);
    };
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const { access_token, refresh_token } = response.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      // Fetch full profile immediately to set user details and organization status
      const profileResponse = await api.get('/users/profile');
      const loggedUser = profileResponse.data;
      setUser(loggedUser);
      setLoading(false);
      return loggedUser;
    } catch (error: any) {
      setLoading(false);
      throw error;
    }
  };

  const logoutState = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await api.post(`/auth/logout?refresh_token=${refreshToken}`);
      } catch (error) {
        console.error('Logout error on backend:', error);
      }
    }
    logoutState();
  };

  const register = async (data: any): Promise<void> => {
    try {
      await api.post('/auth/register', data);
    } catch (error) {
      throw error;
    }
  };

  const refreshProfile = async (): Promise<void> => {
    try {
      const response = await api.get('/users/profile');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to refresh profile:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
