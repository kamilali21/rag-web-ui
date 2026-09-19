"use client";

// Added by ChatGPT: network failures never downgrade email sign-in to passwords.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PasswordLogin from "@/components/auth/password-login";
import EmailLogin from "@/components/auth/email-login";

export default function LoginPage() {
  const [emailOTP, setEmailOTP] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const load = async () => {
    setError("");
    try {
      const methods = await api.get("/api/auth/methods", { redirectOnUnauthorized: false, cache: "no-store" });
      if (typeof methods.email_otp !== "boolean") throw new Error("Invalid sign-in configuration");
      setEmailOTP(methods.email_otp);
    } catch { setError("Sign-in is temporarily unavailable."); }
  };
  useEffect(() => { void load(); }, []);
  if (emailOTP !== null) return emailOTP ? <EmailLogin /> : <PasswordLogin />;
  return <main className="auth-page"><div className="w-full max-w-md rounded-lg bg-white p-8 space-y-4 text-center">
    <p role={error ? "alert" : "status"}>{error || "Loading sign-in..."}</p>
    {error && <button className="primary-action" onClick={load}>Retry</button>}
  </div></main>;
}
