"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { api } from "@/lib/api";

export default function SignOutButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const signOut = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post("/api/auth/logout");
      localStorage.removeItem("token");
      router.replace("/login");
    } catch {
      setError("Sign out failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return <div className="signout-action">
    <button type="button" className={`signout-button ${className}`} onClick={signOut} disabled={busy}>
      <LogOut size={20} strokeWidth={1.7} aria-hidden="true" />
      <span>{busy ? "Signing out..." : "Sign out"}</span>
    </button>
    {error && <p role="alert" className="signout-error">{error}</p>}
  </div>;
}
