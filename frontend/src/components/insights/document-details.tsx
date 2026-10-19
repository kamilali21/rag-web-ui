"use client";
import { useEffect, useState } from "react";
import { Download, ExternalLink } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { InsightsDocument } from "@/lib/insights";
import { documentSize } from "@/lib/library";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DocumentSummaryPanel } from "@/components/knowledge-base/document-summary";

export function PrivateInsightsDetails({ id, onClose }: { id: number; onClose: () => void }) {
  const [document, setDocument] = useState<InsightsDocument | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setDocument(null); setError("");
    api.get(`/api/insights/documents/${id}?scope=private`, { signal: controller.signal, cache: "no-store" })
      .then(value => { if (!controller.signal.aborted) setDocument(value); })
      .catch(failure => { if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : "Unable to load this document."); });
    return () => controller.abort();
  }, [id, retry]);
  const content = document ? `/api/knowledge-base/${document.knowledge_base_id}/documents/${document.id}/content` : "";
  return <Dialog open onOpenChange={open => { if (!open) onClose(); }}><DialogContent className="public-document-dialog">
    <DialogHeader><DialogTitle>{document?.title || "Private document"}</DialogTitle><DialogDescription>Your ready private paper</DialogDescription></DialogHeader>
    {error ? <div role="alert"><p>{error}</p><Button onClick={() => setRetry(value => value + 1)}>Retry</Button></div> : !document ? <p role="status">Loading document...</p> : <>
      <dl className="document-details"><dt>File</dt><dd>{document.file_name} ({documentSize(document.file_size)})</dd><dt>Author</dt><dd>{document.authors_text || "Not recorded"}</dd><dt>Department</dt><dd>{document.department_name || "Not assigned"}</dd></dl>
      {document.abstract && <p>{document.abstract}</p>}
      <DocumentSummaryPanel documentId={document.id} scope="private" />
      <div className="public-dialog-actions"><Button asChild><a href={`${content}?inline=true`} target="_blank" rel="noopener noreferrer"><ExternalLink size={16} /> Open document</a></Button><Button asChild variant="outline"><a href={content}><Download size={16} /> Download</a></Button></div>
    </>}
  </DialogContent></Dialog>;
}
