// Added by ChatGPT: OTP interactions and rollout errors without real email or network access.
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import EmailLogin from '../email-login';
import LoginPage from '@/app/login/page';
import PasswordLogin from '../password-login';
import RegisterPage from '@/app/register/page';
import { api, ApiError } from '@/lib/api';

const replace = jest.fn();
const push = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, push }) }));
jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api');
  return { ...actual, api: { get: jest.fn(), post: jest.fn() } };
});
const post = api.post as jest.Mock;
const get = api.get as jest.Mock;

beforeEach(() => { jest.clearAllMocks(); localStorage.clear(); });

// Added by ChatGPT: only the redundant sign-in shortcut is removed, not verification enforcement.
test('sign-in exposes Reset password without a manual Verify email shortcut', () => {
  render(<PasswordLogin emailOTP />);
  expect(screen.queryByRole('button', { name: 'Verify email' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Reset password' }));
  expect(screen.getByText('Reset your password')).toBeInTheDocument();
});

async function sendCode() {
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'alice@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send code' }));
  await screen.findByLabelText('Verification code');
}

test('email verification returns to password login without creating a session', async () => {
  post.mockResolvedValueOnce({ message: 'Code sent.', retry_after: 60 }).mockResolvedValueOnce({ message: 'Email verified. Sign in with your password.' });
  render(<EmailLogin />);
  await sendCode();
  expect(screen.getByRole('button', { name: /Resend in/ })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.change(screen.getByLabelText('Registration password'), { target: { value: 'Password123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Verify email' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Email verified.'));
  expect(post).toHaveBeenLastCalledWith('/api/auth/verify-otp', { email: 'alice@example.com', code: '123456', password: 'Password123', purpose: 'verify_email' }, { redirectOnUnauthorized: false });
  expect(get).not.toHaveBeenCalled();
  expect(replace).not.toHaveBeenCalled();
  expect(localStorage.getItem('token')).toBeNull();
});

test('invalid code remains on the form and changing email clears the code', async () => {
  post.mockResolvedValueOnce({ message: 'Code sent.', retry_after: 0 }).mockRejectedValueOnce(new ApiError(400, 'Invalid or expired code'));
  render(<EmailLogin />);
  await sendCode();
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.change(screen.getByLabelText('Registration password'), { target: { value: 'Password123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Verify email' }));
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
  expect(await screen.findByRole('button', { name: /Resend in/ })).toBeDisabled();
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
  post.mockResolvedValue({ authenticated: true });
  get.mockRejectedValue(new ApiError(401, 'Session unavailable'));
  render(<PasswordLogin emailOTP />);
  fireEvent.change(screen.getByLabelText('Email or username'), { target: { value: 'alice' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByText('Session unavailable')).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
});

test('method-discovery failure does not expose password fallback', async () => {
  get.mockRejectedValue(new ApiError(503, 'Unavailable'));
  render(<LoginPage />);
  await screen.findByRole('alert');
  expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  get.mockResolvedValue({ email_otp: true });
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await screen.findByLabelText('Email or username');
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

// Added by ChatGPT: the restored registration, password login and recovery paths.
test('enabled flow signs in with password, checks cookie session and stores no JWT', async () => {
  post.mockResolvedValue({ authenticated: true });
  get.mockResolvedValue({ id: 1 });
  localStorage.setItem('token', 'stale');
  render(<PasswordLogin emailOTP />);
  fireEvent.change(screen.getByLabelText('Email or username'), { target: { value: 'alice@example.com' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'));
  expect(post).toHaveBeenCalledTimes(1);
  expect(post.mock.calls[0][0]).toBe('/api/auth/token');
  expect(localStorage.getItem('token')).toBeNull();
});

test('unverified password login opens verification instead of dashboard', async () => {
  post.mockResolvedValue({ verification_required: true, email: 'alice@example.com' });
  render(<PasswordLogin emailOTP />);
  fireEvent.change(screen.getByLabelText('Email or username'), { target: { value: 'alice' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByLabelText('Email address')).toHaveValue('alice@example.com');
  expect(push).not.toHaveBeenCalled();
});

test('registration remains available with OTP enabled and advances to verification', async () => {
  get.mockResolvedValue({ email_otp: true });
  post.mockResolvedValue({ id: 1 });
  render(<RegisterPage />);
  await screen.findByLabelText('Username');
  for (const [label, value] of [['Username', 'alice'], ['Email', 'alice@example.com'], ['Password', 'Password123'], ['Confirm Password', 'Password123']]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole('button', { name: 'Create Account' }));
  expect(await screen.findByLabelText('Email address')).toHaveValue('alice@example.com');
  expect(post).toHaveBeenCalledWith('/api/auth/register', { username: 'alice', email: 'alice@example.com', password: 'Password123' });
  expect(push).not.toHaveBeenCalled();
});

test('password setup requires matching passwords and sends a purpose-bound code', async () => {
  post.mockResolvedValue({ message: 'Code sent.', retry_after: 0 });
  render(<EmailLogin purpose="reset_password" />);
  await sendCode();
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } });
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'Password123' } });
  fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'Different123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save password' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match');
  expect(post).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'Password123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save password' }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
  expect(post.mock.calls[1][1]).toEqual({ email: 'alice@example.com', code: '123456', password: 'Password123', purpose: 'reset_password' });
});
