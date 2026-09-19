// Added by ChatGPT: OTP interactions and rollout errors without real email or network access.
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import EmailLogin from '../email-login';
import LoginPage from '@/app/login/page';
import { api, ApiError } from '@/lib/api';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, push: jest.fn() }) }));
jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api');
  return { ...actual, api: { get: jest.fn(), post: jest.fn() } };
});
const post = api.post as jest.Mock;
const get = api.get as jest.Mock;

beforeEach(() => { jest.clearAllMocks(); localStorage.clear(); });

async function sendCode() {
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'alice@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send code' }));
  await screen.findByLabelText('Verification code');
}

test('email/code sign-in checks the session and never stores a bearer token', async () => {
  post.mockResolvedValueOnce({ message: 'Code sent.', retry_after: 60 }).mockResolvedValueOnce({ id: 1 });
  get.mockResolvedValue({ id: 1, roles: ['researcher'] });
  localStorage.setItem('token', 'legacy-token');
  render(<EmailLogin />);
  await sendCode();
  expect(screen.getByRole('button', { name: /Resend in/ })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.click(screen.getByRole('button', { name: 'Verify and sign in' }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith('/dashboard'));
  expect(post).toHaveBeenLastCalledWith('/api/auth/verify-otp', { email: 'alice@example.com', code: '123456' }, { redirectOnUnauthorized: false });
  expect(get).toHaveBeenCalledWith('/api/auth/me', expect.any(Object));
  expect(localStorage.getItem('token')).toBeNull();
});

test('invalid code remains on the form and changing email clears the code', async () => {
  post.mockResolvedValueOnce({ message: 'Code sent.', retry_after: 0 }).mockRejectedValueOnce(new ApiError(400, 'Invalid or expired code'));
  render(<EmailLogin />);
  await sendCode();
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.click(screen.getByRole('button', { name: 'Verify and sign in' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid or expired code');
  expect(replace).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Change email' }));
  expect(screen.queryByLabelText('Verification code')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Email address')).toBeEnabled();
});

test('resend uses the same endpoint and resets the cooldown', async () => {
  post.mockResolvedValueOnce({ message: 'Code sent.', retry_after: 0 }).mockResolvedValueOnce({ message: 'Code sent again.', retry_after: 60 });
  render(<EmailLogin />);
  await sendCode();
  fireEvent.click(screen.getByRole('button', { name: 'Resend code' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Code sent again.'));
  expect(post).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('button', { name: /Resend in/ })).toBeDisabled();
});

test('server rate limit disables sending until its Retry-After', async () => {
  post.mockRejectedValue(new ApiError(429, 'Please wait', 60));
  render(<EmailLogin />);
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'alice@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send code' }));
  await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: /Try again in/ })).toBeDisabled();
});

test('missing cookie acceptance cannot navigate into the dashboard', async () => {
  post.mockResolvedValue({ message: 'Code sent.', retry_after: 0 });
  get.mockRejectedValue(new ApiError(401, 'Session unavailable'));
  render(<EmailLogin />);
  await sendCode();
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.click(screen.getByRole('button', { name: 'Verify and sign in' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Session unavailable');
  expect(replace).not.toHaveBeenCalled();
});

test('method-discovery failure does not expose password fallback', async () => {
  get.mockRejectedValue(new ApiError(503, 'Unavailable'));
  render(<LoginPage />);
  await screen.findByRole('alert');
  expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  get.mockResolvedValue({ email_otp: true });
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await screen.findByLabelText('Email address');
});

test('malformed method response cannot enable password fallback', async () => {
  get.mockResolvedValue({});
  render(<LoginPage />);
  await screen.findByRole('alert');
  expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
});

test('explicitly disabled OTP keeps the existing password form', async () => {
  get.mockResolvedValue({ email_otp: false });
  render(<LoginPage />);
  await screen.findByLabelText('Password');
  expect(screen.queryByLabelText('Email address')).not.toBeInTheDocument();
});
