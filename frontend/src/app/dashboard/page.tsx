"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, MessageSquare, Moon, RefreshCw, Send, Sun } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { useTheme } from "@/components/theme-provider";
import { api } from "@/lib/api";
import { LibraryCollection } from "@/lib/library";

type ResearcherRequests = {
  publications: { id: number; status: string; publication_status: string | null }[];
  withdrawals: { publication_request_id: number; status: string }[];
};

// Added by ChatGPT: a quiet dashboard using real API counts and the shared reference palette.
export default function DashboardPage() {
  const { isDark, toggleTheme } = useTheme();
  const [stats, setStats] = useState<{ documents: number; publications: number; chats: number } | null>(null);
  const [error, setError] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    setStats(null);
    // Added by ChatGPT: totals include every API page rather than stopping at the default limit.
    const allPages = async <T,>(path: string): Promise<T[]> => {
      const result: T[] = [];
      for (let skip = 0; ; skip += 100) {
        const page: T[] = await api.get(`${path}?skip=${skip}&limit=100`, { signal: controller.signal });
        result.push(...page);
        if (page.length < 100) return result;
      }
    };
    Promise.all([
      allPages<LibraryCollection>("/api/knowledge-base"),
      allPages<unknown>("/api/chat"),
      api.get("/api/researcher/requests", { signal: controller.signal, cache: "no-store" }) as Promise<ResearcherRequests>,
    ]).then(([collections, chats, requests]: [LibraryCollection[], unknown[], ResearcherRequests]) => {
      if (!controller.signal.aborted) setStats({
        documents: collections.reduce((sum, collection) => sum + collection.documents.length, 0),
        publications: requests.publications.filter(request => request.status === "published" && request.publication_status === "published" &&
          !requests.withdrawals.some(withdrawal => withdrawal.publication_request_id === request.id && withdrawal.status === "approved")).length,
        chats: chats.length,
      });
    }).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [refresh]);

  return (
    <DashboardLayout>
      <div className="dashboard-heading">
        <h1>Dashboard</h1>
        <button type="button" className="primary-action premium-action theme-toggle" role="switch" aria-label="Dark mode" aria-checked={isDark} onClick={toggleTheme}>
          {isDark ? <Sun size={20} aria-hidden="true" /> : <Moon size={20} aria-hidden="true" />}
          <span>Dark mode</span>
          <span className="theme-switch-track" aria-hidden="true"><span /></span>
        </button>
      </div>
      {error ? <div className="library-empty" role="alert"><p>Unable to load your dashboard.</p><button className="primary-action" onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={18} /> Retry</button></div> :
        <div className="dashboard-stats" aria-busy={!stats}>
          {[{ label: "Documents", value: stats?.documents }, { label: "Publications", value: stats?.publications }, { label: "Conversations", value: stats?.chats }].map(({ label, value }) =>
            <div key={label} className="dashboard-stat"><strong>{value ?? "..."}</strong><span>{label}</span></div>)}
        </div>}
      <h2 className="text-xl font-semibold mb-4">Workspace</h2>
      <div className="dashboard-links">
        <Link href="/dashboard/knowledge"><BookOpen className="text-primary" size={24} /> Library</Link>
        <Link href="/dashboard/chat/new"><MessageSquare className="text-primary" size={24} /> New conversation</Link>
        <Link href="/dashboard/knowledge?requestPublication=1"><Send className="text-primary" size={24} /> Request publication</Link>
      </div>
    </DashboardLayout>
  );
}
