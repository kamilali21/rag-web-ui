"use client";

import { useEffect, useState } from "react";
import { Save, Loader2, Plus, Pencil } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Department, PublicMetadata } from "@/lib/public-library";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const adminError = (error: unknown) => error instanceof ApiError ? error.message : "Request failed. Please try again.";
export type AdminTask = { id: number; document_id: number | null; upload_id: number | null; title: string | null;
  file_name: string; status: string; publication_status: string; created_at: string; error_message: string | null };
type Changed = { onClose: () => void; onChanged: () => void; onForbidden: () => void };

// Added by ChatGPT: one dialog scale, scrollable body and fixed actions across corpus CRUD forms.
export function CorpusDialog({ title, description, children, footer, busy, onClose, compact = false }:
  { title: string; description: string; children: React.ReactNode; footer?: React.ReactNode; busy: boolean; onClose: () => void; compact?: boolean }) {
  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose(); }}>
    <DialogContent className={`corpus-dialog${compact ? " corpus-dialog-compact" : ""}`} onInteractOutside={event => event.preventDefault()}>
      <DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>{description}</DialogDescription></DialogHeader>
      <div className="corpus-dialog-body">{children}</div>
      {footer && <footer className="corpus-dialog-footer">{footer}</footer>}
    </DialogContent>
  </Dialog>;
}

// Added by ChatGPT: send only changed fields, preserving inactive references and concurrent disjoint edits.
export function MetadataEditor({ task, onClose, onChanged, onForbidden }: { task: AdminTask } & Changed) {
  const [original, setOriginal] = useState<PublicMetadata | null>(null);
  const [draft, setDraft] = useState<PublicMetadata | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [keywords, setKeywords] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setError("");
    void (async () => {
      try {
        const metadata: PublicMetadata = await api.get(`/api/corpus/documents/${task.document_id}/metadata?include_unpublished=true`, { signal: controller.signal, cache: "no-store" });
        const items: Department[] = [];
        for (let after = 0; ; ) {
          const page: Department[] = await api.get(`/api/departments?include_inactive=true&limit=100${after ? `&after_id=${after}` : ""}`, { signal: controller.signal });
          items.push(...page); if (page.length < 100) break; after = page[page.length - 1].id;
        }
        if (!controller.signal.aborted) { setOriginal(metadata); setDraft(metadata); setKeywords((metadata.keywords || []).join("\n")); setDepartments(items); }
      } catch (failure) { if (!controller.signal.aborted) { setError(adminError(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); } }
    })();
    return () => controller.abort();
  }, [task.document_id, retry, onForbidden]);
  const change = (key: keyof PublicMetadata, value: string | number | null) => setDraft(valueBefore => valueBefore && ({ ...valueBefore, [key]: value }));
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (!draft || !original) return;
    const next = { ...draft, keywords: keywords.split("\n").map(word => word.trim()).filter(Boolean) };
    const keys: (keyof PublicMetadata)[] = ["title", "authors_text", "abstract", "department_id", "document_type", "publication_year", "publication_date", "supervisor", "keywords", "doi", "language"];
    const patch = Object.fromEntries(keys.filter(key => JSON.stringify(next[key]) !== JSON.stringify(original[key])).map(key => [key, next[key]]));
    if (!Object.keys(patch).length) { onClose(); return; }
    if (next.keywords.length > 20 || next.keywords.some(word => word.length > 100)) { setError("Use up to 20 keywords, each no longer than 100 characters."); return; }
    if (next.publication_year && next.publication_date && Number(next.publication_date.slice(0, 4)) !== next.publication_year) { setError("Publication year must match the publication date."); return; }
    setBusy(true); setError("");
    try { await api.patch(`/api/corpus/documents/${task.document_id}/metadata`, patch); onChanged(); onClose(); }
    catch (failure) { setError(adminError(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    finally { setBusy(false); }
  };
  return <CorpusDialog title="Edit academic metadata" description={task.file_name} busy={busy} onClose={onClose}
    footer={<><Button variant="outline" disabled={busy} onClick={onClose}>Cancel</Button><Button type="submit" form="corpus-metadata" disabled={busy || !draft}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save changes</Button></>}>
    {error && <p role="alert" className="corpus-error">{error}</p>}
    {!draft ? <><p role="status">{error ? "Metadata unavailable" : "Loading metadata..."}</p>{error && <Button variant="outline" onClick={() => setRetry(value => value + 1)}>Retry</Button>}</> :
      <form id="corpus-metadata" className="corpus-form" onSubmit={save}>
        <label className="corpus-form-wide">Title<input className="public-input" required maxLength={500} value={draft.title} onChange={e => change("title", e.target.value)} /></label>
        <label className="corpus-form-wide">Authors<textarea aria-label="Authors" className="public-input" rows={2} maxLength={8000} value={draft.authors_text || ""} onChange={e => change("authors_text", e.target.value || null)} /></label>
        <label>Department<select aria-label="Department" className="public-input" value={draft.department_id || ""} onChange={e => change("department_id", e.target.value ? Number(e.target.value) : null)}><option value="">Not assigned</option>
          {departments.filter(d => d.is_active || d.id === original?.department_id).map(d => <option key={d.id} value={d.id} disabled={!d.is_active}>{d.name}{d.is_active ? "" : " (inactive)"}</option>)}</select></label>
        <label>Document type<select aria-label="Document type" className="public-input" value={draft.document_type || ""} onChange={e => change("document_type", e.target.value || null)}><option value="">Not assigned</option>{["paper", "thesis", "report", "other"].map(type => <option key={type} value={type}>{type}</option>)}</select></label>
        <label>Publication year<input className="public-input" type="number" min={1000} max={9999} value={draft.publication_year || ""} onChange={e => change("publication_year", e.target.value ? Number(e.target.value) : null)} /></label>
        <label>Publication date<input className="public-input" type="date" min="1000-01-01" max="9999-12-31" value={draft.publication_date || ""} onChange={e => change("publication_date", e.target.value || null)} /></label>
        <label className="corpus-form-wide">Abstract<textarea aria-label="Abstract" className="public-input" rows={4} maxLength={16000} value={draft.abstract || ""} onChange={e => change("abstract", e.target.value || null)} /></label>
        <label>Keywords (one per line)<textarea aria-label="Keywords (one per line)" className="public-input" rows={3} value={keywords} maxLength={2020} onChange={e => setKeywords(e.target.value)} /></label>
        <label>Supervisor<input className="public-input" maxLength={255} value={draft.supervisor || ""} onChange={e => change("supervisor", e.target.value || null)} /></label>
        <label>DOI<input className="public-input" placeholder="10.1234/example" maxLength={255} value={draft.doi || ""} onChange={e => change("doi", e.target.value || null)} /></label>
        <label>Language<input className="public-input" placeholder="en" maxLength={35} pattern="[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*" value={draft.language || ""} onChange={e => change("language", e.target.value || null)} /></label>
      </form>}
  </CorpusDialog>;
}

export type AdminAction = "publish" | "unpublish" | "archive" | "delete" | "retry" | "rename";
const actionLabels = { publish: "Publish document", unpublish: "Unpublish document", archive: "Archive document", delete: "Delete permanently", retry: "Retry processing", rename: "Rename file" };
const actionWarnings = {
  publish: "This document will become visible and queryable by all researchers.",
  unpublish: "This document will be hidden from researchers. It can be published again later.",
  archive: "Archival permanently hides this document. Files are retained until deletion. Archived documents cannot be republished.",
  delete: "The source files, indexed content and bookmarks will be permanently removed. This cannot be undone.",
  retry: "The retained source will be processed again. It will remain unpublished.",
  rename: "File name",
};

// Added by ChatGPT: mutations remain explicit and await server confirmation; errors keep the dialog open.
export function AdminActionDialog({ task, action, onClose, onChanged, onForbidden }: { task: AdminTask; action: AdminAction } & Changed) {
  const [name, setName] = useState(task.file_name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const doc = `/api/corpus/documents/${task.document_id}`;
      if (action === "rename") await api.patch(doc, { file_name: name.trim() });
      else if (action === "delete") await api.delete(task.document_id ? doc : `/api/corpus/tasks/${task.id}`);
      else if (action === "retry") await api.post(`/api/corpus/tasks/${task.id}/retry`);
      else await api.post(`${doc}/${action}`);
      onChanged(); onClose();
    } catch (failure) { setError(adminError(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    finally { setBusy(false); }
  };
  return <CorpusDialog compact title={actionLabels[action]} description={task.title || task.file_name} busy={busy} onClose={onClose}
    footer={<><Button variant="outline" disabled={busy} onClick={onClose}>Cancel</Button><Button form="corpus-action" type="submit" variant={action === "delete" ? "destructive" : "default"} disabled={busy || (action === "rename" && !name.trim())}>{busy && <Loader2 size={16} className="animate-spin" />}{actionLabels[action]}</Button></>}>
    <form id="corpus-action" onSubmit={submit}>{action === "rename" ? <label className="corpus-field">File name<input className="public-input" required maxLength={150} value={name} onChange={e => setName(e.target.value)} /></label> : <p>{actionWarnings[action]}</p>}</form>
    {error && <p role="alert" className="corpus-error">{error}</p>}
  </CorpusDialog>;
}

// Added by ChatGPT: department administration is reference-data editing, never account/role management.
export function DepartmentManager({ onClose, onChanged, onForbidden }: Changed) {
  const [items, setItems] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const [name, setName] = useState(""); const [code, setCode] = useState(""); const [active, setActive] = useState(true);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    void (async () => {
      try {
        const all: Department[] = [];
        for (let after = 0; ; ) {
          const page: Department[] = await api.get(`/api/departments?include_inactive=true&limit=100${after ? `&after_id=${after}` : ""}`, { signal: controller.signal });
          all.push(...page); if (page.length < 100) break; after = page[page.length - 1].id;
        }
        if (!controller.signal.aborted) setItems(all);
      } catch (failure) { if (!controller.signal.aborted) { setError(adminError(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); } }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })(); return () => controller.abort();
  }, [version, onForbidden]);
  const reset = () => { setSelected(null); setName(""); setCode(""); setActive(true); };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const data = { name: name.trim(), code: code.trim().toUpperCase(), is_active: active };
      if (selected === null) await api.post("/api/departments", data); else await api.patch(`/api/departments/${selected}`, data);
      reset(); setVersion(value => value + 1); onChanged();
    } catch (failure) { setError(adminError(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); }
    finally { setBusy(false); }
  };
  return <CorpusDialog title="Departments" description="UAF Research Corpus" busy={busy} onClose={onClose}
    footer={<><Button variant="outline" disabled={busy} onClick={onClose}>Done</Button><Button type="submit" form="corpus-department" disabled={busy || !name.trim() || !code.trim()}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}{selected === null ? "Create department" : "Save department"}</Button></>}>
    {error && <p role="alert" className="corpus-error">{error}<Button variant="outline" onClick={() => setVersion(value => value + 1)}>Refresh departments</Button></p>}
    <div className="corpus-departments">{loading ? <p role="status">Loading departments...</p> : items.length ? items.map(item => <div key={item.id} className="corpus-department-row"><span><strong>{item.name}</strong><small>{item.code} / {item.is_active ? "Active" : "Inactive"}</small></span><button className="icon-button" aria-label={`Edit ${item.name}`} title={`Edit ${item.name}`} disabled={busy} onClick={() => { setSelected(item.id); setName(item.name); setCode(item.code); setActive(item.is_active); }}><Pencil size={16} /></button></div>) : <p>No departments yet.</p>}</div>
    <div className="corpus-form-heading"><h3>{selected === null ? "New department" : "Edit department"}</h3>{selected !== null && <Button variant="outline" disabled={busy} onClick={reset}><Plus size={16} /> New</Button>}</div>
    <form id="corpus-department" className="corpus-form" onSubmit={save}>
      <label>Department name<input className="public-input" maxLength={150} required value={name} onChange={e => setName(e.target.value)} /></label>
      <label>Code<input className="public-input" maxLength={32} pattern="[A-Za-z0-9][A-Za-z0-9_-]*" required value={code} onChange={e => setCode(e.target.value)} /></label>
      <label className="corpus-checkbox"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /> Active</label>
    </form>
  </CorpusDialog>;
}
