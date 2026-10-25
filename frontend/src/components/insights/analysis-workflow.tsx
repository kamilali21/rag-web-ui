"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { InsightsDocument, InsightsScope } from "@/lib/insights";
import { comparisonRequestId } from "@/lib/comparison";
import { AnalysisRun, lastAnalysisKey, validAnalysisRequest } from "@/lib/research-analysis";
import { AnalysisResult } from "./analysis-result";

export function AnalysisWorkflow({ selected, scope, toggle, onClose, onStarted }: {
  selected: InsightsDocument[]; scope: InsightsScope; toggle: (document: InsightsDocument) => void; onClose: () => void; onStarted?: (requestId: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [focus, setFocus] = useState<"overview" | "contradictions" | "candidate_gaps">("overview");
  const [includeRelated, setIncludeRelated] = useState(scope !== "private");
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [savedPath, setSavedPath] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const pending = useRef<AbortController | null>(null);
  const requestKey = useRef<{ body: string; id: string } | null>(null);
  const fail = (failure: unknown) => setError(failure instanceof ApiError ? failure.message : "Unable to load analysis. Please retry.");
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now(); setElapsed(0);
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [busy]);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = Number(params.get("analysis")), requestId = params.get("analysisRequest");
    const path = Number.isSafeInteger(id) && id > 0 ? `/api/insights/analyses/${id}`
      : validAnalysisRequest(requestId) ? `/api/insights/analyses/requests/${requestId}` : null;
    if (!path) return;
    const controller = new AbortController(); pending.current = controller;
    let timer: ReturnType<typeof setTimeout>; let polls = 0;
    setSavedPath(path); setBusy(true); setError(""); setRun(null);
    const read = async () => {
      try {
        const value: AnalysisRun = await api.get(path, { signal: controller.signal, cache: "no-store" });
        if (controller.signal.aborted) return;
        setRun(value);
        if (value.status === "processing" && ++polls < 60) timer = setTimeout(() => void read(), 5000);
      } catch (failure) { if (!controller.signal.aborted) fail(failure); }
      finally { if (!controller.signal.aborted) setBusy(false); }
    };
    void read();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [reload]);
  const setLocation = (key: string, value: string) => {
    const url = new URL(window.location.href); url.searchParams.delete("analysis"); url.searchParams.delete("analysisRequest");
    url.searchParams.set(key, value); window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  };
  const generate = async () => {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setBusy(true); setError("");
    const body = { scope, document_ids: selected.map(doc => doc.id), question, include_related: scope !== "private" && includeRelated,
      ...(focus !== "overview" ? { focus } : {}) };
    if (requestKey.current?.body !== JSON.stringify(body)) requestKey.current = { body: JSON.stringify(body), id: comparisonRequestId() };
    const requestId = requestKey.current.id;
    try { sessionStorage.setItem(lastAnalysisKey, requestId); } catch { /* Storage may be disabled. */ }
    onStarted?.(requestId); setLocation("analysisRequest", requestId);
    try {
      const result: AnalysisRun = await api.post("/api/insights/analyses", { ...body, request_id: requestKey.current.id }, { signal: controller.signal });
      if (!controller.signal.aborted) { setRun(result); setLocation("analysis", String(result.id)); }
    } catch (failure) {
      if (!controller.signal.aborted) { fail(failure); if (failure instanceof ApiError && failure.status > 0) requestKey.current = null; }
    } finally { if (!controller.signal.aborted) setBusy(false); }
  };
  return <>
    {error && <p role="alert">{error}</p>}
    {run ? <><AnalysisResult run={run} /><div className="insights-dialog-actions"><Button variant="outline" onClick={onClose}>Close analysis</Button>{run.status === "processing" && <Button disabled={busy} onClick={() => { setLocation("analysis", String(run.id)); setReload(value => value + 1); }}>Check analysis status</Button>}</div></>
      : savedPath ? <><p role="status">{busy ? "Loading saved analysis..." : "Saved analysis unavailable."}</p><Button disabled={busy} onClick={() => setReload(value => value + 1)}>Retry saved analysis</Button></>
      : <>
        <div className="insights-picker" role="group" aria-label="Selected documents">{selected.map(doc => <label key={doc.id}><input type="checkbox" checked disabled={busy} onChange={() => toggle(doc)} /><span>{doc.title}<small>{doc.scope} / {doc.authors_text || "Author not recorded"}</small></span></label>)}</div>
        <label className="insights-field">Analysis focus<select className="public-input" disabled={busy} value={focus} onChange={event => setFocus(event.target.value as typeof focus)}><option value="overview">Research overview</option><option value="contradictions">Evidence interpretation</option><option value="candidate_gaps">Candidate research gaps</option></select></label>
        {focus === "contradictions" && <p className="insights-workflow-note">Select at least two papers. Identify supporting, contradicting and qualifying evidence, with cited context differences. This does not decide which study is right.</p>}
        {focus === "candidate_gaps" && <p className="insights-workflow-note">Identify candidate gaps within the indexed corpus using cited evidence patterns and verified source quotations. This is a bounded review, not proof of a gap in global research.</p>}
        <label className="insights-field">Research question (optional)<textarea rows={2} maxLength={1000} disabled={busy} value={question} onChange={event => setQuestion(event.target.value)} /></label>
        <label className="analysis-related-choice"><input type="checkbox" checked={scope !== "private" && includeRelated} disabled={busy || scope === "private"} onChange={event => setIncludeRelated(event.target.checked)} /> Include up to 3 related public papers</label>
        <p className="insights-workflow-note">{scope === "private" ? "Private scope uses only your selected papers. Choose Both to include related public evidence." : "Related discovery narrows to at most 20 metadata-matched public papers before semantic ranking."} Select 1–5 papers. Missing information is marked explicitly.</p>
        {busy && <p role="status">Building profiles and synthesizing cited findings ({elapsed}s). The selected model can take a few minutes. You can close this dialog and use Resume last analysis without generating again.</p>}
        {error && <Button variant="outline" onClick={() => setReload(value => value + 1)}>Check saved result</Button>}
        <div className="insights-dialog-actions"><Button variant="outline" onClick={onClose}>{busy ? "Close and resume later" : "Cancel"}</Button><Button disabled={busy || selected.length < (focus === "contradictions" ? 2 : 1)} onClick={() => void generate()}>{busy ? "Analysing papers..." : "Generate analysis"}</Button></div>
      </>}
  </>;
}
