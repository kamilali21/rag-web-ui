"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Book, BookOpen, Home, LogOut, Menu, MessageSquare, Sparkles, User } from "lucide-react";
import Breadcrumb from "@/components/ui/breadcrumb";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

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

  useEffect(() => {
    if (!localStorage.getItem("token")) router.replace("/login");
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
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
      <button className="app-nav-link app-signout" onClick={handleLogout}>
        <LogOut size={24} strokeWidth={1.6} aria-hidden="true" /> Sign out
      </button>
    </>
  );

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
