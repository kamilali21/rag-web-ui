"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, ExternalLink, Loader2, RefreshCw, Save, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Department } from "@/lib/public-library";
import { Button } from "@/components/ui/button";

type ReviewItem = { id: number; request_type: "publication" | "withdrawal"; status: string; title?: string;
  source_file_name?: string | null; created_at: string; requester_id: number; profile: Record<string, any> | null;
  metadata?: Record<string, any>; public_document_id?: number | null; publication_request_id?: number;
  reason?: string | null; decision_reason?: string | null; public_card_consent?: boolean };
type Detail = ReviewItem & { document?: { id: number; file_name: string; file_size: number; content_type: string } | null;
  admin_photo_url?: string | null; metadata: Record<string, any> };
const message = (error: unknown) => error instanceof ApiError ? error.message : "Request failed. Please try again.";
const types = ["paper", "thesis", "report", "other"];

export function PublicationRequestsAdmin({ onBack, onForbidden }: { onBack: () => void; onForbidden: () => void }) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selected, setSelected] = useState<Detail | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [draft, setDraft] = useState<Record<string, any>>({});
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  const load = useCallback(async (signal?: AbortSignal) => {
    const [queue, departmentsPage]: [ReviewItem[], Department[]] = await Promise.all([
      api.get("/api/researcher/admin", { signal, cache: "no-store" }),
      api.get("/api/departments?include_inactive=true&limit=100", { signal, cache: "no-store" }),
    ]);
    if (!signal?.aborted) { setItems(queue); setDepartments(departmentsPage); }
  }, []);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    void load(controller.signal).catch(failure => { if (!controller.signal.aborted) {
      setError(message(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden();
    } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load, refresh, onForbidden]);

  useEffect(() => {
    if (!items.some(item => item.status === "processing")) return;
    const timer = setTimeout(() => setRefresh(value => value + 1), 3000);
    return () => clearTimeout(timer);
  }, [items]);

  const open = async (item: ReviewItem) => {
    setSelected(null); setError(""); setBusy(true);
    try {
      if (item.request_type === "withdrawal") { setSelected(item as Detail); return; }
      const detail: Detail = await api.get(`/api/researcher/admin/${item.id}`, { cache: "no-store" });
      setSelected({ ...item, ...detail }); setDraft(detail.metadata); setReason("");
    } catch (failure) { setError(message(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    finally { setBusy(false); }
  };
  const runAction = async (url: string, data?: unknown) => {
    if (!selected) return;
    setBusy(true); setError("");
    try { await api.post(url, data); setSelected(null); setRefresh(value => value + 1); }
    catch (failure) { setError(message(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    finally { setBusy(false); }
  };
  const saveMetadata = async (event: React.FormEvent) => {
    event.preventDefault(); if (!selected) return;
    setBusy(true); setError("");
    const body = { ...draft, department_id: Number(draft.department_id),
      publication_year: draft.publication_year ? Number(draft.publication_year) : null,
      keywords: typeof draft.keywords === "string" ? draft.keywords.split(",").map((word: string) => word.trim()).filter(Boolean) : draft.keywords };
    try {
      const updated = await api.patch(`/api/researcher/admin/${selected.id}/metadata`, body);
      setDraft(updated.metadata); setSelected({ ...selected, metadata: updated.metadata }); setRefresh(value => value + 1);
    } catch (failure) { setError(message(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    finally { setBusy(false); }
  };
  const update = (key: string, value: any) => setDraft((previous: Record<string, any>) => ({ ...previous, [key]: value }));
  const titleOf = (item: ReviewItem) => item.metadata?.title || item.title || item.source_file_name || `${item.request_type} request #${item.id}`;

  return <section className="list-page publication-review">
    <header className="researcher-page-heading"><div><button className="corpus-back" onClick={onBack}><ArrowLeft size={16} /> Public Library</button>
      <h1>Publication requests</h1><p>Review submissions and withdrawal requests.</p></div>
      <Button variant="outline" disabled={loading} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={16} /> Refresh</Button>
    </header>
    {error && <p role="alert" className="corpus-error">{error}</p>}
    {selected ? <div className="review-detail">
      <div className="researcher-section-heading"><div><h2>{titleOf(selected)}</h2><p>{selected.request_type === "publication" ? `Publication request #${selected.id}` : `Withdrawal request #${selected.id}`} · {selected.status}</p></div>
        <Button variant="outline" onClick={() => setSelected(null)}>Back to requests</Button></div>
      {selected.request_type === "publication" ? <>
        <section className="review-profile"><div className="review-avatar">{selected.admin_photo_url ? <img src={selected.admin_photo_url} alt="Requester profile" /> : <span aria-hidden="true">{selected.profile?.full_name?.slice(0, 1) || "R"}</span>}</div>
          <div><h3>{selected.profile?.full_name || "Researcher"}</h3><p>{selected.profile?.department_name} · {selected.profile?.degree}</p><p>Research area: {selected.profile?.research_area}</p>
            <p>Ag number: {selected.profile?.ag_number || "Not provided"} · Class: {selected.profile?.class_name || "Not provided"} · Section: {selected.profile?.section || "Not provided"}</p></div></section>
        <section className="review-source"><div><h3>Requested private document</h3><p>{selected.document?.file_name || selected.source_file_name || "Unavailable"}</p>
          <p>Public researcher card consent: {selected.public_card_consent ? "Yes" : "No"}</p></div>
          {selected.document && <a className="primary-action" href={`/api/researcher/admin/${selected.id}/source?inline=true`} target="_blank" rel="noopener noreferrer"><ExternalLink size={16} /> Open exact document</a>}
        </section>
        <form className="corpus-form review-metadata" onSubmit={saveMetadata}>
          <h3 className="corpus-form-wide">Request metadata</h3>
          <label className="corpus-form-wide">Title<input className="public-input" required maxLength={500} value={draft.title || ""} onChange={event => update("title", event.target.value)} /></label>
          <label className="corpus-form-wide">Author(s)<textarea className="public-input" required rows={2} maxLength={8000} value={draft.authors_text || ""} onChange={event => update("authors_text", event.target.value)} /></label>
          <label>Department<select className="public-input" required value={draft.department_id || ""} onChange={event => update("department_id", event.target.value)}><option value="">Choose department</option>
            {departments.map(item => <option key={item.id} value={item.id}>{item.name}{item.is_active ? "" : " (inactive)"}</option>)}</select></label>
          <label>Document type<select className="public-input" required value={draft.document_type || ""} onChange={event => update("document_type", event.target.value)}><option value="">Choose type</option>{types.map(type => <option key={type}>{type}</option>)}</select></label>
          <label>Publication year<input className="public-input" type="number" min={1000} max={9999} value={draft.publication_year || ""} onChange={event => update("publication_year", event.target.value)} /></label>
          <label>Publication date<input className="public-input" type="date" value={draft.publication_date || ""} onChange={event => update("publication_date", event.target.value)} /></label>
          <label className="corpus-form-wide">Abstract<textarea className="public-input" rows={3} maxLength={16000} value={draft.abstract || ""} onChange={event => update("abstract", event.target.value)} /></label>
          <label>Keywords<input className="public-input" maxLength={2020} value={Array.isArray(draft.keywords) ? draft.keywords.join(", ") : draft.keywords || ""} onChange={event => update("keywords", event.target.value)} /></label>
          <label>Supervisor<input className="public-input" maxLength={255} value={draft.supervisor || ""} onChange={event => update("supervisor", event.target.value)} /></label>
          <label>DOI<input className="public-input" maxLength={255} value={draft.doi || ""} onChange={event => update("doi", event.target.value)} /></label>
          <label>Language<input className="public-input" maxLength={35} value={draft.language || ""} onChange={event => update("language", event.target.value)} /></label>
          {["pending", "failed"].includes(selected.status) && <div className="corpus-form-wide flex justify-end"><Button type="submit" variant="outline" disabled={busy}><Save size={16} /> Save metadata</Button></div>}
        </form>
        {selected.status === "pending" && <section className="review-decision"><label>Denial reason (required to deny)<textarea className="public-input" rows={2} maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></label>
          <div><Button disabled={busy} onClick={() => void runAction(`/api/researcher/admin/${selected.id}/approve`)}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />} Approve &amp; index</Button>
            <Button variant="destructive" disabled={busy || !reason.trim()} onClick={() => void runAction(`/api/researcher/admin/${selected.id}/deny`, { reason })}><X size={16} /> Deny request</Button></div>
        </section>}
        {selected.status === "failed" && <Button disabled={busy} onClick={() => void runAction(`/api/researcher/admin/${selected.id}/approve`)}><RefreshCw size={16} /> Retry indexing</Button>}
        {selected.status === "processing" && <p role="status">Public copy is processing. It will appear only after indexing succeeds.</p>}
      </> : <>
        <section className="review-profile"><div><h3>{selected.profile?.full_name || "Researcher"}</h3><p>{selected.profile?.department_name} · {selected.profile?.degree}</p><p>Research area: {selected.profile?.research_area}</p>
          <p>Ag number: {selected.profile?.ag_number || "Not provided"} · Class: {selected.profile?.class_name || "Not provided"} · Section: {selected.profile?.section || "Not provided"}</p></div></section>
        <section className="review-source"><div><h3>Published document</h3><p>{selected.source_file_name || "Unavailable"}</p><p>Reason: {selected.reason || "Not provided"}</p></div>
          <a className="primary-action" href={`/api/researcher/admin/withdrawals/${selected.id}/document`} target="_blank" rel="noopener noreferrer"><ExternalLink size={16} /> Open exact document</a></section>
        <section className="review-decision"><label>Decision reason (required to deny)<textarea className="public-input" rows={2} maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></label>
          <div><Button disabled={busy} onClick={() => void runAction(`/api/researcher/admin/withdrawals/${selected.id}/approve`)}><Check size={16} /> Approve withdrawal</Button>
            <Button variant="destructive" disabled={busy || !reason.trim()} onClick={() => void runAction(`/api/researcher/admin/withdrawals/${selected.id}/deny`, { reason })}><X size={16} /> Deny request</Button></div></section>
      </>}
    </div> : loading ? <p role="status">Loading requests...</p> : items.length ? <div className="researcher-request-list">{items.map(item =>
      <button className="review-queue-row" key={`${item.request_type}-${item.id}`} onClick={() => void open(item)} disabled={busy}>
        <span><strong>{titleOf(item)}</strong><small>{item.profile?.full_name || "Researcher"} · {item.profile?.department_name || "Department not recorded"}</small></span>
        <span className="review-queue-status"><span className="capitalize">{item.request_type}</span><small>{item.status}</small></span>
      </button>)}</div> : <div className="library-empty"><Check size={32} /><h2>No requests need review</h2></div>}
  </section>;
}
