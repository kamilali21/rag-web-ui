"use client";

import { useEffect, useState } from "react";
import { Loader2, Send } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Department } from "@/lib/public-library";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type EligibleDocument = { id: number; file_name: string; file_size: number };
type Draft = { title: string; authors_text: string; abstract: string; department_id: string; document_type: string;
  publication_year: string; publication_date: string; supervisor: string; keywords: string; doi: string; language: string };
const cleanDraft: Draft = { title: "", authors_text: "", abstract: "", department_id: "", document_type: "paper",
  publication_year: "", publication_date: "", supervisor: "", keywords: "", doi: "", language: "" };
const message = (error: unknown) => error instanceof ApiError ? error.message : "Request failed. Please try again.";

export function PublicationRequestDialog({ open, onOpenChange, onCreated }: {
  open: boolean; onOpenChange: (open: boolean) => void; onCreated: () => void;
}) {
  const [documents, setDocuments] = useState<EligibleDocument[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [profileReady, setProfileReady] = useState<boolean | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [draft, setDraft] = useState<Draft>(cleanDraft);
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController(); setLoading(true); setError(""); setDone(false);
    void (async () => {
      try {
        const [files, profile, departmentsPage]: [EligibleDocument[], any, Department[]] = await Promise.all([
          api.get("/api/researcher/eligible-documents", { signal: controller.signal, cache: "no-store" }),
          api.get("/api/researcher/profile", { signal: controller.signal, cache: "no-store" }),
          api.get("/api/departments?limit=100", { signal: controller.signal, cache: "no-store" }),
        ]);
        if (controller.signal.aborted) return;
        setDocuments(files); setDepartments(departmentsPage); setProfileReady(Boolean(profile));
        setSourceId(files[0] ? String(files[0].id) : "");
        setDraft({ ...cleanDraft, department_id: profile?.department_id ? String(profile.department_id) : "" });
      } catch (failure) { if (!controller.signal.aborted) setError(message(failure)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [open]);

  const update = (key: keyof Draft, value: string) => setDraft(previous => ({ ...previous, [key]: value }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    const metadata = {
      title: draft.title.trim(), authors_text: draft.authors_text.trim(), department_id: Number(draft.department_id),
      document_type: draft.document_type, abstract: draft.abstract.trim() || null,
      publication_year: draft.publication_year ? Number(draft.publication_year) : null,
      publication_date: draft.publication_date || null, supervisor: draft.supervisor.trim() || null,
      keywords: draft.keywords.split(",").map(value => value.trim()).filter(Boolean),
      doi: draft.doi.trim() || null, language: draft.language.trim() || null,
    };
    if (metadata.keywords.length > 20 || metadata.keywords.some(word => word.length > 100)) {
      setError("Use up to 20 keywords, each no longer than 100 characters."); setBusy(false); return;
    }
    try {
      await api.post("/api/researcher/requests", { source_document_id: Number(sourceId), metadata, public_card_consent: consent });
      setDone(true); onCreated();
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  };

  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="researcher-dialog">
    <DialogHeader><DialogTitle>Request publication</DialogTitle><DialogDescription>Submit one ready private document for admin review. Your original remains private.</DialogDescription></DialogHeader>
    {loading ? <p role="status">Loading your ready documents...</p> : error && !documents.length && profileReady === null ? <p role="alert">{error}</p> :
      done ? <div className="space-y-3"><p role="status">Your request was sent for review. Its status will appear on your Profile page.</p><Button onClick={() => onOpenChange(false)}>Done</Button></div> :
      profileReady === false ? <div className="space-y-3"><p>Complete your researcher profile before requesting publication.</p><Button asChild><a href="/dashboard/profile">Open Profile</a></Button></div> :
      documents.length === 0 ? <p role="status">No fully processed private documents are ready to submit yet.</p> :
      <form className="corpus-form researcher-request-form" onSubmit={submit}>
        <label className="corpus-form-wide">Private document<select className="public-input" value={sourceId} onChange={event => setSourceId(event.target.value)} required>
          {documents.map(document => <option key={document.id} value={document.id}>{document.file_name}</option>)}
        </select></label>
        <label className="corpus-form-wide">Title<input className="public-input" maxLength={500} required value={draft.title} onChange={event => update("title", event.target.value)} /></label>
        <label className="corpus-form-wide">Author(s)<textarea className="public-input" rows={2} maxLength={8000} required value={draft.authors_text} onChange={event => update("authors_text", event.target.value)} /></label>
        <label>Department<select className="public-input" value={draft.department_id} onChange={event => update("department_id", event.target.value)} required>
          <option value="">Choose department</option>{departments.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Document type<select className="public-input" value={draft.document_type} onChange={event => update("document_type", event.target.value)} required>
          {[["paper", "Paper"], ["thesis", "Thesis"], ["report", "Report"], ["other", "Other"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>Publication year<input className="public-input" type="number" min={1000} max={9999} value={draft.publication_year} onChange={event => update("publication_year", event.target.value)} /></label>
        <label>Publication date<input className="public-input" type="date" value={draft.publication_date} onChange={event => update("publication_date", event.target.value)} /></label>
        <label className="corpus-form-wide">Abstract<textarea className="public-input" rows={3} maxLength={16000} value={draft.abstract} onChange={event => update("abstract", event.target.value)} /></label>
        <label>Keywords<input className="public-input" placeholder="Comma separated" maxLength={2020} value={draft.keywords} onChange={event => update("keywords", event.target.value)} /></label>
        <label>Supervisor<input className="public-input" maxLength={255} value={draft.supervisor} onChange={event => update("supervisor", event.target.value)} /></label>
        <label>DOI<input className="public-input" maxLength={255} placeholder="10.1234/example" value={draft.doi} onChange={event => update("doi", event.target.value)} /></label>
        <label>Language<input className="public-input" maxLength={35} placeholder="en" value={draft.language} onChange={event => update("language", event.target.value)} /></label>
        <label className="corpus-form-wide corpus-checkbox researcher-consent"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />
          <span>Allow this paper to display my name, department, degree, research area and profile photo (if added). Ag number, class and section are never shown publicly.</span></label>
        {error && <p className="corpus-error corpus-form-wide" role="alert">{error}</p>}
        <div className="corpus-form-wide flex justify-end gap-2"><Button variant="outline" type="button" disabled={busy} onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" disabled={busy || !sourceId}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Send request</Button></div>
      </form>}
  </DialogContent></Dialog>;
}
