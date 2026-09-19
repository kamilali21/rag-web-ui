"use client";

// Added by ChatGPT: one-time verification/recovery, never passwordless sign-in or registration.
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

export default function EmailLogin({ initialEmail = "", initialPassword = "", purpose = "verify_email", onComplete }: {
  initialEmail?: string; initialPassword?: string; purpose?: "verify_email" | "reset_password"; onComplete?: () => void;
}) {
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState(initialPassword);
  const [confirmation, setConfirmation] = useState("");
  const [complete, setComplete] = useState(false);
  const recovery = purpose === "reset_password";
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [retryAt, setRetryAt] = useState(0);
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const tick = () => setSeconds(Math.max(0, Math.ceil((retryAt - Date.now()) / 1000)));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [retryAt]);

  const perform = async (verify: boolean) => {
    setBusy(true); setError(""); setNotice("");
    try {
      if (verify) {
        if (recovery && password !== confirmation) { setError("Passwords do not match"); return; }
        const result = await api.post("/api/auth/verify-otp", { email, code, password, purpose }, { redirectOnUnauthorized: false });
        setNotice(result.message); setComplete(true); setPassword(""); setConfirmation(""); setCode("");
      } else {
        const result = await api.post("/api/auth/request-otp", { email, purpose }, { redirectOnUnauthorized: false });
        setSent(true); setCode(""); setNotice(result.message);
        setRetryAt(Date.now() + result.retry_after * 1000);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Please try again.");
      if (err instanceof ApiError && err.retryAfter) setRetryAt(Date.now() + err.retryAfter * 1000);
    } finally { setBusy(false); }
  };

  const inputStyle = "mt-1 block w-full px-3 py-2 rounded-md border border-gray-300 shadow-sm focus:ring-2 focus:ring-green-700";
  return <main className="auth-page"><div className="w-full max-w-md"><div className="bg-white rounded-lg shadow-md p-8 space-y-6">
    <div className="text-center"><h1 className="text-3xl font-bold text-gray-900">ResearchIQ</h1>
      <p className="mt-2 text-sm text-gray-600">{recovery ? "Set or reset your password" : "Verify your email"}</p></div>
    {complete ? <div className="space-y-4"><p role="status" className="text-green-800">{notice}</p>
      {onComplete ? <button className="primary-action w-full justify-center" onClick={onComplete}>Back to sign in</button>
        : <Link className="primary-action w-full justify-center" href="/login">Back to sign in</Link>}</div> : <form className="space-y-5" onSubmit={event => { event.preventDefault(); void perform(sent); }}>
      <div><label htmlFor="email" className="block text-sm font-medium text-gray-700">Email address</label>
        <input id="email" type="email" autoComplete="email" required maxLength={255} className={inputStyle}
          value={email} disabled={busy || sent} onChange={event => setEmail(event.target.value)} /></div>
      {sent && <div><label htmlFor="code" className="block text-sm font-medium text-gray-700">Verification code</label>
        <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}"
          maxLength={6} required autoFocus disabled={busy} className={inputStyle} value={code}
          onChange={event => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} /></div>}
      {sent && <div><label htmlFor="verification-password" className="block text-sm font-medium text-gray-700">{recovery ? "New password" : "Registration password"}</label>
        <input id="verification-password" type="password" autoComplete={recovery ? "new-password" : "current-password"}
          required minLength={recovery ? 8 : 1} maxLength={72} className={inputStyle} value={password} disabled={busy}
          onChange={event => setPassword(event.target.value)} /></div>}
      {sent && recovery && <div><label htmlFor="confirmation" className="block text-sm font-medium text-gray-700">Confirm new password</label>
        <input id="confirmation" type="password" autoComplete="new-password" required maxLength={72} className={inputStyle}
          value={confirmation} disabled={busy} onChange={event => setConfirmation(event.target.value)} /></div>}
      {notice && <p role="status" className="text-sm text-green-800 break-words">{notice}</p>}
      {error && <p role="alert" className="p-3 rounded-md bg-red-50 text-red-700 text-sm break-words">{error}</p>}
      <button type="submit" disabled={busy || (!sent && seconds > 0)} className="primary-action w-full justify-center disabled:opacity-50">
        {busy ? "Please wait..." : sent ? recovery ? "Save password" : "Verify email" : seconds > 0 ? `Try again in ${seconds}s` : "Send code"}</button>
      {sent && <div className="flex flex-wrap justify-between gap-3 text-sm">
        <button type="button" disabled={busy || seconds > 0} className="text-green-800 disabled:text-gray-500"
          onClick={() => void perform(false)}>{seconds > 0 ? `Resend in ${seconds}s` : "Resend code"}</button>
        <button type="button" disabled={busy} className="text-gray-600" onClick={() => {
          setSent(false); setCode(""); setPassword(""); setConfirmation(""); setError(""); setNotice("");
        }}>Change email</button>
      </div>}
    </form>}
    {!complete && (onComplete ? <button className="text-sm text-green-800" disabled={busy} onClick={onComplete}>Back to sign in</button>
      : <Link className="text-sm text-green-800" href="/login">Back to sign in</Link>)}
  </div></div></main>;
}
