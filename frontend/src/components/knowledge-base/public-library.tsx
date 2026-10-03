"use client";

import { useCallback, useEffect, useState } from "react";
import { Bookmark, BookOpen, ChevronLeft, ChevronRight, File, Globe, Loader2, MessageSquare, Plus, RefreshCw, Search, Settings2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { documentSize } from "@/lib/library";
import { Department, emptyPublicFilters, PUBLIC_PAGE_SIZE, PublicDocument, publicDocumentsUrl } from "@/lib/public-library";
import { Button } from "@/components/ui/button";
import { PublicDocumentDetails, PublicQuery, PublicUpload } from "./public-library-dialogs";
import { CorpusManager } from "./corpus-manager";

// Added by ChatGPT: published server-side catalog; no private KB IDs or private upload components enter this view.
export function PublicLibrary({ scopeControl }: { scopeControl: React.ReactNode }) {
  const [context, setContext] = useState<{ name: string; canUpload: boolean; departments: Department[] } | null>(null);
  const [draft, setDraft] = useState(emptyPublicFilters);
  const [filters, setFilters] = useState(emptyPublicFilters);
  const [cursors, setCursors] = useState<(number | null)[]>([null]);
  const [documents, setDocuments] = useState<PublicDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [contextError, setContextError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [queryOpen, setQueryOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [permissionNotice, setPermissionNotice] = useState("");
  const [bookmarking, setBookmarking] = useState<number | null>(null);
  const [bookmarkError, setBookmarkError] = useState("");
  const [listVersion, setListVersion] = useState(0);
  const [managing, setManaging] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setContextError("");
    void (async () => {
      try {
        const [corpus, user] = await Promise.all([
          api.get("/api/corpus", { signal: controller.signal, cache: "no-store" }),
          api.get("/api/auth/me", { signal: controller.signal, cache: "no-store" }),
        ]);
        const departments: Department[] = [];
        for (let after = 0; ; ) {
          const page: Department[] = await api.get(`/api/departments?limit=100${after ? `&after_id=${after}` : ""}`, { signal: controller.signal });
          departments.push(...page);
          if (page.length < 100) break;
          after = page[page.length - 1].id;
        }
        if (!controller.signal.aborted) setContext({ name: corpus.name, canUpload: user.roles?.includes("admin") === true, departments });
      } catch (failure) { if (!controller.signal.aborted) setContextError(failure instanceof ApiError ? failure.message : "The public corpus is unavailable."); }
    })();
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    if (!context) return;
    const controller = new AbortController();
    setLoading(true); setError(""); setDocuments([]);
    api.get(publicDocumentsUrl(filters, cursors[cursors.length - 1]), { signal: controller.signal, cache: "no-store" })
      .then(data => { if (!controller.signal.aborted) setDocuments(data); })
      .catch(failure => { if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : "Unable to load public documents."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [context, filters, cursors, listVersion]);

  // Added by ChatGPT: saved references belong to the session user; private/public source identity never changes.
  const toggleBookmark = async (document: PublicDocument) => {
    setBookmarking(document.id); setBookmarkError("");
    try {
      const path = `/api/corpus/documents/${document.id}/bookmark`;
      if (document.is_bookmarked) await api.delete(path); else await api.post(path);
      if (filters.bookmarked) setListVersion(value => value + 1);
      else setDocuments(values => values.map(row => row.id === document.id ? { ...row, is_bookmarked: !document.is_bookmarked } : row));
    } catch (failure) { setBookmarkError(failure instanceof ApiError ? failure.message : "Could not update bookmark."); }
    finally { setBookmarking(null); }
  };

  const forbidden = useCallback(() => {
    setContext(value => value && { ...value, canUpload: false });
    setPermissionNotice("Your public upload permission is no longer available.");
    setUploadOpen(false);
    setManaging(false);
  }, []);
  const clearFilters = () => { setDraft(emptyPublicFilters); setFilters(emptyPublicFilters); setCursors([null]); };
  const visible = documents.slice(0, PUBLIC_PAGE_SIZE);
  const failure = contextError || error;
  const busy = !context || loading;

  // Added by ChatGPT: management is a separate admin surface; Public remains published-only.
  if (managing && context?.canUpload) return <CorpusManager onBack={() => { setManaging(false); setRefresh(value => value + 1); }} onForbidden={forbidden} />;

  return <section className="list-page" aria-label="Public library">
    <div className="library-heading">
      <div className="library-title"><h1>Library</h1><Globe size={27} strokeWidth={1.8} aria-label="Public library" /></div>
      {scopeControl}
      <div className="library-heading-actions">
        {context?.canUpload && <button className="icon-button" title="Manage corpus" aria-label="Manage corpus" onClick={() => setManaging(true)}><Settings2 size={21} /></button>}
        <Button className="primary-action premium-action" onClick={() => setQueryOpen(true)} disabled={!context || !!contextError}><MessageSquare size={18} /> Query corpus</Button>
        {context?.canUpload && <Button className="primary-action premium-action" onClick={() => setUploadOpen(true)} disabled={!!contextError}><Plus size={20} /> Add Documents</Button>}
      </div>
    </div>
    <h2 className="public-corpus-name">{context?.name || "UAF Research Corpus"}</h2>
    <form className="public-library-filters" onSubmit={event => { event.preventDefault(); setFilters({ ...draft }); setCursors([null]); }}>
      <div className="library-search"><Search size={23} strokeWidth={1.6} aria-hidden="true" />
        <input type="search" aria-label="Search public library" placeholder="Search titles, authors, abstracts..." maxLength={200} value={draft.search} onChange={event => setDraft({ ...draft, search: event.target.value })} />
      </div>
      <div className="public-filters">
        <div className="public-filter-fields">
          <label>Author<input className="public-input" value={draft.author} maxLength={200} onChange={event => setDraft({ ...draft, author: event.target.value })} /></label>
          <label>Department<select className="public-input" value={draft.department_id} onChange={event => setDraft({ ...draft, department_id: event.target.value })}>
          <option value="">All departments</option>{context?.departments.map(department => <option key={department.id} value={department.id}>{department.name}</option>)}
          </select></label>
          <fieldset className="public-year-range"><legend>Year range</legend><div className="public-year-inputs">
            <input aria-label="From year" placeholder="From" className="public-input" type="number" min={1000} max={9999} value={draft.year_from} onChange={event => setDraft({ ...draft, year_from: event.target.value })} />
            <span aria-hidden="true">–</span>
            <input aria-label="To year" placeholder="To" className="public-input" type="number" min={draft.year_from || 1000} max={9999} value={draft.year_to} onChange={event => setDraft({ ...draft, year_to: event.target.value })} />
          </div></fieldset>
          <label>Type<select className="public-input" value={draft.document_type} onChange={event => setDraft({ ...draft, document_type: event.target.value })}>
          <option value="">All types</option>{["paper", "thesis", "report", "other"].map(type => <option key={type} value={type}>{type[0].toUpperCase() + type.slice(1)}</option>)}
          </select></label>
          <label className="public-saved-filter"><input type="checkbox" checked={draft.bookmarked === "true"} onChange={event => setDraft({ ...draft, bookmarked: event.target.checked ? "true" : "" })} /> Saved only</label>
        </div>
        <div className="public-filter-actions">
          <Button type="submit" disabled={!context}><Search size={16} /> Search</Button>
          <Button variant="outline" type="button" title="Clear public filters" aria-label="Clear public filters" onClick={clearFilters}><X size={16} /> Clear</Button>
        </div>
      </div>
    </form>
    {permissionNotice && <p role="alert">{permissionNotice}</p>}
    {bookmarkError && <p role="alert">{bookmarkError}</p>}
    {failure ? <div className="library-empty" role="alert"><h2>Public library unavailable</h2><p>{failure}</p><Button onClick={() => setRefresh(value => value + 1)}><RefreshCw size={16} /> Retry</Button></div> :
      busy ? <div className="library-empty" role="status"><Loader2 className="animate-spin" /><p>Loading public research...</p></div> :
      visible.length ? <table className="library-table public-library-table" aria-label="Public research documents">
        <colgroup><col style={{ width: "43%" }} /><col style={{ width: "22%" }} /><col style={{ width: "25%" }} /><col style={{ width: "10%" }} /></colgroup>
        <thead><tr><th scope="col">Title</th><th scope="col">Author</th><th scope="col">Department</th><th scope="col">Year</th></tr></thead>
        <tbody>{visible.map(document => <tr key={document.id}>
          <td><div className="public-document-cell">
            <span className="document-icon" aria-hidden="true"><File strokeWidth={1.6} /><span>{document.file_name.split(".").pop()?.slice(0, 4)}</span></span>
            <div className="public-document-summary"><div className="public-document-title">
            <button className="document-name" title={document.title} aria-label={`Details for ${document.title}`} onClick={() => setSelectedId(document.id)}><span className="document-label">{document.title}</span></button>
            <button className="icon-button" aria-label={`${document.is_bookmarked ? "Remove bookmark for" : "Bookmark"} ${document.title}`}
            title={document.is_bookmarked ? "Remove bookmark" : "Bookmark document"} aria-pressed={document.is_bookmarked}
            disabled={bookmarking !== null} onClick={() => void toggleBookmark(document)}>
            {bookmarking === document.id ? <Loader2 size={18} className="animate-spin" /> : <Bookmark size={18} fill={document.is_bookmarked ? "currentColor" : "none"} />}
          </button></div><span className="public-document-kind">{document.document_type || "Document"} / {documentSize(document.file_size)}</span></div></div></td>
          <td><span className={`public-table-value${document.authors_text ? "" : " text-muted-foreground"}`}>{document.authors_text || "Not recorded"}</span></td>
          <td><span className={`public-table-value${document.department_name ? "" : " text-muted-foreground"}`}>{document.department_name || "Not assigned"}</span></td>
          <td><span className={document.publication_year ? undefined : "text-muted-foreground"}>{document.publication_year || "Not recorded"}</span></td>
        </tr>)}</tbody>
      </table> : <div className="library-empty"><BookOpen size={36} strokeWidth={1.4} /><h2>{cursors.length > 1 ? "No documents on this page" : Object.values(filters).some(Boolean) ? "No matching research" : "No published research yet"}</h2>
        {Object.values(filters).some(Boolean) && <Button variant="outline" onClick={clearFilters}>Clear filters</Button>}</div>}
    <div className="library-footer">
      <p role="status">{!busy && !failure ? `${visible.length} document${visible.length === 1 ? "" : "s"} on this page` : ""}</p>
      <div className="library-tools"><nav className="library-tools" aria-label="Public library pages">
        <button className="icon-button" title="Previous page" aria-label="Previous page" disabled={busy || !!failure || cursors.length === 1} onClick={() => setCursors(values => values.slice(0, -1))}><ChevronLeft size={20} /></button>
        <span className="text-sm">Page {cursors.length}</span>
        <button className="icon-button" title="Next page" aria-label="Next page" disabled={busy || !!failure || documents.length <= PUBLIC_PAGE_SIZE} onClick={() => setCursors(values => [...values, visible[visible.length - 1].id])}><ChevronRight size={20} /></button>
      </nav>
        <button className="icon-button" title="Refresh public library" aria-label="Refresh public library" disabled={busy && !failure} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={17} /></button>
      </div>
    </div>
    <PublicDocumentDetails id={selectedId} onClose={() => setSelectedId(null)} />
    <PublicQuery open={queryOpen} onOpenChange={setQueryOpen} onSelect={id => { setQueryOpen(false); setSelectedId(id); }} />
    {context?.canUpload && <PublicUpload open={uploadOpen} onOpenChange={setUploadOpen} onForbidden={forbidden} />}
  </section>;
}
