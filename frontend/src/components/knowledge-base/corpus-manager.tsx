"use client";

import { useEffect, useState } from "react";
import * as Menu from "@radix-ui/react-dropdown-menu";
import { ArrowLeft, Building2, ChevronLeft, ChevronRight, MoreHorizontal, Plus, RefreshCw, Search, X, Eye, Pencil, Archive, Trash2, Upload, RotateCcw, FilePenLine } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PublicDocumentDetails, PublicUpload } from "./public-library-dialogs";
import { AdminAction, AdminActionDialog, AdminTask, adminError, DepartmentManager, MetadataEditor } from "./corpus-admin-dialogs";

const emptyFilters = { search: "", status: "", publication_status: "" };

// Added by ChatGPT: recoverable admin inbox uses existing task/document identities and lifecycle APIs.
export function CorpusManager({ onBack, onForbidden }: { onBack: () => void; onForbidden: () => void }) {
  const [draft, setDraft] = useState(emptyFilters); const [filters, setFilters] = useState(emptyFilters);
  const [cursors, setCursors] = useState<(number | null)[]>([null]);
  const [tasks, setTasks] = useState<AdminTask[]>([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(""); const [version, setVersion] = useState(0);
  const [upload, setUpload] = useState(false); const [departments, setDepartments] = useState(false);
  const [view, setView] = useState<number | null>(null); const [edit, setEdit] = useState<AdminTask | null>(null);
  const [action, setAction] = useState<{ task: AdminTask; type: AdminAction } | null>(null);
  const refresh = () => setVersion(value => value + 1);
  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const params = new URLSearchParams({ limit: "21" });
    Object.entries(filters).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()); });
    const cursor = cursors[cursors.length - 1]; if (cursor) params.set("before_id", String(cursor));
    setLoading(true); setError(""); setTasks([]);
    const load = async () => {
      try {
        const rows: AdminTask[] = await api.get(`/api/corpus/tasks?${params}`, { signal: controller.signal, cache: "no-store" });
        if (controller.signal.aborted) return;
        setTasks(rows); setError("");
        if (rows.some(task => ["pending", "processing"].includes(task.status))) timer = setTimeout(load, 3000);
      } catch (failure) { if (!controller.signal.aborted) { setError(adminError(failure)); if (failure instanceof ApiError && failure.status === 403) onForbidden(); } }
      finally { if (!controller.signal.aborted) setLoading(false); }
    };
    void load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [filters, cursors, version, onForbidden]);
  const rows = tasks.slice(0, 20);
  return <section aria-label="Corpus management">
    <div className="corpus-manager-heading"><div><button className="corpus-back" onClick={onBack}><ArrowLeft size={17} /> Public library</button><h1>Manage corpus</h1><p>UAF Research Corpus</p></div>
      <div className="corpus-toolbar"><Button variant="outline" onClick={() => setDepartments(true)}><Building2 size={17} /> Departments</Button><button className="primary-action premium-action" onClick={() => setUpload(true)}><Plus size={18} /> Add Documents</button></div>
    </div>
    <form className="corpus-filters" onSubmit={event => { event.preventDefault(); setFilters({ ...draft }); setCursors([null]); }}>
      <label>Title or filename<input type="search" className="public-input" maxLength={200} value={draft.search} onChange={e => setDraft({ ...draft, search: e.target.value })} /></label>
      <label>Processing<select aria-label="Processing" className="public-input" value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value })}><option value="">All states</option>{["pending", "processing", "completed", "failed"].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <label>Publication<select aria-label="Publication" className="public-input" value={draft.publication_status} onChange={e => setDraft({ ...draft, publication_status: e.target.value })}><option value="">All states</option>{["draft", "published", "archived"].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <Button type="submit"><Search size={16} /> Search</Button><button className="icon-button" type="button" title="Clear management filters" aria-label="Clear management filters" onClick={() => { setDraft(emptyFilters); setFilters(emptyFilters); setCursors([null]); }}><X size={18} /></button>
    </form>
    {error ? <div className="library-empty" role="alert"><h2>Management unavailable</h2><p>{error}</p><Button onClick={refresh}>Retry</Button></div> : loading ? <p role="status" className="corpus-loading">Loading corpus uploads...</p> : !rows.length ? <div className="library-empty"><h2>No uploads found</h2></div> :
      <table className="corpus-table" aria-label="Corpus uploads"><thead><tr><th>Document</th><th>Processing</th><th>Publication</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{rows.map(task => {
        const active = ["pending", "processing"].includes(task.status);
        const editable = task.document_id !== null && task.status === "completed" && task.publication_status !== "archived";
        const command = (type: AdminAction) => setAction({ task, type });
        return <tr key={task.id}><td><strong>{task.title || task.file_name}</strong>{task.title && task.title !== task.file_name && <span>{task.file_name}</span>}<small>Task #{task.id} / {new Date(task.created_at).toLocaleDateString()}</small></td>
          <td><span className={`corpus-status corpus-status-${task.status}`}>{task.status === "completed" ? "Ready" : task.status}</span>{task.error_message && <small>{task.error_message}</small>}</td>
          <td><span className={`corpus-status corpus-status-${task.publication_status}`}>{task.publication_status}</span></td>
          <td><Menu.Root><Menu.Trigger asChild><button className="icon-button" aria-label={`Actions for ${task.file_name}`} title="Document actions"><MoreHorizontal size={20} /></button></Menu.Trigger>
            <Menu.Portal><Menu.Content className="corpus-menu" sideOffset={4} align="end">
              {task.document_id !== null && <Menu.Item onSelect={() => setView(task.document_id)}><Eye size={16} /> View document</Menu.Item>}
              {editable && <><Menu.Item onSelect={() => setEdit(task)}><Pencil size={16} /> Edit metadata</Menu.Item><Menu.Item onSelect={() => command("rename")}><FilePenLine size={16} /> Rename file</Menu.Item>
                <Menu.Item onSelect={() => command(task.publication_status === "published" ? "unpublish" : "publish")}><Upload size={16} />{task.publication_status === "published" ? "Unpublish document" : "Publish document"}</Menu.Item></>}
              {task.status === "failed" && task.upload_id !== null && task.publication_status !== "archived" && <Menu.Item onSelect={() => command("retry")}><RotateCcw size={16} /> Retry processing</Menu.Item>}
              {!active && task.document_id !== null && task.publication_status !== "archived" && <Menu.Item onSelect={() => command("archive")}><Archive size={16} /> Archive document</Menu.Item>}
              {!active && (task.document_id !== null || task.status === "failed") && <><Menu.Separator /><Menu.Item className="corpus-danger" onSelect={() => command("delete")}><Trash2 size={16} /> Delete permanently</Menu.Item></>}
            </Menu.Content></Menu.Portal></Menu.Root></td></tr>;
      })}</tbody></table>}
    <div className="library-footer"><p role="status">{!loading && !error ? `${rows.length} uploads on this page` : ""}</p><nav className="library-tools" aria-label="Management pages">
      <button className="icon-button" title="Previous page" aria-label="Previous page" disabled={loading || !!error || cursors.length === 1} onClick={() => setCursors(values => values.slice(0, -1))}><ChevronLeft size={20} /></button><span>Page {cursors.length}</span>
      <button className="icon-button" title="Next page" aria-label="Next page" disabled={loading || !!error || tasks.length <= 20} onClick={() => setCursors(values => [...values, rows[19].id])}><ChevronRight size={20} /></button>
      <button className="icon-button" title="Refresh management" aria-label="Refresh management" disabled={loading} onClick={refresh}><RefreshCw size={17} /></button></nav></div>
    <PublicUpload open={upload} onOpenChange={open => { setUpload(open); if (!open) refresh(); }} onForbidden={onForbidden} />
    <PublicDocumentDetails id={view} onClose={() => setView(null)} manage />
    {edit && <MetadataEditor key={edit.id} task={edit} onClose={() => setEdit(null)} onChanged={refresh} onForbidden={onForbidden} />}
    {action && <AdminActionDialog key={`${action.task.id}-${action.type}`} task={action.task} action={action.type} onClose={() => setAction(null)} onChanged={refresh} onForbidden={onForbidden} />}
    {departments && <DepartmentManager onClose={() => setDepartments(false)} onChanged={refresh} onForbidden={onForbidden} />}
  </section>;
}
