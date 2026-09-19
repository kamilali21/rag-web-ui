// Added by ChatGPT: request credentials, CSRF precedence and safe login error handling.
import { api, getAuthHeaders, authenticatedFetch } from '../api';

beforeEach(() => {
  localStorage.clear();
  document.cookie = 'researchiq_local_csrf=; Max-Age=0; Path=/';
  global.fetch = jest.fn();
});

test('CSRF token takes precedence over stale legacy bearer token', () => {
  localStorage.setItem('token', 'old');
  expect(getAuthHeaders()).toEqual({ Authorization: 'Bearer old' });
  document.cookie = 'researchiq_local_csrf=bound-csrf; Path=/';
  expect(getAuthHeaders()).toEqual({ 'X-CSRF-Token': 'bound-csrf' });
});

test('JSON mutations carry same-origin cookies and CSRF', async () => {
  document.cookie = 'researchiq_local_csrf=bound-csrf; Path=/';
  (fetch as jest.Mock).mockResolvedValue({ ok: true, status: 200, json: async () => ({ id: 1 }) });
  await api.post('/api/chat/', { title: 'Research' });
  expect(fetch).toHaveBeenCalledWith('/api/chat/', expect.objectContaining({
    credentials: 'same-origin', method: 'POST', headers: {
      'X-CSRF-Token': 'bound-csrf', 'Content-Type': 'application/json',
    },
  }));
});

test('rate limit Retry-After reaches the form', async () => {
  (fetch as jest.Mock).mockResolvedValue({ ok: false, status: 429,
    headers: { get: () => '60' }, json: async () => ({ detail: 'Please wait' }) });
  await expect(api.post('/api/auth/request-otp', {})).rejects.toMatchObject({ status: 429, retryAfter: 60 });
});

test('login 401 stays local instead of redirecting', async () => {
  (fetch as jest.Mock).mockResolvedValue({ ok: false, status: 401 });
  localStorage.setItem('token', 'unchanged');
  await expect(api.get('/api/auth/me', { redirectOnUnauthorized: false })).rejects.toMatchObject({ status: 401 });
  expect(localStorage.getItem('token')).toBe('unchanged');
});

test('chat streams read rotated CSRF credentials at request time', async () => {
  (fetch as jest.Mock).mockResolvedValue({ ok: true });
  document.cookie = 'researchiq_local_csrf=first; Path=/';
  await authenticatedFetch('/api/chat/1/messages', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  let request = (fetch as jest.Mock).mock.calls[0][1];
  expect(request.headers.get('X-CSRF-Token')).toBe('first');
  expect(request.headers.get('Content-Type')).toBe('application/json');
  expect(request.credentials).toBe('same-origin');
  document.cookie = 'researchiq_local_csrf=rotated; Path=/';
  await authenticatedFetch('/api/chat/1/messages', { method: 'POST' });
  request = (fetch as jest.Mock).mock.calls[1][1];
  expect(request.headers.get('X-CSRF-Token')).toBe('rotated');
  expect(request.headers.has('Authorization')).toBe(false);
});
