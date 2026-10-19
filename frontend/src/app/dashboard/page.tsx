"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, BookOpen, ClipboardList, Globe, MessageSquare, Moon, RefreshCw, Send, Sun } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { PublicationRequestDialog } from "@/components/knowledge-base/researcher-publication-dialogs";
import { PublicationRequestsAdmin } from "@/components/knowledge-base/publication-requests-admin";
import { useTheme } from "@/components/theme-provider";
import { api, ApiError } from "@/lib/api";
import { documentDate } from "@/lib/library";

type Publication = { id: number; status: string; publication_status: string | null;
  metadata?: { title?: string }; source_file_name?: string | null; created_at: string };
type Withdrawal = { id: number; publication_request_id: number; status: string; title?: string; created_at: string };
type ResearcherRequests = { publications: Publication[]; withdrawals: Withdrawal[] };
type DashboardData = { documents: number; requests: ResearcherRequests; admin: boolean; pendingReview: number | null };

export default function DashboardPage() {
  const { isDark, toggleTheme } = useTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [publicationOpen, setPublicationOpen] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [notice, setNotice] = useState("");
  const forbidden = useCallback(() => {
    setReviewing(false);
    setData(value => value && { ...value, admin: false, pendingReview: null });
    setNotice("Your publication review permission is no longer available.");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    void (async () => {
      try {
        const [catalog, requests, user]: [{ total: number }, ResearcherRequests, { roles?: string[] }] = await Promise.all([
          api.get("/api/knowledge-base/catalog?skip=0&limit=1", { signal: controller.signal, cache: "no-store" }),
          api.get("/api/researcher/requests", { signal: controller.signal, cache: "no-store" }),
          api.get("/api/auth/me", { signal: controller.signal, cache: "no-store" }),
        ]);
        let admin = user.roles?.includes("admin") === true;
        let pendingReview: number | null = null;
        if (admin) {
          try {
            const result: { count: number } = await api.get("/api/researcher/admin/count", { signal: controller.signal, cache: "no-store" });
            pendingReview = result.count;
          } catch (failure) {
            if (failure instanceof ApiError && failure.status === 403) admin = false;
            // A missing count must never be presented as an empty review queue.
          }
        }
        if (!controller.signal.aborted) setData({ documents: catalog.total, requests, admin, pendingReview });
      } catch { if (!controller.signal.aborted) setError(true); }
    })();
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    if (!data || reviewing || publicationOpen || !(data.admin || data.requests.publications.some(item => ["pending", "processing"].includes(item.status)))) return;
    const timer = setTimeout(() => setRefresh(value => value + 1), 30000);
    return () => clearTimeout(timer);
  }, [data, reviewing, publicationOpen]);

  const published = data?.requests.publications.filter(item => item.status === "published" && item.publication_status === "published" &&
    !data.requests.withdrawals.some(withdrawal => withdrawal.publication_request_id === item.id && withdrawal.status === "approved")).length;
  const pending = data?.admin ? data.pendingReview : data &&
    data.requests.publications.filter(item => item.status === "pending").length + data.requests.withdrawals.filter(item => item.status === "pending").length;
  const activity = data ? [
    ...data.requests.publications.map(item => ({ key: `publication-${item.id}`, title: item.metadata?.title || item.source_file_name || `Publication request #${item.id}`,
      kind: "Publication request", date: item.created_at, status: item.status === "published" && item.publication_status !== "published" ? "Archived" : item.status })),
    ...data.requests.withdrawals.map(item => ({ key: `withdrawal-${item.id}`, title: item.title || `Withdrawal request #${item.id}`,
      kind: "Withdrawal request", date: item.created_at, status: item.status })),
  ].sort((a, b) => documentDate(b.date).getTime() - documentDate(a.date).getTime()).slice(0, 5) : [];

  return <DashboardLayout>
    {reviewing && data?.admin ? <PublicationRequestsAdmin backLabel="Dashboard" onBack={() => { setReviewing(false); setRefresh(value => value + 1); }} onForbidden={forbidden} /> : <>
      <div className="dashboard-heading">
        <div><h1>Your dashboard</h1><p className="dashboard-subtitle">Keep your research moving.</p></div>
        <button type="button" className="primary-action premium-action theme-toggle" role="switch" aria-label="Dark mode" aria-checked={isDark} onClick={toggleTheme}>
          {isDark ? <Sun size={20} aria-hidden="true" /> : <Moon size={20} aria-hidden="true" />}
          <span>Dark mode</span><span className="theme-switch-track" aria-hidden="true"><span /></span>
        </button>
      </div>
      {notice && <p role="alert">{notice}</p>}
      {error ? <div className="library-empty" role="alert"><p>Unable to load your dashboard.</p><button className="primary-action" onClick={() => setRefresh(value => value + 1)}><RefreshCw size={18} /> Retry</button></div> : <>
        <div className="dashboard-stats" aria-label="Research overview" aria-busy={!data}>
          <Link href="/dashboard/knowledge" className="dashboard-stat" aria-label={`My papers: ${data?.documents ?? "loading"}`}>
            <span className="dashboard-stat-top"><BookOpen size={22} aria-hidden="true" /><strong>{data?.documents ?? "…"}</strong></span>
            <span className="dashboard-stat-label">My papers</span><span className="dashboard-stat-note">Private Library</span>
          </Link>
          <button type="button" className="dashboard-stat" disabled={!data} onClick={() => data?.admin ? setReviewing(true) : setPublicationOpen(true)} aria-label={`Publication requests: ${pending ?? "unavailable"} awaiting review`}>
            <span className="dashboard-stat-top"><ClipboardList size={22} aria-hidden="true" /><strong>{pending ?? (data ? "—" : "…")}</strong></span>
            <span className="dashboard-stat-label">Publication requests</span><span className="dashboard-stat-note">{data?.admin ? "Awaiting your review" : "Awaiting review · submit a paper"} <ArrowUpRight size={14} aria-hidden="true" /></span>
          </button>
          <Link href="/dashboard/profile#publication-activity" className="dashboard-stat dashboard-stat-published" aria-label={`Published: ${published ?? "loading"}`}>
            <span className="dashboard-stat-top"><Globe size={22} aria-hidden="true" /><strong>{published ?? "…"}</strong></span>
            <span className="dashboard-stat-label">Published</span><span className="dashboard-stat-note">Your public papers</span>
          </Link>
        </div>
        <section className="dashboard-activity" aria-labelledby="publication-activity-heading">
          <div className="dashboard-section-heading"><h2 id="publication-activity-heading">Publication activity</h2><Link href="/dashboard/profile#publication-activity">View all <ArrowUpRight size={15} aria-hidden="true" /></Link></div>
          {!data ? <p role="status">Loading your activity…</p> : activity.length ? <ul>{activity.map(item => <li key={item.key}>
            <Link href="/dashboard/profile#publication-activity"><span className="dashboard-activity-dot" aria-hidden="true" /><span className="dashboard-activity-title"><strong>{item.title}</strong><small>{item.kind}</small></span><span className="dashboard-activity-status" data-status={item.status}>{item.status}</span></Link>
          </li>)}</ul> : <p className="dashboard-activity-empty">No publication requests yet. Submit a ready paper to start the review process.</p>}
        </section>
      </>}
      <div className="dashboard-links">
        <Link href="/dashboard/chat/new"><MessageSquare size={20} aria-hidden="true" /> New conversation</Link>
        {data?.admin && <button type="button" onClick={() => setPublicationOpen(true)}><Send size={20} aria-hidden="true" /> Request publication</button>}
      </div>
    </>}
    <PublicationRequestDialog open={publicationOpen} onOpenChange={setPublicationOpen} onCreated={() => setRefresh(value => value + 1)} />
  </DashboardLayout>;
}
