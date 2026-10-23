"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { InsightsDocument, InsightsScope } from "@/lib/insights";
import { comparisonRequestId } from "@/lib/comparison";
import { AnalysisRun } from "@/lib/research-analysis";
import { AnalysisResult } from "./analysis-result";

export function AnalysisWorkflow({ selected, scope, toggle, onClose }: {
  selected: InsightsDocument[]; scope: InsightsScope; toggle: (document: InsightsDocument) => void; onClose: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [includeRelated, setIncludeRelated] = useState(scope !== "private");
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const pending = useRef<AbortController | null>(null);
  const requestKey = useRef<{ body: string; id: string } | null>(null);
  const fail = (failure: unknown) => setError(failure instanceof ApiError ? failure.message : "Unable to load analysis. Please retry.");
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    const id = Number(new URLSearchParams(window.location.search).get("analysis"));
    if (!Number.isSafeInteger(id) || id <= 0) return;
    const controller = new AbortController(); pending.current = controller;
    setSavedId(id); setBusy(true); setError(""); setRun(null);
    api.get(`/api/insights/analyses/${id}`, { signal: controller.signal, cache: "no-store" })
      .then((value: AnalysisRun) => { if (!controller.signal.aborted) setRun(value); })
      .catch(failure => { if (!controller.signal.aborted) fail(failure); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [reload]);
  const generate = async () => {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setBusy(true); setError("");
    const body = { scope, document_ids: selected.map(doc => doc.id), question, include_related: scope !== "private" && includeRelated };
    if (requestKey.current?.body !== JSON.stringify(body)) requestKey.current = { body: JSON.stringify(body), id: comparisonRequestId() };
    try {
      const result: AnalysisRun = await api.post("/api/insights/analyses", { ...body, request_id: requestKey.current.id }, { signal: controller.signal });
      if (!controller.signal.aborted) setRun(result);
    } catch (failure) {
      if (!controller.signal.aborted) { fail(failure); if (failure instanceof ApiError && failure.status > 0) requestKey.current = null; }
    } finally { if (!controller.signal.aborted) setBusy(false); }
  };
  return <>
    {error && <p role="alert">{error}</p>}
    {run ? <><AnalysisResult run={run} /><div className="insights-dialog-actions"><Button variant="outline" onClick={onClose}>Close analysis</Button>{run.status === "processing" && <Button asChild><a href={`/dashboard/insights?analysis=${run.id}`}>Reload saved analysis</a></Button>}</div></>
      : savedId ? <><p role="status">{busy ? "Loading saved analysis..." : "Saved analysis unavailable."}</p><Button disabled={busy} onClick={() => setReload(value => value + 1)}>Retry saved analysis</Button></>
      : <>
        <div className="insights-picker" role="group" aria-label="Selected documents">{selected.map(doc => <label key={doc.id}><input type="checkbox" checked disabled={busy} onChange={() => toggle(doc)} /><span>{doc.title}<small>{doc.scope} / {doc.authors_text || "Author not recorded"}</small></span></label>)}</div>
        <label className="insights-field">Research question (optional)<textarea rows={2} maxLength={1000} disabled={busy} value={question} onChange={event => setQuestion(event.target.value)} /></label>
        <label className="analysis-related-choice"><input type="checkbox" checked={scope !== "private" && includeRelated} disabled={busy || scope === "private"} onChange={event => setIncludeRelated(event.target.checked)} /> Include up to 3 related public papers</label>
        <p className="insights-workflow-note">{scope === "private" ? "Private scope uses only your selected papers. Choose Both to include related public evidence." : "Related discovery narrows to at most 20 metadata-matched public papers before semantic ranking."} Select 1–5 papers. Missing information is marked explicitly.</p>
        {busy && <p role="status">Building research profiles, checking related evidence and synthesizing cited findings. Closing this dialog does not cancel server processing.</p>}
        <div className="insights-dialog-actions"><Button variant="outline" onClick={onClose}>Cancel</Button><Button disabled={busy || !selected.length} onClick={() => void generate()}>{busy ? "Analysing papers..." : "Generate analysis"}</Button></div>
      </>}
  </>;
}
