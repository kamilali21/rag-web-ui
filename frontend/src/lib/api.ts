interface FetchOptions extends Omit<RequestInit, 'body' | 'headers'> {
  data?: any;
  headers?: Record<string, string>;
  redirectOnUnauthorized?: boolean;
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public retryAfter = 0) {
    super(message);
    this.name = 'ApiError';
  }
}

// Added by ChatGPT: only the CSRF cookie is readable; the session secret stays HttpOnly.
export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const cookieName = window.location.protocol === 'https:' ? '__Host-researchiq_csrf' : 'researchiq_local_csrf';
  const csrf = document.cookie.split('; ').find(value => value.startsWith(`${cookieName}=`))?.split('=')[1];
  if (csrf) return { 'X-CSRF-Token': decodeURIComponent(csrf) };
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Added by ChatGPT: streaming chat needs the same current credentials as JSON requests.
export const authenticatedFetch: typeof fetch = (input, init) => {
  const headers = new Headers(init?.headers);
  Object.entries(getAuthHeaders()).forEach(([key, value]) => headers.set(key, value));
  return fetch(input, { ...init, cache: 'no-store', credentials: 'same-origin', headers });
};

export async function fetchApi(fullUrl: string, options: FetchOptions = {}) {
  const { data, headers: customHeaders = {}, redirectOnUnauthorized = true, ...restOptions } = options;

  const headers: Record<string, string> = {
    ...getAuthHeaders(),
    ...customHeaders,
  };

  // If no content type is specified and we have data, default to JSON
  if (!headers['Content-Type'] && data && !(data instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const config: RequestInit = {
    ...restOptions,
    cache: 'no-store',
    credentials: 'same-origin',
    headers,
  };

  // Handle body based on Content-Type
  if (data) {
    if (data instanceof FormData) {
      config.body = data;
    } else if (headers['Content-Type'] === 'application/json') {
      config.body = JSON.stringify(data);
    } else if (headers['Content-Type'] === 'application/x-www-form-urlencoded') {
      config.body = typeof data === 'string' ? data : new URLSearchParams(data).toString();
    } else {
      config.body = data;
    }
  }

  try {
    const response = await fetch(fullUrl, config);

    if (response.status === 401) {
      if (redirectOnUnauthorized && typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      throw new ApiError(401, 'Unauthorized - Please log in again');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        typeof (errorData.message || errorData.detail) === 'string'
          ? errorData.message || errorData.detail : 'Please check your input and try again',
        Number(response.headers.get('Retry-After')) || 0
      );
    }

    return response.status === 204 ? undefined : await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(500, 'Network error or server is unreachable');
  }
}

// Helper methods for common HTTP methods
export const api = {
  get: (url: string, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'GET' }),

  post: (url: string, data?: any, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'POST', data }),

  put: (url: string, data?: any, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'PUT', data }),

  delete: (url: string, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'DELETE' }),

  patch: (url: string, data?: any, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'PATCH', data }),
};
