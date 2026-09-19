"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import EmailLogin from "./email-login";

// Added by ChatGPT: passwords sign in; OTP is reserved for verification and recovery.
export default function PasswordLogin({ emailOTP = false }: { emailOTP?: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState<string | null>(null);
  const [recovery, setRecovery] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const username = formData.get("username");
    const password = formData.get("password");

    try {
      const formUrlEncoded = new URLSearchParams();
      formUrlEncoded.append("username", username as string);
      formUrlEncoded.append("password", password as string);

      const data = await api.post("/api/auth/token", formUrlEncoded, {
        redirectOnUnauthorized: false,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      if (emailOTP) {
        localStorage.removeItem("token");
        if (data.verification_required) { setVerificationEmail(data.email); return; }
        await api.get("/api/auth/me", { redirectOnUnauthorized: false, cache: "no-store" });
      } else {
        localStorage.setItem("token", data.access_token);
      }
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  if (verificationEmail !== null || recovery) return <EmailLogin
    initialEmail={verificationEmail || ""} purpose={recovery ? "reset_password" : "verify_email"}
    onComplete={() => { setVerificationEmail(null); setRecovery(false); setError(""); }} />;

  // Added by ChatGPT: shared forest/cream authentication surface retains the login behavior.
  return (
    <main className="auth-page">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-md p-8 space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900">
              Welcome To RAG Web UI
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Please sign in to continue
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="username"
                  className="block text-sm font-medium text-gray-700"
                >
                  Email or username
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  maxLength={255}
                  required
                  disabled={loading}
                  className="mt-1 block w-full px-3 py-2 rounded-md border border-gray-300 shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your email or username"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-700"
                >
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  disabled={loading}
                  className="mt-1 block w-full px-3 py-2 rounded-md border border-gray-300 shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your password"
                />
              </div>
            </div>

            {error && (
              <div role="alert" className="p-3 rounded-md bg-red-50 text-red-700 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          {emailOTP && <div className="flex flex-wrap justify-between gap-3 text-sm text-green-800">
            <button type="button" onClick={() => setVerificationEmail("")}>Verify email</button>
            <button type="button" onClick={() => setRecovery(true)}>Set or reset password</button>
          </div>}

          <div className="text-center">
            <Link
              href="/register"
              className="text-sm font-medium text-gray-600 hover:text-gray-500"
            >
              Don't have an account? Create one now
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
