"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight, History, Loader2, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ComparisonRun } from "@/lib/comparison";
import { AnalysisRun } from "@/lib/research-analysis";
import { DocumentSummary } from "@/lib/document-summary";
import { ComparisonResult } from "./comparison-result";
import { AnalysisResult } from "./analysis-result";
import { SummaryResult } from "@/components/knowledge-base/document-summary";

export const historyTypes = { summary: "Summary", compare: "Comparison", analyze: "Research overview", contradictions: "Evidence interpretation", candidate_gaps: "Candidate research gaps" };
const statuses = { processing: "Processing", complete: "Complete", failed: "Failed", insufficient_evidence: "Insufficient evidence" };
type Kind = keyof typeof historyTypes;
type Status = keyof typeof statuses;
type Entry = { id: number; analysis_type: Kind; status: Status; scope: string; created_at: string; available: boolean;
  documents: { id: number; title: string }[]; question: string | null };
type Saved = { id: number; analysis_type: Kind; status: Status; created_at: string; completed_at: string | null; error_message: string | null;
  result: AnalysisRun["result"] | ComparisonRun["result"] | DocumentSummary;
  evidence: { evidence_id: string; document_id: number; page: number | null; excerpt: string; evidence_hash: string }[] };
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Unable to load history. Please retry.";
const dateText = (value: string) => new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`).toLocaleString();

export function AnalysisHistory() {
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [scope, setScope] = useState("");
  const [cursors, setCursors] = useState<(number | null)[]>([null]);
  const [items, setItems] = useState<Entry[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [run, setRun] = useState<Saved | null>(null);
  const [reading, setReading] = useState(false);
  const [readError, setReadError] = useState("");
  const [reload, setReload] = useState(0);
  const trigger = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    const id = Number(new URLSearchParams(window.location.search).get("run"));
    if (Number.isSafeInteger(id) && id > 0) setSelected(id);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setItems([]); setNext(null);
    const params = new URLSearchParams({ limit: "20" });
    if (kind) params.set("analysis_type", kind);
    if (status) params.set("status", status);
    if (scope) params.set("scope", scope);
    const before = cursors[cursors.length - 1];
    if (before) params.set("before_id", String(before));
    api.get(`/api/insights/history?${params}`, { signal: controller.signal, cache: "no-store" })
      .then((data: { items: Entry[]; next_before_id: number | null }) => { if (!controller.signal.aborted) { setItems(data.items); setNext(data.next_before_id); } })
      .catch(failure => { if (!controller.signal.aborted) setError(errorText(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [kind, status, scope, cursors, refresh]);
  useEffect(() => {
    if (selected === null) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>; let polls = 0;
    setRun(null); setReading(true); setReadError("");
    const read = async () => {
      try {
        const value: Saved = await api.get(`/api/insights/history/${selected}`, { signal: controller.signal, cache: "no-store" });
        if (controller.signal.aborted) return;
        setRun(value);
        if (value.status === "processing" && ++polls < 60) timer = setTimeout(() => void read(), 5000);
      } catch (failure) { if (!controller.signal.aborted) { setRun(null); setReadError(errorText(failure)); } }
      finally { if (!controller.signal.aborted) setReading(false); }
    };
    void read();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [selected, reload]);
  const choose = (id: number, button: HTMLButtonElement) => {
    trigger.current = button; setSelected(id);
    const url = new URL(window.location.href); url.searchParams.set("run", String(id));
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  };
  const close = () => {
    setSelected(null); setRun(null);
    if (run) setItems(values => values.map(item => item.id === run.id ? { ...item, status: run.status } : item));
    const url = new URL(window.location.href); url.searchParams.delete("run");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  };
  return <section className="list-page" aria-label="Analysis history">
    <div className="library-heading"><div className="library-title"><h1>Analysis history</h1><History size={27} aria-hidden="true" /></div>
      <Button variant="outline" asChild><a href="/dashboard/insights"><ArrowLeft size={18} /> Back to Insights</a></Button></div>
    <p className="insights-catalog-note">Your saved summaries, comparisons and analyses. Reopen results and inspect the evidence without generating again. Source access is checked each time.</p>
    <div className="history-filters">
      <label>Workflow<select className="public-input" value={kind} onChange={event => { setKind(event.target.value); setCursors([null]); }}><option value="">All workflows</option>{Object.entries(historyTypes).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Status<select className="public-input" value={status} onChange={event => { setStatus(event.target.value); setCursors([null]); }}><option value="">All statuses</option>{Object.entries(statuses).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Sources<select className="public-input" value={scope} onChange={event => { setScope(event.target.value); setCursors([null]); }}><option value="">All sources</option><option value="public">Public</option><option value="private">Private</option><option value="both">Public + Private</option></select></label>
      <Button variant="outline" disabled={loading} onClick={() => { setCursors([null]); setRefresh(value => value + 1); }}><RefreshCw size={16} /> Refresh history</Button>
    </div>
    {error ? <div className="library-empty" role="alert"><p>{error}</p><Button onClick={() => setRefresh(value => value + 1)}>Retry history</Button></div>
      : loading ? <div className="library-empty" role="status"><Loader2 className="animate-spin" /><p>Loading history...</p></div>
      : !items.length ? <div className="library-empty"><History size={36} /><h2>{kind || status || scope ? "No matching history" : "No saved research yet"}</h2><p>Generate a summary from Library, or compare and analyse papers in Insights.</p></div>
      : <table className="library-table history-table" aria-label="Saved research"><thead><tr><th scope="col">Research</th><th scope="col">Workflow</th><th scope="col">Status</th><th scope="col">Saved</th><th scope="col"><span className="sr-only">Open result</span></th></tr></thead>
        <tbody>{items.map(item => <tr key={item.id}><td><div className="history-title">{item.available ? item.question || item.documents.map(doc => doc.title).join(" · ") : "Sources no longer available"}</div><small>{item.available ? `${item.documents.length} selected paper${item.documents.length === 1 ? "" : "s"} · ${item.scope === "both" ? "Public + Private" : item.scope}` : "Saved content is hidden because source access changed."}</small></td>
          <td data-label="Workflow">{historyTypes[item.analysis_type]}</td><td data-label="Status"><span className="dashboard-activity-status">{statuses[item.status]}</span></td><td data-label="Saved"><time dateTime={`${item.created_at}Z`}>{dateText(item.created_at)}</time></td>
          <td><Button variant="outline" disabled={!item.available} aria-label={`Open ${historyTypes[item.analysis_type].toLowerCase()} ${item.id}`} onClick={event => choose(item.id, event.currentTarget)}>Open</Button></td></tr>)}</tbody></table>}
    <div className="library-footer"><p role="status">{!loading && !error ? `${items.length} saved result${items.length === 1 ? "" : "s"} on this page` : ""}</p><nav className="library-tools" aria-label="History pages"><button className="icon-button" aria-label="Previous history page" disabled={loading || !!error || cursors.length === 1} onClick={() => setCursors(value => value.slice(0, -1))}><ChevronLeft size={20} /></button><span>Page {cursors.length}</span><button className="icon-button" aria-label="Next history page" disabled={loading || !!error || next === null} onClick={() => setCursors(value => [...value, next])}><ChevronRight size={20} /></button></nav></div>
    <Dialog open={selected !== null} onOpenChange={open => { if (!open) close(); }}><DialogContent className="insights-dialog" onCloseAutoFocus={event => { if (trigger.current?.isConnected) { event.preventDefault(); trigger.current.focus(); } }}>
      <DialogHeader><DialogTitle>{run ? historyTypes[run.analysis_type] : "Saved research"}</DialogTitle><DialogDescription>Private saved output. Citations open the source; snapshots preserve the evidence used at generation time.</DialogDescription></DialogHeader>
      {reading && <p role="status">Loading saved result...</p>}
      {readError && <p role="alert">{readError}</p>}
      {run?.status === "processing" && <p role="status">Still processing. This view checks status without starting another generation.</p>}
      {run?.status === "failed" && <p role="alert">{run.error_message || "Generation failed. Start a new request from Library or Insights."}</p>}
      {run?.result && (run.analysis_type === "summary" ? <SummaryResult summary={run.result as DocumentSummary} /> : run.analysis_type === "compare" ? <ComparisonResult run={run as ComparisonRun} /> : <AnalysisResult run={run as AnalysisRun} />)}
      {!!run?.evidence.length && <details className="comparison-evidence"><summary>Saved evidence snapshots ({run.evidence.length})</summary><p className="insights-workflow-note">These passages are the stored evidence, not a fresh retrieval. Retrieval scores are not scientific confidence.</p>{run.evidence.map(item => <article key={item.evidence_id}><h4>{item.evidence_id} · Document {item.document_id}{item.page === null ? "" : ` · Page ${item.page + 1}`}</h4><blockquote>{item.excerpt}</blockquote></article>)}</details>}
      <div className="insights-dialog-actions"><Button variant="outline" onClick={close}>Close saved result</Button>{(readError || run?.status === "processing") && <Button disabled={reading} onClick={() => setReload(value => value + 1)}>Check saved result</Button>}</div>
    </DialogContent></Dialog>
  </section>;
}
