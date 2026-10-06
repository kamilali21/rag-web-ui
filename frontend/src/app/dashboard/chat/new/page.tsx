"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { api, ApiError } from "@/lib/api";

type Scope = "public" | "private" | "both";
interface KnowledgeBase { id: number; name: string; description?: string }

export default function NewChatPage() {
  const router = useRouter();
  const [scope, setScope] = useState<Scope>("private");
  const [collections, setCollections] = useState<KnowledgeBase[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("scope");
    if (requested === "public" || requested === "private" || requested === "both") setScope(requested);
    let active = true;
    api.get("/api/knowledge-base").then((rows: KnowledgeBase[]) => {
      if (active) { setCollections(rows); setSelected(rows.map(row => row.id)); }
    }).catch(() => { if (active) setError("Private collections could not be loaded. Please refresh to retry."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim() || (scope === "private" && !selected.length)) return;
    setSubmitting(true); setError("");
    try {
      const chat = await api.post("/api/chat/", {
        title: title.trim(), source_scope: scope, knowledge_base_ids: scope === "public" ? [] : selected,
      });
      router.push(`/dashboard/chat/${chat.id}`);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Conversation could not be started. Please try again.");
    } finally { setSubmitting(false); }
  };

  return <DashboardLayout><div className="max-w-2xl mx-auto space-y-6">
    <header><h1 className="text-3xl font-bold">Research Assistant</h1>
      <p className="text-muted-foreground mt-2">Choose your sources for a new conversation. Answers include inspectable citations.</p></header>
    <form onSubmit={submit} className="space-y-6">
      <div className="space-y-2"><label htmlFor="chat-title" className="block font-medium">Conversation title</label>
        <input id="chat-title" className="public-input w-full" required maxLength={255} value={title}
          onChange={event => setTitle(event.target.value)} placeholder="What are you researching?" /></div>
      <fieldset className="space-y-2"><legend className="font-medium">Sources</legend>
        <div className="flex flex-wrap gap-3">{(["public", "private", "both"] as Scope[]).map(value => <label key={value}
          className={`flex items-center gap-2 rounded-lg border px-4 py-3 cursor-pointer ${scope === value ? "border-primary bg-primary/5" : ""}`}>
          <input type="radio" name="source-scope" value={value} checked={scope === value} onChange={() => setScope(value)} />
          {value === "both" ? "Both" : value === "public" ? "Public" : "Private"}
        </label>)}</div>
        <p className="text-sm text-muted-foreground">{scope === "public" ? "Published UAF corpus documents." : scope === "both" ? "Published UAF documents and your selected private collections." : "Ready documents in your selected private collections."}</p>
      </fieldset>
      {scope !== "public" && <fieldset className="space-y-3"><legend className="font-medium">Private collections</legend>
        {loading ? <p role="status">Loading collections...</p> : collections.length ? <div className="grid gap-3 sm:grid-cols-2">
          {collections.map(collection => <label key={collection.id} className="flex items-start gap-3 border rounded-lg p-3 cursor-pointer">
            <input className="mt-1" type="checkbox" checked={selected.includes(collection.id)} onChange={event => setSelected(ids => event.target.checked ? [...ids, collection.id] : ids.filter(id => id !== collection.id))} />
            <span className="min-w-0"><span className="block font-medium break-words">{collection.name}</span>
              {collection.description && <span className="block text-sm text-muted-foreground line-clamp-2">{collection.description}</span>}</span>
          </label>)}
        </div> : <p className="text-sm text-muted-foreground">No private collections yet. <Link href="/dashboard/knowledge" className="underline">Open your Library</Link>, or choose Public to use the corpus.</p>}
        <p className="text-xs text-muted-foreground">This source selection is saved with the conversation. Start a new conversation to change it.</p>
      </fieldset>}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <div className="flex flex-wrap justify-end gap-3">
        <button type="button" onClick={() => router.back()} className="secondary-action">Cancel</button>
        <button type="submit" className="primary-action premium-action" disabled={submitting || !title.trim() || (scope !== "public" && loading) || (scope === "private" && !selected.length)}>
          {submitting ? "Starting..." : "Start conversation"}
        </button>
      </div>
    </form>
  </div></DashboardLayout>;
}
