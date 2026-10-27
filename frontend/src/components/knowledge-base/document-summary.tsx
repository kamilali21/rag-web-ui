"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { DocumentSummary, SummaryCitation, SummaryScope } from "@/lib/document-summary";
import { comparisonRequestId } from "@/lib/comparison";

const unavailableText = "Not identified in retrieved evidence.";

function sourceUrl(citation: SummaryCitation) {
  const path = citation.scope === "public"
    ? `/api/corpus/documents/${citation.document_id}/content?inline=true`
    : `/api/knowledge-base/${citation.knowledge_base_id}/documents/${citation.document_id}/content?inline=true`;
  return `${path}${citation.page === null ? "" : `#page=${citation.page + 1}`}`;
}

function errorText(error: unknown) {
  return error instanceof ApiError ? error.message : "Could not summarize this document. Please retry.";
}

export function DocumentSummaryPanel({ documentId, scope }: { documentId: number; scope: SummaryScope }) {
  const [summary, setSummary] = useState<DocumentSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  const requestId = useRef<string | null>(null);

  useEffect(() => {
    request.current?.abort();
    setSummary(null);
    setLoading(false);
    setError("");
    requestId.current = null;
    return () => request.current?.abort();
  }, [documentId, scope]);

  const summarize = async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    if (!requestId.current) requestId.current = comparisonRequestId();
    try {
      const result: DocumentSummary = await api.post(
        "/api/retrieval/documents/summarize",
        { document_id: documentId, scope, request_id: requestId.current },
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) { setSummary(result); requestId.current = null; }
    } catch (failure) {
      if (!controller.signal.aborted) {
        setError(errorText(failure));
        if (failure instanceof ApiError && failure.status > 0) requestId.current = null;
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  return <div className="document-summary-control">
    <Button type="button" variant="outline" disabled={loading} onClick={() => void summarize()}>
      {loading ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Sparkles size={16} aria-hidden="true" />}
      {loading ? "Summarizing..." : summary ? "Refresh summary" : "Summarize paper"}
    </Button>
    <p className="insights-workflow-note">New summaries are saved privately in <a className="insights-text-action" href="/dashboard/insights/history">Analysis history</a>.</p>
    {loading && <p role="status" className="document-summary-status">Retrieving evidence from this paper and preparing its summary...</p>}
    {error && <div role="alert" className="document-summary-error">
      <p>{error}</p>
      <Button type="button" variant="outline" disabled={loading} onClick={() => void summarize()}>Retry summary</Button>
    </div>}
    {summary && <><SummaryResult summary={summary} />{summary.run_id && <a className="insights-text-action" href={`/dashboard/insights/history?run=${summary.run_id}`}>Reopen saved summary</a>}</>}
  </div>;
}

export function SummaryResult({ summary }: { summary: DocumentSummary }) {
  return <section className="document-summary" aria-label="Evidence-grounded summary">
      <h3><FileText size={17} aria-hidden="true" /> Evidence-grounded summary</h3>
      {summary.status === "insufficient_evidence" && <p role="status" className="document-summary-status">{summary.message}</p>}
      <div className="document-summary-sections">
        {summary.sections.map(section => <section key={section.key}>
          <h4>{section.title}</h4>
          {section.unavailable || section.claims.length === 0
            ? <p className="document-summary-unavailable">{unavailableText}</p>
            : <ul>{section.claims.map((claim, index) => <li key={`${section.key}-${index}`}>
              <span>{claim.text}</span>
              <span className="document-summary-citations" aria-label="Claim citations">
                {claim.citations.map(citation => <a key={`${citation.id}-${citation.page ?? "unknown"}`}
                  href={sourceUrl(citation)} target="_blank" rel="noopener noreferrer"
                  aria-label={`Open ${citation.file_name}${citation.page === null ? "" : `, page ${citation.page + 1}`}`}
                  title={`${citation.file_name}${citation.page === null ? "" : `, page ${citation.page + 1}`}`}>
                  [{citation.id}]{citation.page === null ? "" : ` p. ${citation.page + 1}`}
                </a>)}
              </span>
            </li>)}</ul>}
        </section>)}
      </div>
    </section>;
}
