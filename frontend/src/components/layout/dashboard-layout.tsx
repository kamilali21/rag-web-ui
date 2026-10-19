"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Book, BookOpen, CircleUser, Home, Menu, MessageSquare, Sparkles } from "lucide-react";
import Breadcrumb from "@/components/ui/breadcrumb";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api";
import { useTheme } from "@/components/theme-provider";
import SignOutButton from "@/components/layout/sign-out-button";

type SidebarProfile = { full_name?: string | null; photo_url?: string | null } | null;
type CurrentIdentity = { username?: string | null };

// Added by ChatGPT: shared navigation for the reference sidebar and accessible mobile drawer.
const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Library", href: "/dashboard/knowledge", icon: Book },
  { name: "Chat", href: "/dashboard/chat", icon: MessageSquare },
  // Added by ChatGPT: frontend research workspace in desktop and mobile navigation.
  { name: "Insights", href: "/dashboard/insights", icon: Sparkles },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [authError, setAuthError] = useState("");
  const [identity, setIdentity] = useState<CurrentIdentity | null>(null);
  const [profile, setProfile] = useState<SidebarProfile>(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const { isDark } = useTheme();

  // Added by ChatGPT: validate the server session before rendering protected content.
  useEffect(() => {
    let active = true;
    api.get("/api/auth/me", { redirectOnUnauthorized: false, cache: "no-store" }).then((current: CurrentIdentity) => {
      if (!active) return;
      setIdentity(current);
      setAuthenticated(true);
      void api.get("/api/researcher/profile", { cache: "no-store" }).then(currentProfile => {
        if (active) setProfile(currentProfile);
      }).catch(() => {
        // Authentication remains valid when an account has not created a researcher profile yet.
      });
    }).catch(error => {
      if (!active) return;
      if (error instanceof ApiError && error.status === 401) router.replace("/login");
      else setAuthError("Your session could not be checked. Please retry.");
    });
    return () => { active = false; };
  }, [router]);

  useEffect(() => {
    if (!accountMenuOpen) return;
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!(event.target instanceof Element) || !event.target.closest(".app-account-menu-anchor")) setAccountMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccountMenuOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accountMenuOpen]);

  // Added by ChatGPT: retain authentication and route behavior in both navigation layouts.
  const sidebar = (
    <>
      <Link href="/dashboard" className="app-brand" onClick={() => setMenuOpen(false)}>
        <span className="app-brand-mark" aria-hidden="true"><BookOpen size={38} strokeWidth={1} /></span>
        <span>rAGRI search</span>
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
      <div className="app-sidebar-bottom">
        <div className="app-account-menu-anchor">
          <button type="button" aria-label="Open account menu" aria-expanded={accountMenuOpen}
            className={`app-profile-card${pathname.startsWith("/dashboard/profile") ? " is-active" : ""}`}
            onClick={() => setAccountMenuOpen(open => !open)}>
          <span className="app-profile-avatar" aria-hidden="true">
            {profile?.photo_url ? <img src={profile.photo_url} alt="" /> : <CircleUser size={24} strokeWidth={1.6} />}
          </span>
          <span className="app-profile-copy"><strong>{profile?.full_name || identity?.username || "Profile"}</strong>
            <small>{identity?.username ? `@${identity.username}` : "Manage your profile"}</small></span>
          </button>
          {accountMenuOpen && <div className="app-account-menu" role="group" aria-label="Account menu">
            <div className="app-account-menu-identity">
              <span className="app-profile-avatar" aria-hidden="true">
                {profile?.photo_url ? <img src={profile.photo_url} alt="" /> : <CircleUser size={24} strokeWidth={1.6} />}
              </span>
              <span className="app-profile-copy"><strong>{profile?.full_name || identity?.username || "Profile"}</strong>
                <small>{identity?.username ? `@${identity.username}` : "Researcher account"}</small></span>
            </div>
            <Link href="/dashboard/profile" className="app-account-menu-profile" onClick={() => {
              setAccountMenuOpen(false);
              setMenuOpen(false);
            }}>View profile</Link>
            <SignOutButton className="account-menu-signout" />
          </div>}
        </div>
      </div>
    </>
  );

  if (!authenticated) return <main className="auth-page"><div className="w-full max-w-md rounded-lg bg-white p-8 space-y-4 text-center">
    <p role={authError ? "alert" : "status"}>{authError || "Checking session..."}</p>
    {authError && <button className="primary-action" onClick={() => window.location.reload()}>Retry</button>}
  </div></main>;

  return (
    <div className={`app-shell${isDark ? " dark" : ""}`}>
      {/* Added by ChatGPT: Radix manages focus trapping, Escape, and return focus on mobile. */}
      <a href="#main-content" className="skip-link">Skip to content</a>
      <aside className="app-sidebar">{sidebar}</aside>
      <header className="app-mobile-header">
        <span>rAGRI search</span>
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
  sidebarNav: [...navigation.map(({ name, href }) => ({
    title: name, href, icon: name === "Library" ? "database" : name === "Chat" ? "messageSquare" : name === "Insights" ? "sparkles" : name === "Dashboard" ? "home" : "key",
  })), { title: "Profile", href: "/dashboard/profile", icon: "user" }],
};
