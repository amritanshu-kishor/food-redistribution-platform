import axios from 'axios';

let rawApiUrl = import.meta.env.VITE_API_URL;
if (rawApiUrl && !rawApiUrl.endsWith('/api/v1') && !rawApiUrl.endsWith('/api/v1/')) {
  rawApiUrl = rawApiUrl.endsWith('/') ? `${rawApiUrl}api/v1` : `${rawApiUrl}/api/v1`;
}

export const API_URL =
  rawApiUrl ||
  (import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1');

export const API_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, '');

export function mediaUrl(path?: string | null): string {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${API_ORIGIN}${path}`;
}

export const api = axios.create({
  baseURL: API_URL,
});

// Attach access token to every outgoing request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Catch token expirations, perform refresh token rotation, and retry requests
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Check if error is unauthorized and we haven't already retried this request
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          // Perform POST call to rotate access and refresh tokens
          const response = await axios.post(
            `${API_URL}/auth/refresh?refresh_token=${refreshToken}`
          );
          
          if (response.status === 200) {
            const { access_token, refresh_token } = response.data;
            
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', refresh_token);
            
            // Re-auth the failed request headers and retry
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          // Refresh token expired or revoked -> clear storage and redirect
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          
          // Dispatch a custom event to notify auth context or redirect to login
          window.dispatchEvent(new Event('auth_session_expired'));
          return Promise.reject(refreshError);
        }
      }
    }
    return Promise.reject(error);
  }
);
