"use client";

// Added by ChatGPT: email-only login with a resend timer and no browser-stored bearer secret.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export default function EmailLogin() {
  const router = useRouter();
  const [email, setEmail] = useState("");
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
        await api.post("/api/auth/verify-otp", { email, code }, { redirectOnUnauthorized: false });
        localStorage.removeItem("token");
        await api.get("/api/auth/me", { redirectOnUnauthorized: false, cache: "no-store" });
        router.replace("/dashboard");
      } else {
        const result = await api.post("/api/auth/request-otp", { email }, { redirectOnUnauthorized: false });
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
      <p className="mt-2 text-sm text-gray-600">{sent ? "Verify your email" : "Sign in or create an account"}</p></div>
    <form className="space-y-5" onSubmit={event => { event.preventDefault(); void perform(sent); }}>
      <div><label htmlFor="email" className="block text-sm font-medium text-gray-700">Email address</label>
        <input id="email" type="email" autoComplete="email" required maxLength={255} className={inputStyle}
          value={email} disabled={busy || sent} onChange={event => setEmail(event.target.value)} /></div>
      {sent && <div><label htmlFor="code" className="block text-sm font-medium text-gray-700">Verification code</label>
        <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}"
          maxLength={6} required autoFocus disabled={busy} className={inputStyle} value={code}
          onChange={event => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} /></div>}
      {notice && <p role="status" className="text-sm text-green-800 break-words">{notice}</p>}
      {error && <p role="alert" className="p-3 rounded-md bg-red-50 text-red-700 text-sm break-words">{error}</p>}
      <button type="submit" disabled={busy || (!sent && seconds > 0)} className="primary-action w-full justify-center disabled:opacity-50">
        {busy ? "Please wait..." : sent ? "Verify and sign in" : seconds > 0 ? `Try again in ${seconds}s` : "Send code"}</button>
      {sent && <div className="flex flex-wrap justify-between gap-3 text-sm">
        <button type="button" disabled={busy || seconds > 0} className="text-green-800 disabled:text-gray-500"
          onClick={() => void perform(false)}>{seconds > 0 ? `Resend in ${seconds}s` : "Resend code"}</button>
        <button type="button" disabled={busy} className="text-gray-600" onClick={() => {
          setSent(false); setCode(""); setError(""); setNotice("");
        }}>Change email</button>
      </div>}
    </form>
  </div></div></main>;
}
