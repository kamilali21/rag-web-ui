"use client";

import { useCallback, useEffect, useState } from "react";
import { Camera, Loader2, Save, Trash2, UserRound } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Department } from "@/lib/public-library";
import { Button } from "@/components/ui/button";
import SignOutButton from "@/components/layout/sign-out-button";

type Profile = { full_name: string; department_id: number; department_name: string | null; degree: string;
  research_area: string; ag_number: string | null; class_name: string | null; section: string | null; photo_url: string | null };
type Publication = { id: number; status: string; metadata: { title: string }; source_file_name: string | null;
  public_document_id: number | null; publication_status: string | null; denial_reason: string | null; created_at: string };
type Withdrawal = { id: number; publication_request_id: number; title: string; status: string; reason: string | null; decision_reason: string | null };
type RequestData = { publications: Publication[]; withdrawals: Withdrawal[] };
const errorText = (error: unknown) => error instanceof ApiError ? error.message : "Request failed. Please try again.";
const emptyProfile = { full_name: "", department_id: "", degree: "", research_area: "", ag_number: "", class_name: "", section: "" };

export function ResearcherProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [draft, setDraft] = useState(emptyProfile);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [requests, setRequests] = useState<RequestData>({ publications: [], withdrawals: [] });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [photoVersion, setPhotoVersion] = useState(0);
  const [refresh, setRefresh] = useState(0);

  const load = useCallback(async (signal?: AbortSignal) => {
    const [current, departmentPage, data] = await Promise.all([
      api.get("/api/researcher/profile", { signal, cache: "no-store" }),
      api.get("/api/departments?limit=100", { signal, cache: "no-store" }),
      api.get("/api/researcher/requests", { signal, cache: "no-store" }),
    ]);
    if (signal?.aborted) return;
    setProfile(current); setDepartments(departmentPage); setRequests(data);
    setDraft(current ? { full_name: current.full_name, department_id: String(current.department_id), degree: current.degree,
      research_area: current.research_area, ag_number: current.ag_number || "", class_name: current.class_name || "", section: current.section || "" } : emptyProfile);
  }, []);

  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    void load(controller.signal).catch(failure => { if (!controller.signal.aborted) setError(errorText(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load, refresh]);

  useEffect(() => {
    if (!requests.publications.some(item => item.status === "processing")) return;
    const timer = setTimeout(() => setRefresh(value => value + 1), 3000);
    return () => clearTimeout(timer);
  }, [requests]);

  const update = (key: keyof typeof emptyProfile, value: string) => setDraft(previous => ({ ...previous, [key]: value }));
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const result = await api.put("/api/researcher/profile", { ...draft, department_id: Number(draft.department_id) });
      setProfile(result); setNotice("Profile saved.");
    } catch (failure) { setError(errorText(failure)); }
    finally { setBusy(false); }
  };
  const photo = async (file?: File) => {
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) { setError("Choose an image up to 3 MiB."); return; }
    const form = new FormData(); form.append("file", file); setBusy(true); setError("");
    try { await api.put("/api/researcher/profile/photo", form); setProfile(previous => previous && { ...previous, photo_url: "/api/researcher/profile/photo" }); setPhotoVersion(value => value + 1); setNotice("Profile photo updated."); }
    catch (failure) { setError(errorText(failure)); }
    finally { setBusy(false); }
  };
  const removePhoto = async () => {
    setBusy(true); setError("");
    try { await api.delete("/api/researcher/profile/photo"); setPhotoVersion(value => value + 1); setRefresh(value => value + 1); }
    catch (failure) { setError(errorText(failure)); }
    finally { setBusy(false); }
  };
  const withdraw = async (request: Publication) => {
    const reason = window.prompt(`Request withdrawal of “${request.metadata.title}”? Optional reason:`);
    if (reason === null) return;
    setBusy(true); setError("");
    try { await api.post(`/api/researcher/requests/${request.id}/withdrawals`, { reason: reason.trim() || null }); setRefresh(value => value + 1); }
    catch (failure) { setError(errorText(failure)); }
    finally { setBusy(false); }
  };
  const cancel = async (requestId: number) => {
    setBusy(true); setError("");
    try { await api.post(`/api/researcher/requests/${requestId}/cancel`); setRefresh(value => value + 1); }
    catch (failure) { setError(errorText(failure)); }
    finally { setBusy(false); }
  };
  const withdrawalByPublication = new Map(requests.withdrawals.map(item => [item.publication_request_id, item]));

  return <section className="researcher-profile list-page">
    <header className="researcher-page-heading"><div><p className="researcher-eyebrow">RESEARCHER WORKSPACE</p><h1>Profile</h1>
      <p>Manage your academic details and publication requests.</p></div></header>
    {error && <p role="alert" className="corpus-error">{error}</p>}{notice && <p role="status" className="researcher-notice">{notice}</p>}
    {loading ? <p role="status">Loading your profile...</p> : <>
      <form className="researcher-profile-card corpus-form" onSubmit={save}>
        <div className="researcher-profile-photo">
          {profile?.photo_url ? <img src={`${profile.photo_url}?v=${photoVersion}`} alt="Your profile" /> : <span aria-hidden="true"><UserRound size={34} /></span>}
          <label className="primary-action researcher-photo-action"><Camera size={16} /> Add photo
            <input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={event => { void photo(event.target.files?.[0]); event.currentTarget.value = ""; }} />
          </label>
          {profile?.photo_url && <Button variant="outline" type="button" disabled={busy} onClick={removePhoto}><Trash2 size={15} /> Remove</Button>}
          <small>PNG, JPEG or WebP · up to 3 MiB</small>
        </div>
        <div className="researcher-profile-fields">
          <label>Full name<input className="public-input" maxLength={200} required value={draft.full_name} onChange={event => update("full_name", event.target.value)} /></label>
          <label>Department<select className="public-input" required value={draft.department_id} onChange={event => update("department_id", event.target.value)}>
            <option value="">Choose department</option>{departments.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Degree<input className="public-input" maxLength={120} required placeholder="e.g. MSc Plant Pathology" value={draft.degree} onChange={event => update("degree", event.target.value)} /></label>
          <label className="researcher-wide">Research area<textarea className="public-input" rows={3} maxLength={1000} required value={draft.research_area} onChange={event => update("research_area", event.target.value)} /></label>
          <p className="researcher-private-note researcher-wide">Ag number, class, section and your photo stay private to you and administrators unless a publication request explicitly includes photo consent. These details are never shown on public papers.</p>
          <label>Ag number<input className="public-input" maxLength={80} value={draft.ag_number} onChange={event => update("ag_number", event.target.value)} /></label>
          <label>Class<input className="public-input" maxLength={80} value={draft.class_name} onChange={event => update("class_name", event.target.value)} /></label>
          <label>Section<input className="public-input" maxLength={80} value={draft.section} onChange={event => update("section", event.target.value)} /></label>
          <div className="researcher-wide flex justify-end"><Button type="submit" disabled={busy}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save profile</Button></div>
        </div>
      </form>

      <section className="researcher-requests"><div className="researcher-section-heading"><h2>Publication activity</h2><Button variant="outline" disabled={busy} onClick={() => setRefresh(value => value + 1)}>Refresh</Button></div>
        {requests.publications.length === 0 && <p className="text-muted-foreground">Your publication requests and published papers will appear here.</p>}
        <div className="researcher-request-list">{requests.publications.map(request => {
          const withdrawal = withdrawalByPublication.get(request.id);
          const title = request.metadata?.title || request.source_file_name || `Request ${request.id}`;
          return <article className="researcher-request-card" key={request.id}>
            <div><h3>{title}</h3><p>{request.source_file_name || "Private source removed"} · <span className="capitalize">{withdrawal?.status === "approved" ? "archived" : request.status}</span></p>
              {request.denial_reason && <p className="researcher-decision-reason"><strong>Admin response:</strong> {request.denial_reason}</p>}
              {withdrawal?.decision_reason && <p className="researcher-decision-reason"><strong>Withdrawal response:</strong> {withdrawal.decision_reason}</p>}
              {withdrawal?.status === "pending" && <p role="status">Withdrawal request awaiting review.</p>}
              {request.status === "processing" && <p role="status">Approved. The public copy is processing and indexing before publication.</p>}
              {request.status === "failed" && <p role="status">Indexing did not complete. An administrator can retry the request.</p>}
              {withdrawal?.reason && <p><strong>Your withdrawal note:</strong> {withdrawal.reason}</p>}
            </div>
            <div className="researcher-request-actions">
              {request.status === "pending" && <Button variant="outline" disabled={busy} onClick={() => void cancel(request.id)}>Cancel request</Button>}
              {request.status === "published" && request.publication_status === "published" && !withdrawal?.status?.includes("pending") &&
                <Button variant="outline" disabled={busy} onClick={() => void withdraw(request)}>Request withdrawal</Button>}
              {request.status === "published" && request.public_document_id && request.publication_status === "published" &&
                <a className="primary-action" href={`/api/corpus/documents/${request.public_document_id}/content`}><span>Open public copy</span></a>}
            </div>
          </article>;
        })}</div>
      </section>
    </>}
    <footer className="researcher-profile-footer"><SignOutButton className="profile-signout-button" /></footer>
  </section>;
}
