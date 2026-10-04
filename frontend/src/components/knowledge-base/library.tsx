"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BookOpen, FolderCog, Loader2, LockKeyhole, Plus, RefreshCw, Search, Settings, Trash2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { documentSize, documentStatus, filenameFilters, LibraryCollection, LibraryDocument } from "@/lib/library";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { DocumentUploadSteps } from "./document-upload-steps";
import { LibraryTable } from "./library-table";
import { PublicLibrary } from "./public-library";

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
  const [uploadTarget, setUploadTarget] = useState<number | null>(null);
  const [manageOpen, setManageOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<LibraryDocument | null>(null);
  const [creating, setCreating] = useState(false);
  const [collectionName, setCollectionName] = useState("My documents");
  const [actionError, setActionError] = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);

  // Added by ChatGPT: load every existing collection page; abort on navigation and refresh active jobs.
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setLoading(true);
    const fetchCollections = async () => {
      try {
        let result: LibraryCollection[] = [];
        if (knowledgeBaseId !== undefined) {
          result = [await api.get(`/api/knowledge-base/${knowledgeBaseId}`, { signal: controller.signal })];
        } else {
          for (let skip = 0; ; skip += 100) {
            const page: LibraryCollection[] = await api.get(`/api/knowledge-base?skip=${skip}&limit=100`, { signal: controller.signal });
            result = result.concat(page);
            if (page.length < 100) break;
          }
        }
        if (controller.signal.aborted) return;
        setCollections(result);
        setError("");
        const active = result.some((collection) => collection.documents.some((document) =>
          ["pending", "processing"].includes(documentStatus(document).status)));
        if (active) timer = setTimeout(fetchCollections, 5000);
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : "Unable to load your library.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    void fetchCollections();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [knowledgeBaseId, refresh]);

  const documents = useMemo(() => collections
    .filter((collection) => collectionFilter === "all" || String(collection.id) === collectionFilter)
    .flatMap((collection) => collection.documents), [collections, collectionFilter]);
  const visibleDocuments = documents.filter((document) => {
    const matchesSearch = document.file_name.toLowerCase().includes(query.trim().toLowerCase());
    const shortcut = filenameFilters.find((item) => item.label === filter);
    return matchesSearch && (!shortcut || shortcut.pattern.test(document.file_name)) &&
      (processingFilter === "all" || documentStatus(document).status === processingFilter);
  });
  const hasFilters = Boolean(query || filter || processingFilter !== "all");
  const clearFilters = () => { setQuery(""); setFilter(null); setProcessingFilter("all"); };

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
    } catch (failure) {
      setActionError(failure instanceof ApiError ? failure.message : "Could not delete collection.");
    } finally { setDeleting(null); }
  };

  return (
    <section className="list-page" aria-label="Private library">
      {/* Added by ChatGPT: the original private workflows stay separate from public corpus management. */}
      <div className="library-heading">
        <div className="library-title"><h1>Library</h1><LockKeyhole size={27} strokeWidth={1.8} aria-label="Private library" /></div>
        {scopeControl}
        <Button className="library-upload-action primary-action premium-action" onClick={openUpload} disabled={loading || !!error}>
          <Plus size={21} strokeWidth={1.6} aria-hidden="true" /> Add Documents
        </Button>
      </div>
      <div className="library-search">
        <Search size={23} strokeWidth={1.6} aria-hidden="true" />
        <input type="search" aria-label="Search your library" placeholder="Search your library..." value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      <div className="library-filters" role="group" aria-label="Private library filters">
        {filenameFilters.map(({ label, description }) => <Button key={label} variant={filter === label ? "default" : "outline"} title={description}
          aria-label={description} aria-pressed={filter === label} onClick={() => setFilter(filter === label ? null : label)}>{label}</Button>)}
        <select className="library-select" aria-label="Processing status" value={processingFilter} onChange={event => setProcessingFilter(event.target.value)}>
          <option value="all">All processing states</option><option value="pending">Pending</option><option value="processing">Processing</option><option value="completed">Ready</option><option value="failed">Failed</option><option value="unknown">Unknown</option>
        </select>
        {hasFilters && <button className="icon-button" aria-label="Clear filters" title="Clear filters" onClick={clearFilters}><X size={18} /></button>}
      </div>

      {/* Added by ChatGPT: real loading, failure, and empty states never substitute sample documents. */}
      {loading ? <div className="library-empty" role="status"><Loader2 className="animate-spin" /><p>Loading your library...</p></div> :
        error ? <div className="library-empty" role="alert"><h2>Library unavailable</h2><p>{error}</p><Button onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={16} /> Retry</Button></div> :
        visibleDocuments.length > 0 ? <LibraryTable documents={visibleDocuments} onSelect={setSelectedDocument} /> :
          <div className="library-empty"><BookOpen size={36} strokeWidth={1.4} /><h2>{hasFilters ? "No matching documents" : "No documents yet"}</h2>
            {hasFilters ? <Button variant="outline" onClick={clearFilters}>Clear filters</Button> :
            <Button onClick={openUpload}><Plus size={18} /> Add Documents</Button>}</div>}

      <div className="library-footer">
        <p role="status" aria-live="polite">{loading || error ? "" : `${visibleDocuments.length} document${visibleDocuments.length === 1 ? "" : "s"}`}</p>
        <div className="library-tools">
          {!knowledgeBaseId && collections.length > 1 && <select className="library-select" aria-label="Filter by collection" value={collectionFilter} onChange={(event) => setCollectionFilter(event.target.value)}>
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

      {/* Added by ChatGPT: preserve collection creation, management, retrieval testing, and deletion. */}
      <Dialog open={manageOpen} onOpenChange={setManageOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Collections</DialogTitle><DialogDescription>Your private knowledge bases.</DialogDescription></DialogHeader>
          <div>{collections.map((collection) => <div className="collection-row" key={collection.id}>
            <div><Link className="font-medium break-words hover:underline" href={`/dashboard/knowledge/${collection.id}`}>{collection.name}</Link><p>{collection.documents.length} documents</p></div>
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
          </>}
        </DialogContent>
      </Dialog>
    </section>
  );
}
