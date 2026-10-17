"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, ChevronLeft, ChevronRight, FolderCog, Loader2, LockKeyhole, Plus, RefreshCw, Search, Send, Settings, Trash2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { documentSize, documentStatus, filenameFilters, LibraryCollection, LibraryDocument } from "@/lib/library";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { DocumentUploadSteps } from "./document-upload-steps";
import { LibraryTable } from "./library-table";
import { PublicLibrary } from "./public-library";
import { PublicationRequestDialog } from "./researcher-publication-dialogs";

// Added by ChatGPT: a document-first view over the existing owner-scoped knowledge-base APIs.
export function Library({ knowledgeBaseId }: { knowledgeBaseId?: number }) {
  // Added by ChatGPT: switching scope unmounts private modals/polling instead of sharing document state.
  const [scope, setScope] = useState<"public" | "private">("private");
  const scopeControl = <div className="library-scope" role="group" aria-label="Library access">
    <button aria-pressed={scope === "public"} onClick={() => setScope("public")}>Public</button>
    <button aria-pressed={scope === "private"} onClick={() => setScope("private")}>Private</button>
  </div>;
  return scope === "public" ? <PublicLibrary scopeControl={scopeControl} /> :
    <PrivateLibrary knowledgeBaseId={knowledgeBaseId} scopeControl={scopeControl} />;
}

function PrivateLibrary({ knowledgeBaseId, scopeControl }: { knowledgeBaseId?: number; scopeControl: React.ReactNode }) {
  const [collections, setCollections] = useState<LibraryCollection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<string | null>(null);
  const [processingFilter, setProcessingFilter] = useState("all");
  const [collectionFilter, setCollectionFilter] = useState("all");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [publicationOpen, setPublicationOpen] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<number | null>(null);
  const [manageOpen, setManageOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<LibraryDocument | null>(null);
  const [creating, setCreating] = useState(false);
  const [collectionName, setCollectionName] = useState("My documents");
  const [actionError, setActionError] = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);
  const [visibleDocuments, setDocuments] = useState<LibraryDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [appliedQuery, setAppliedQuery] = useState("");

  // Dashboard shortcut deep-link opens the existing workflow once, then cleans its URL flag.
  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.get("requestPublication") !== "1") return;
    setPublicationOpen(true);
    url.searchParams.delete("requestPublication");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }, []);

  useEffect(() => {
    if (query === appliedQuery) return;
    const timer = setTimeout(() => { setAppliedQuery(query); setPage(0); }, 250);
    return () => clearTimeout(timer);
  }, [query, appliedQuery]);

  // Added by ChatGPT: load every existing collection page; abort on navigation and refresh active jobs.
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setLoading(true);
    const fetchCollections = async () => {
      try {
        let result: LibraryCollection[] = [];
          for (let skip = 0; ; skip += 100) {
            const batch: LibraryCollection[] = await api.get(`/api/knowledge-base?summary=true&skip=${skip}&limit=100`, { signal: controller.signal });
            result = result.concat(batch);
            if (batch.length < 100) break;
          }
        const params = new URLSearchParams({ skip: String(page * 20), limit: "20", search: appliedQuery });
        const kb = knowledgeBaseId ?? (collectionFilter === "all" ? undefined : Number(collectionFilter));
        if (kb !== undefined) params.set("kb_id", String(kb));
        if (filter) params.set("category", filter);
        if (processingFilter !== "all") params.set("status", processingFilter);
        const catalog: { items: LibraryDocument[]; total: number; has_active_tasks: boolean } = await api.get(`/api/knowledge-base/catalog?${params}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setCollections(result);
        setDocuments(catalog.items);
        setTotal(catalog.total);
        if (page > 0 && catalog.items.length === 0) setPage(page - 1);
        setError("");
        if (catalog.has_active_tasks) timer = setTimeout(fetchCollections, 5000);
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : "Unable to load your library.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    void fetchCollections();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [knowledgeBaseId, refresh, page, appliedQuery, filter, processingFilter, collectionFilter]);

  const hasFilters = Boolean(query || filter || processingFilter !== "all");
  const clearFilters = () => { setQuery(""); setAppliedQuery(""); setFilter(null); setProcessingFilter("all"); setPage(0); };

  // Added by ChatGPT: uploads still use the upstream upload/preview/process workflow and collection IDs.
  const openUpload = () => {
    setActionError("");
    setUploadTarget(knowledgeBaseId ?? (collections.length === 1 ? collections[0].id : null));
    setUploadOpen(true);
  };
  const closeUpload = (open: boolean) => {
    setUploadOpen(open);
    if (!open) setRefresh((value) => value + 1);
  };
  const createFirstCollection = async (event: React.FormEvent) => {
    event.preventDefault();
    setCreating(true);
    setActionError("");
    try {
      const collection: LibraryCollection = await api.post("/api/knowledge-base", { name: collectionName.trim(), description: "" });
      setCollections((previous) => [...previous, collection]);
      setUploadTarget(collection.id);
    } catch (failure) {
      setActionError(failure instanceof ApiError ? failure.message : "Could not create collection.");
    } finally { setCreating(false); }
  };
  const deleteCollection = async (collection: LibraryCollection) => {
    if (!window.confirm(`Delete "${collection.name}" and all its documents? This cannot be undone.`)) return;
    setDeleting(collection.id);
    setActionError("");
    try {
      await api.delete(`/api/knowledge-base/${collection.id}`);
      setCollections((previous) => previous.filter((item) => item.id !== collection.id));
      setCollectionFilter("all");
      setPage(0);
      setRefresh(value => value + 1);
    } catch (failure) {
      setActionError(failure instanceof ApiError ? failure.message : "Could not delete collection.");
    } finally { setDeleting(null); }
  };

  const deleteDocument = async (document: LibraryDocument) => {
    if (!window.confirm(`Delete "${document.file_name}"? This cannot be undone.`)) return;
    setDeleting(document.id);
    setActionError("");
    try {
      const item = document.upload_id ? `uploads/${document.upload_id}` : `documents/${document.id}`;
      await api.delete(`/api/knowledge-base/${document.knowledge_base_id}/${item}`);
      setSelectedDocument(null);
      setRefresh(value => value + 1);
    } catch (failure) {
      setActionError(failure instanceof ApiError ? failure.message : "Cleanup incomplete. Retry deletion.");
    } finally { setDeleting(null); }
  };

  return (
    <section className="list-page" aria-label="Private library">
      {/* Added by ChatGPT: the original private workflows stay separate from public corpus management. */}
      <div className="library-heading">
        <div className="library-title"><h1>Library</h1><LockKeyhole size={27} strokeWidth={1.8} aria-label="Private library" /></div>
        {scopeControl}
        <div className="library-heading-actions">
          <Button className="primary-action premium-action" onClick={() => setPublicationOpen(true)} disabled={loading || !!error}>
            <Send size={18} aria-hidden="true" /> Request publication
          </Button>
          <Button className="primary-action premium-action" onClick={openUpload} disabled={loading || !!error}>
            <Plus size={21} strokeWidth={1.6} aria-hidden="true" /> Add Documents
          </Button>
        </div>
      </div>
      <div className="library-search">
        <Search size={23} strokeWidth={1.6} aria-hidden="true" />
        <input type="search" aria-label="Search your library" placeholder="Search your library..." value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      <div className="library-filters" role="group" aria-label="Private library filters">
        {filenameFilters.map(({ label, description }) => <Button key={label} variant={filter === label ? "default" : "outline"} title={description}
          aria-label={description} aria-pressed={filter === label} onClick={() => { setFilter(filter === label ? null : label); setPage(0); }}>{label}</Button>)}
        <select className="library-select" aria-label="Processing status" value={processingFilter} onChange={event => { setProcessingFilter(event.target.value); setPage(0); }}>
          <option value="all">All processing states</option><option value="pending">Pending</option><option value="processing">Processing</option><option value="completed">Ready</option><option value="failed">Failed</option><option value="unknown">Unknown</option>
        </select>
        {hasFilters && <button className="icon-button" aria-label="Clear filters" title="Clear filters" onClick={clearFilters}><X size={18} /></button>}
      </div>

      {/* Added by ChatGPT: real loading, failure, and empty states never substitute sample documents. */}
      {loading ? <div className="library-empty" role="status"><Loader2 className="animate-spin" /><p>Loading your library...</p></div> :
        error ? <div className="library-empty" role="alert"><h2>Library unavailable</h2><p>{error}</p><Button onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={16} /> Retry</Button></div> :
        visibleDocuments.length > 0 ? <LibraryTable documents={visibleDocuments} onSelect={document => { setActionError(""); setSelectedDocument(document); }} /> :
          <div className="library-empty"><BookOpen size={36} strokeWidth={1.4} /><h2>{hasFilters ? "No matching documents" : "No documents yet"}</h2>
            {hasFilters ? <Button variant="outline" onClick={clearFilters}>Clear filters</Button> :
            <Button onClick={openUpload}><Plus size={18} /> Add Documents</Button>}</div>}

      <div className="library-footer">
        <p role="status" aria-live="polite">{loading || error ? "" : `${total} file${total === 1 ? "" : "s"}`}</p>
        <div className="library-tools">
          <button className="icon-button" aria-label="Previous page" disabled={loading || page === 0} onClick={() => setPage(value => value - 1)}><ChevronLeft size={18} /></button>
          <span>Page {page + 1}</span>
          <button className="icon-button" aria-label="Next page" disabled={loading || (page + 1) * 20 >= total} onClick={() => setPage(value => value + 1)}><ChevronRight size={18} /></button>
          {!knowledgeBaseId && collections.length > 1 && <select className="library-select" aria-label="Filter by collection" value={collectionFilter} onChange={(event) => { setCollectionFilter(event.target.value); setPage(0); }}>
            <option value="all">All collections</option>{collections.map((collection) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
          </select>}
          {knowledgeBaseId ? <Link href="/dashboard/knowledge" className="text-sm underline underline-offset-4">All documents</Link> :
            <button className="icon-button" title="Manage collections" aria-label="Manage collections" onClick={() => { setActionError(""); setManageOpen(true); }}><FolderCog size={19} /></button>}
          <button className="icon-button" title="Refresh library" aria-label="Refresh library" disabled={loading} onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={17} /></button>
        </div>
      </div>

      {/* Added by ChatGPT: collection selection keeps uploads in their original private scope. */}
      <Dialog open={uploadOpen} onOpenChange={closeUpload}>
        <DialogContent className="max-w-4xl">
          <DialogHeader><DialogTitle>Add Documents</DialogTitle>
            <DialogDescription>{uploadTarget ? collections.find((collection) => collection.id === uploadTarget)?.name : "Select a private collection."}</DialogDescription>
          </DialogHeader>
          {uploadTarget ? <DocumentUploadSteps key={uploadTarget} knowledgeBaseId={uploadTarget} onComplete={() => closeUpload(false)} /> :
            collections.length ? <div className="grid gap-3">{collections.map((collection) =>
              <button key={collection.id} className="collection-row text-left" onClick={() => setUploadTarget(collection.id)}><BookOpen size={20} /><span className="break-words min-w-0">{collection.name}</span></button>)}</div> :
              <form onSubmit={createFirstCollection} className="space-y-4">
                <label htmlFor="first-collection" className="block text-sm font-medium">Collection name</label>
                <input id="first-collection" className="w-full rounded-lg border p-3 bg-card" value={collectionName} onChange={(event) => setCollectionName(event.target.value)} maxLength={255} required />
                <Button disabled={creating || !collectionName.trim()} type="submit">{creating ? "Creating..." : "Create collection"}</Button>
              </form>}
          {actionError && <p role="alert" className="text-destructive">{actionError}</p>}
        </DialogContent>
      </Dialog>

      <PublicationRequestDialog open={publicationOpen} onOpenChange={setPublicationOpen} onCreated={() => setRefresh(value => value + 1)} />

      {/* Added by ChatGPT: preserve collection creation, management, retrieval testing, and deletion. */}
      <Dialog open={manageOpen} onOpenChange={setManageOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Collections</DialogTitle><DialogDescription>Your private knowledge bases.</DialogDescription></DialogHeader>
          <div>{collections.map((collection) => <div className="collection-row" key={collection.id}>
            <div><Link className="font-medium break-words hover:underline" href={`/dashboard/knowledge/${collection.id}`}>{collection.name}</Link></div>
            <Link href={`/dashboard/knowledge/${collection.id}`} className="icon-button" title={`Open ${collection.name}`} aria-label={`Open ${collection.name}`}><Settings size={18} /></Link>
            <Link href={`/dashboard/test-retrieval/${collection.id}`} className="icon-button" title={`Test retrieval in ${collection.name}`} aria-label={`Test retrieval in ${collection.name}`}><Search size={18} /></Link>
            <button className="icon-button text-destructive" title={`Delete ${collection.name}`} aria-label={`Delete ${collection.name}`} disabled={deleting !== null} onClick={() => deleteCollection(collection)}>{deleting === collection.id ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={18} />}</button>
          </div>)}</div>
          {actionError && <p role="alert" className="text-destructive">{actionError}</p>}
          <Button asChild><Link href="/dashboard/knowledge/new"><Plus size={18} /> New collection</Link></Button>
        </DialogContent>
      </Dialog>

      {/* Added by ChatGPT: document details expose real file data without inventing download endpoints. */}
      <Dialog open={selectedDocument !== null} onOpenChange={(open) => { if (!open) setSelectedDocument(null); }}>
        <DialogContent>
          <DialogHeader><DialogTitle className="break-all pr-5">{selectedDocument?.file_name}</DialogTitle><DialogDescription>Private document</DialogDescription></DialogHeader>
          {selectedDocument && <>
            <dl className="document-details"><dt>Size</dt><dd>{documentSize(selectedDocument.file_size)}</dd><dt>Status</dt><dd>{documentStatus(selectedDocument).label}</dd><dt>Collection</dt><dd>{collections.find((collection) => collection.id === selectedDocument.knowledge_base_id)?.name}</dd></dl>
            <Button asChild><Link href={`/dashboard/knowledge/${selectedDocument.knowledge_base_id}`} onClick={() => setSelectedDocument(null)}>Open collection</Link></Button>
            {!selectedDocument.upload_id && <Button asChild variant="outline"><a href={`/api/knowledge-base/${selectedDocument.knowledge_base_id}/documents/${selectedDocument.id}/content?inline=true`} target="_blank" rel="noopener noreferrer">Open document</a></Button>}
            {selectedDocument.upload_id && <p className="text-sm text-muted-foreground">This upload has not produced a document yet. If processing failed, delete it and upload the file again.</p>}
            <Button variant="destructive" disabled={deleting !== null || ["pending", "processing"].includes(documentStatus(selectedDocument).status) && !selectedDocument.upload_id} onClick={() => deleteDocument(selectedDocument)}>
              <Trash2 size={16} /> {deleting !== null ? "Deleting..." : "Delete file"}
            </Button>
            {actionError && <p role="alert" className="text-destructive">{actionError}</p>}
          </>}
        </DialogContent>
      </Dialog>
    </section>
  );
}
