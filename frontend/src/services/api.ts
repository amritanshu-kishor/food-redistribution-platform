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

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback;
  const detail: unknown = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) =>
      item && typeof item.msg === 'string' ? [item.msg] : []
    );
    if (messages.length) return messages.join('. ');
  }
  return fallback;
}

let refreshPromise: Promise<string> | null = null;

function refreshAccessToken(refreshToken: string): Promise<string> {
  // All requests in this tab share a single refresh-token rotation.
  if (!refreshPromise) {
    refreshPromise = axios.post(`${API_URL.replace(/\/$/, '')}/auth/refresh`, {
      refresh_token: refreshToken,
    }).then(({ data }) => {
      if (localStorage.getItem('refresh_token') !== refreshToken) {
        throw new Error('Session changed while refreshing');
      }
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return data.access_token as string;
    }).catch((error) => {
      if ([401, 403].includes(error.response?.status) && localStorage.getItem('refresh_token') === refreshToken) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.dispatchEvent(new Event('auth_session_expired'));
      }
      throw error;
    }).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

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
    const requestUrl = originalRequest?.url || '';
    
    // Check if error is unauthorized and we haven't already retried this request
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !requestUrl.includes('/auth/login') &&
      !requestUrl.includes('/auth/refresh')
    ) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          const currentToken = localStorage.getItem('access_token');
          // A late 401 may belong to the old token after rotation has finished.
          const accessToken = currentToken && originalRequest.headers.Authorization !== `Bearer ${currentToken}`
            ? currentToken
            : await refreshAccessToken(refreshToken);
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      }
    }
    return Promise.reject(error);
  }
);
