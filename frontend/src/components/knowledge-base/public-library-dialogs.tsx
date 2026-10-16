"use client";

import { useEffect, useRef, useState } from "react";
import { Download, ExternalLink, Loader2, Search, Upload } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { documentSize } from "@/lib/library";
import { CorpusEvidence, Department, PublicDocument, PublicMetadata } from "@/lib/public-library";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import Link from "next/link";

const message = (error: unknown) => error instanceof ApiError ? error.message : "Request failed. Please try again.";

// Added by ChatGPT: detail reads recheck publication rather than trusting an older catalog row.
export function PublicDocumentDetails({ id, onClose, manage = false }: { id: number | null; onClose: () => void; manage?: boolean }) {
  const [details, setDetails] = useState<{ document: PublicDocument; metadata: PublicMetadata; department: Department | null } | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setDetails(null); setError("");
    if (id === null) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const [document, metadata]: [PublicDocument, PublicMetadata] = await Promise.all([
          api.get(`/api/corpus/documents/${id}${manage ? "?include_unpublished=true" : ""}`, { signal: controller.signal, cache: "no-store" }),
          api.get(`/api/corpus/documents/${id}/metadata${manage ? "?include_unpublished=true" : ""}`, { signal: controller.signal, cache: "no-store" }),
        ]);
        const department = metadata.department_id ? await api.get(`/api/departments/${metadata.department_id}`, { signal: controller.signal }) : null;
        if (!controller.signal.aborted) setDetails({ document, metadata, department });
      } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof ApiError && failure.status === 404 ? "This document is no longer available in the public corpus." : message(failure)); }
    })();
    return () => controller.abort();
  }, [id, retry, manage]);
  const metadata = details?.metadata;
  return <Dialog open={id !== null} onOpenChange={open => { if (!open) onClose(); }}>
    <DialogContent className="public-document-dialog">
      <DialogHeader><DialogTitle className="break-words pr-6">{metadata?.title || "Public document"}</DialogTitle><DialogDescription>UAF Research Corpus</DialogDescription></DialogHeader>
      {error ? <div role="alert"><p>{error}</p><Button variant="outline" onClick={() => setRetry(value => value + 1)}>Retry</Button></div> :
        !details || !metadata ? <p role="status">Loading document...</p> : <>
          <dl className="document-details">
            <dt>Authors</dt><dd>{metadata.authors_text || "Not recorded"}</dd>
            <dt>Department</dt><dd>{details.department?.name || "Not assigned"}</dd>
            <dt>Type</dt><dd className="capitalize">{metadata.document_type || "Not recorded"}</dd>
            <dt>Publication</dt><dd>{metadata.publication_date || metadata.publication_year || "Not recorded"}</dd>
            {metadata.supervisor && <><dt>Supervisor</dt><dd>{metadata.supervisor}</dd></>}
            {metadata.language && <><dt>Language</dt><dd>{metadata.language}</dd></>}
            {metadata.doi && <><dt>DOI</dt><dd>{metadata.doi}</dd></>}
            <dt>File</dt><dd>{details.document.file_name} ({documentSize(details.document.file_size)})</dd>
          </dl>
          {!!metadata.keywords?.length && <ul className="public-keywords" aria-label="Keywords">{metadata.keywords.map(word => <li key={word}>{word}</li>)}</ul>}
          {metadata.abstract && <section className="public-abstract"><h3>Abstract</h3><p>{metadata.abstract}</p></section>}
          {details.document.researcher_card && <section className="public-researcher-card" aria-label="Researcher profile">
            {details.document.researcher_card.photo_url && <img src={details.document.researcher_card.photo_url} alt="" />}
            <div><h3>{details.document.researcher_card.full_name}</h3><p>{details.document.researcher_card.department_name} · {details.document.researcher_card.degree}</p>
              <p>{details.document.researcher_card.research_area}</p></div>
          </section>}
          <div className="public-dialog-actions">
            {/* Cookie-authenticated links retain server authorization and never expose MinIO paths. */}
            <Button asChild><a href={`/api/corpus/documents/${id}/content?inline=true${manage ? "&include_unpublished=true" : ""}`} target="_blank" rel="noopener noreferrer"><ExternalLink size={16} /> Open document</a></Button>
            <Button variant="outline" asChild><a href={`/api/corpus/documents/${id}/content${manage ? "?include_unpublished=true" : ""}`}><Download size={16} /> Download</a></Button>
          </div>
        </>}
    </DialogContent>
  </Dialog>;
}

// Added by ChatGPT: existing evidence retrieval only, not a new chat or selected-document RAG scope.
export function PublicQuery({ open, onOpenChange, onSelect }: { open: boolean; onOpenChange: (open: boolean) => void; onSelect: (id: number) => void }) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState("5");
  const [results, setResults] = useState<CorpusEvidence[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => { if (!open) { request.current?.abort(); setLoading(false); } return () => request.current?.abort(); }, [open]);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(""); setResults(null);
    try {
      const data = await api.post("/api/corpus/query", { query: query.trim(), top_k: Number(topK) }, { signal: controller.signal });
      if (!controller.signal.aborted) setResults(data.results);
    } catch (failure) { if (!controller.signal.aborted) setError(message(failure)); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="public-document-dialog">
    <DialogHeader><DialogTitle>Query UAF corpus</DialogTitle><DialogDescription>Published research evidence</DialogDescription></DialogHeader>
    <Link href="/dashboard/chat/new?scope=public" className="primary-action premium-action justify-center">Ask Research Assistant</Link>
    <form onSubmit={submit} className="space-y-3">
      <label htmlFor="public-question" className="block text-sm font-medium">Question</label>
      <textarea id="public-question" className="public-input w-full" rows={3} maxLength={4000} value={query} onChange={event => setQuery(event.target.value)} required />
      <div className="public-dialog-actions"><label className="text-sm">Results <select className="library-select" value={topK} onChange={event => setTopK(event.target.value)}>{[3, 5, 10].map(k => <option key={k} value={k}>{k}</option>)}</select></label>
        <Button type="submit" disabled={loading || !query.trim()}>{loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />} Find evidence</Button></div>
    </form>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Retrieving evidence...</p>}
    {results?.length === 0 && <p role="status">No published evidence found.</p>}
    {results && <div className="public-evidence" aria-label="Retrieved evidence">{results.map(result => <article key={result.metadata.chunk_id}>
      <button className="public-source" onClick={() => onSelect(result.metadata.document_id)}>{result.metadata.file_name}
        {Number.isInteger(result.metadata.page) && (result.metadata.page ?? -1) >= 0 ? `, page ${result.metadata.page! + 1}` : ""}<ExternalLink size={14} aria-hidden="true" /></button>
      <p>{result.content}</p>
    </article>)}</div>}
  </DialogContent></Dialog>;
}

// Added by ChatGPT: one admin upload through Phase 4; no metadata/publication/deletion management UI.
export function PublicUpload({ open, onOpenChange, onForbidden }: { open: boolean; onOpenChange: (open: boolean) => void; onForbidden: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [task, setTask] = useState<{ id: number; status: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!task || !["pending", "processing"].includes(task.status)) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const current = await api.get(`/api/corpus/tasks/${task.id}`, { signal: controller.signal, cache: "no-store" });
        if (controller.signal.aborted) return;
        setTask(current); setError("");
        if (["pending", "processing"].includes(current.status)) timer = setTimeout(poll, 2000);
      } catch (failure) {
        if (!controller.signal.aborted) { setError(message(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
      }
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [task?.id, task?.status, retry, onForbidden]);
  const upload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    if (!file.size || file.size > 20 * 1024 * 1024) { setError("Choose a non-empty file up to 20 MB."); return; }
    const controller = new AbortController(); request.current = controller;
    setUploading(true); setError("");
    const data = new FormData(); data.append("file", file);
    try {
      const result = await api.post("/api/corpus/documents/upload", data, { signal: controller.signal });
      if (!controller.signal.aborted) setTask(result);
    } catch (failure) {
      if (!controller.signal.aborted) { setError(message(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    } finally { if (!controller.signal.aborted) setUploading(false); }
  };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent>
    <DialogHeader><DialogTitle>Add public documents</DialogTitle><DialogDescription>UAF Research Corpus / Unpublished draft</DialogDescription></DialogHeader>
    {!task ? <form onSubmit={upload} className="space-y-4">
      <label htmlFor="public-upload" className="block text-sm font-medium">PDF, DOCX, TXT or MD (up to 20 MB)</label>
      <input id="public-upload" type="file" accept=".pdf,.docx,.txt,.md" className="public-file-input" disabled={uploading} onChange={event => setFile(event.target.files?.[0] || null)} required />
      <Button disabled={uploading || !file} type="submit">{uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />} {uploading ? "Uploading..." : "Upload document"}</Button>
    </form> : <div className="space-y-3"><p role="status">{task.status === "completed" ? "Processed. Draft awaiting publication." : task.status === "failed" ? "Processing failed. The upload has been retained." : `Document ${task.status}...`}</p>
      <p className="text-sm text-muted-foreground">Upload task #{task.id}</p>
      {["completed", "failed"].includes(task.status) && <Button variant="outline" onClick={() => { setTask(null); setFile(null); setError(""); }}>Upload another</Button>}
    </div>}
    {error && <div role="alert"><p>{error}</p>{task && <Button variant="outline" onClick={() => setRetry(value => value + 1)}>Refresh status</Button>}</div>}
  </DialogContent></Dialog>;
}
