"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Book, BookOpen, Home, LogOut, Menu, MessageSquare, Sparkles, User } from "lucide-react";
import Breadcrumb from "@/components/ui/breadcrumb";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api";

// Added by ChatGPT: shared navigation for the reference sidebar and accessible mobile drawer.
const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Library", href: "/dashboard/knowledge", icon: Book },
  { name: "Chat", href: "/dashboard/chat", icon: MessageSquare },
  // Added by ChatGPT: frontend research workspace in desktop and mobile navigation.
  { name: "Insights", href: "/dashboard/insights", icon: Sparkles },
  { name: "API Keys", href: "/dashboard/api-keys", icon: User },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [authError, setAuthError] = useState("");
  const [signingOut, setSigningOut] = useState(false);

  // Added by ChatGPT: validate the server session before rendering protected content.
  useEffect(() => {
    let active = true;
    api.get("/api/auth/me", { redirectOnUnauthorized: false, cache: "no-store" }).then(() => {
      if (active) setAuthenticated(true);
    }).catch(error => {
      if (!active) return;
      if (error instanceof ApiError && error.status === 401) router.replace("/login");
      else setAuthError("Your session could not be checked. Please retry.");
    });
    return () => { active = false; };
  }, [router]);

  const handleLogout = async () => {
    setSigningOut(true); setAuthError("");
    try {
      await api.post("/api/auth/logout");
      localStorage.removeItem("token");
      router.replace("/login");
    } catch { setAuthError("Sign out failed. Please try again."); }
    finally { setSigningOut(false); }
  };

  // Added by ChatGPT: retain authentication and route behavior in both navigation layouts.
  const sidebar = (
    <>
      <Link href="/dashboard" className="app-brand" onClick={() => setMenuOpen(false)}>
        {/* Added by ChatGPT: outlined RAG wordmark follows the supplied reference. */}
        <span className="app-brand-mark" aria-hidden="true"><BookOpen size={38} strokeWidth={1} /><span>RAG</span></span>
        <span>RAG Web UI</span>
      </Link>
      <nav aria-label="Main navigation" className="app-navigation">
        {navigation.map(({ name, href, icon: Icon }) => {
          const active = href === "/dashboard" ? pathname === href :
            pathname.startsWith(href) || (name === "Library" && pathname.startsWith("/dashboard/test-retrieval"));
          return (
            <Link key={href} href={href} aria-current={active ? "page" : undefined}
              className={`app-nav-link${active ? " is-active" : ""}`} onClick={() => setMenuOpen(false)}>
              <Icon size={24} strokeWidth={1.6} aria-hidden="true" />
              <span>{name}</span>
            </Link>
          );
        })}
      </nav>
      <button className="app-nav-link app-signout" onClick={handleLogout} disabled={signingOut}>
        <LogOut size={24} strokeWidth={1.6} aria-hidden="true" /> Sign out
      </button>
    </>
  );

  if (!authenticated) return <main className="auth-page"><div className="w-full max-w-md rounded-lg bg-white p-8 space-y-4 text-center">
    <p role={authError ? "alert" : "status"}>{authError || "Checking session..."}</p>
    {authError && <button className="primary-action" onClick={() => window.location.reload()}>Retry</button>}
  </div></main>;

  return (
    <div className="app-shell">
      {/* Added by ChatGPT: Radix manages focus trapping, Escape, and return focus on mobile. */}
      <a href="#main-content" className="skip-link">Skip to content</a>
      <aside className="app-sidebar">{sidebar}</aside>
      <header className="app-mobile-header">
        <span>RAG Web UI</span>
        <Dialog open={menuOpen} onOpenChange={setMenuOpen}>
          <DialogTrigger asChild>
            <button className="icon-button" aria-label="Open navigation" title="Open navigation"><Menu /></button>
          </DialogTrigger>
          <DialogContent className="mobile-navigation" aria-describedby={undefined}>
            <DialogTitle className="sr-only">Navigation</DialogTitle>
            {sidebar}
          </DialogContent>
        </Dialog>
      </header>
      <main id="main-content" className="app-main" tabIndex={-1}>
        <Breadcrumb />
        {authError && <p role="alert" className="text-red-700">{authError}</p>}
        {children}
      </main>
    </div>
  );
}

// Added by ChatGPT: preserve the exported configuration for existing consumers.
export const dashboardConfig = {
  mainNav: [],
  sidebarNav: navigation.map(({ name, href }) => ({
    title: name, href, icon: name === "Library" ? "database" : name === "Chat" ? "messageSquare" : name === "Insights" ? "sparkles" : name === "Dashboard" ? "home" : "key",
  })),
};
