"use client";

import { useEffect, useRef, useState } from "react";
import { BarChart3, BookOpen, ChevronLeft, ChevronRight, File, Filter, Loader2, RefreshCw, Search, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PublicDocumentDetails } from "@/components/knowledge-base/public-library-dialogs";
import { PrivateInsightsDetails } from "./document-details";
import { ComparisonResult } from "./comparison-result";
import { AnalysisWorkflow } from "./analysis-workflow";
import { lastAnalysisKey, validAnalysisRequest } from "@/lib/research-analysis";
import { comparisonCriteria, comparisonRequestId, ComparisonRun } from "@/lib/comparison";
import { api, ApiError } from "@/lib/api";
import { Department } from "@/lib/public-library";
import { documentSize } from "@/lib/library";
import { emptyInsightsFilters, InsightsDocument, InsightsMode, InsightsScope, insightsDocumentsUrl, MAX_INSIGHTS_DOCUMENTS } from "@/lib/insights";

const dimensions = Object.keys(comparisonCriteria);
const message = (error: unknown) => error instanceof ApiError ? error.message : "Unable to load Insights. Please retry.";

export function Insights() {
  const [scope, setScope] = useState<InsightsScope>("public");
  const [draft, setDraft] = useState(emptyInsightsFilters);
  const [filters, setFilters] = useState(emptyInsightsFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [cursors, setCursors] = useState<(number | null)[]>([null]);
  const [documents, setDocuments] = useState<InsightsDocument[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [departmentError, setDepartmentError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState<InsightsDocument[]>([]);
  const [details, setDetails] = useState<InsightsDocument | null>(null);
  const [mode, setMode] = useState<InsightsMode | null>(null);
  const [validating, setValidating] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [chosenDimensions, setChosenDimensions] = useState(["objective", "methodology", "findings", "limitations"]);
  const [comparison, setComparison] = useState<ComparisonRun | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [reloadSaved, setReloadSaved] = useState(0);
  const [lastAnalysis, setLastAnalysis] = useState<string | null>(null);
  useEffect(() => {
    try { const id = sessionStorage.getItem(lastAnalysisKey); if (validAnalysisRequest(id)) setLastAnalysis(id); } catch { /* Storage may be disabled. */ }
  }, []);
  const requestKey = useRef<{ body: string; id: string } | null>(null);
  const [question, setQuestion] = useState("");
  const actionTrigger = useRef<HTMLButtonElement | null>(null);
  const validation = useRef<AbortController | null>(null);
  useEffect(() => () => validation.current?.abort(), []);
  useEffect(() => {
    const analysisId = Number(new URLSearchParams(window.location.search).get("analysis"));
    const analysisRequest = new URLSearchParams(window.location.search).get("analysisRequest");
    if ((Number.isSafeInteger(analysisId) && analysisId > 0) || validAnalysisRequest(analysisRequest)) { setMode("analyse"); return; }
    const id = Number(new URLSearchParams(window.location.search).get("comparison"));
    if (!Number.isSafeInteger(id) || id <= 0) return;
    const controller = new AbortController(); validation.current = controller;
    setSavedId(id); setMode("compare"); setValidating(true); setValidationError(""); setComparison(null);
    api.get(`/api/insights/comparisons/${id}`, { signal: controller.signal, cache: "no-store" })
      .then((run: ComparisonRun) => { if (!controller.signal.aborted) setComparison(run); })
      .catch(failure => { if (!controller.signal.aborted) setValidationError(message(failure)); })
      .finally(() => { if (!controller.signal.aborted) setValidating(false); });
    return () => controller.abort();
  }, [reloadSaved]);

  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(""); setDocuments([]);
    api.get(insightsDocumentsUrl(scope, filters, cursors[cursors.length - 1]), { signal: controller.signal, cache: "no-store" })
      .then((result: { items: InsightsDocument[]; has_more: boolean }) => { if (!controller.signal.aborted) { setDocuments(result.items); setHasMore(result.has_more); } })
      .catch(failure => { if (!controller.signal.aborted) setError(message(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, filters, cursors, refresh]);
  useEffect(() => {
    const controller = new AbortController(); setDepartmentError(false);
    void (async () => {
      const result: Department[] = [];
      for (let after = 0; ; ) {
        const page: Department[] = await api.get(`/api/departments?limit=100${after ? `&after_id=${after}` : ""}`, { signal: controller.signal });
        result.push(...page);
        if (page.length < 100) break;
        after = page[page.length - 1].id;
      }
      if (!controller.signal.aborted) setDepartments(result);
    })().catch(() => { if (!controller.signal.aborted) setDepartmentError(true); });
    return () => controller.abort();
  }, [refresh]);

  const toggle = (document: InsightsDocument) => setSelected(previous => previous.some(row => row.id === document.id)
    ? previous.filter(row => row.id !== document.id) : previous.length < MAX_INSIGHTS_DOCUMENTS ? [...previous, document] : previous);
  const allVisibleSelected = documents.length > 0 && documents.every(row => selected.some(item => item.id === row.id));
  const someVisibleSelected = documents.some(row => selected.some(item => item.id === row.id));
  const selectVisible = () => setSelected(previous => allVisibleSelected ? previous.filter(row => !documents.some(item => item.id === row.id))
    : [...previous, ...documents.filter(row => !previous.some(item => item.id === row.id))].slice(0, MAX_INSIGHTS_DOCUMENTS));
  const resetFilters = () => { setDraft(emptyInsightsFilters); setFilters(emptyInsightsFilters); setCursors([null]); };
  const filterCount = Object.entries(filters).filter(([key, value]) => key !== "search" && !!value).length;
  const minimum = 2;
  const closeWorkflow = () => {
    validation.current?.abort(); setMode(null); setValidating(false); setSavedId(null);
    const url = new URL(window.location.href); url.searchParams.delete("comparison"); url.searchParams.delete("analysis");
    url.searchParams.delete("analysisRequest");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  };
  const openWorkflow = (next: InsightsMode, trigger: HTMLButtonElement) => {
    actionTrigger.current = trigger; setMode(next); setComparison(null); setSavedId(null); setValidationError(""); requestKey.current = null;
  };
  const prepare = async () => {
    validation.current?.abort(); const controller = new AbortController(); validation.current = controller;
    setValidating(true); setValidationError("");
    try {
      if (mode === "compare") {
        const body = { scope, document_ids: selected.map(row => row.id), criteria: chosenDimensions, question };
        if (requestKey.current?.body !== JSON.stringify(body)) requestKey.current = { body: JSON.stringify(body), id: comparisonRequestId() };
        const run: ComparisonRun = await api.post("/api/insights/comparisons", { ...body, request_id: requestKey.current.id }, { signal: controller.signal });
        if (!controller.signal.aborted) setComparison(run);
        return;
      }
    } catch (failure) { if (!controller.signal.aborted) { setValidationError(message(failure)); if (failure instanceof ApiError && failure.status > 0) requestKey.current = null; } }
    finally { if (!controller.signal.aborted) setValidating(false); }
  };

  return <section className="list-page" aria-label="Insights">
    <div className="library-heading">
      <div className="library-title"><h1>Insights</h1><Sparkles size={27} strokeWidth={1.8} aria-hidden="true" /></div>
      <div className="library-scope insights-scope" role="group" aria-label="Insights source scope">{(["public", "private", "both"] as const).map(value => <button key={value} aria-pressed={scope === value} onClick={() => {
        setScope(value); setSelected([]); setDetails(null); closeWorkflow(); setCursors([null]); setDocuments([]);
      }}>{value[0].toUpperCase() + value.slice(1)}</button>)}</div>
      <div className="library-heading-actions insights-actions">
        <Button className="primary-action premium-action" disabled={selected.length < 2} onClick={event => openWorkflow("compare", event.currentTarget)}><BarChart3 size={18} /> Compare</Button>
        <Button className="primary-action premium-action" disabled={!selected.length} onClick={event => openWorkflow("analyse", event.currentTarget)}><Sparkles size={18} /> Analyse</Button>
      </div>
    </div>
    <p className="insights-catalog-note">Explore ready papers. Compare two to five studies, or analyse selected research with cited profiles and related evidence.</p>
    <a className="insights-text-action history-entry" href="/dashboard/insights/history">Analysis history</a>
    {lastAnalysis && <a className="insights-text-action" href={`/dashboard/insights?analysisRequest=${lastAnalysis}`}>Resume last analysis</a>}
    <form className="public-library-filters" onSubmit={event => { event.preventDefault(); setFilters({ ...draft }); setCursors([null]); }}>
      <div className="library-search">
        <button type="submit" className="icon-button" aria-label="Search documents"><Search size={23} strokeWidth={1.6} /></button>
        <input type="search" aria-label="Search documents" placeholder="Search titles, authors, abstracts..." maxLength={200} value={draft.search} onChange={event => setDraft({ ...draft, search: event.target.value })} />
        <button type="button" className="icon-button public-filter-toggle" aria-label="Toggle Insights filters" title="Show filters" aria-expanded={filtersOpen} aria-controls="insights-filters" onClick={() => setFiltersOpen(value => !value)}><Filter size={20} />{filterCount > 0 && <span className="public-filter-count">{filterCount}</span>}</button>
      </div>
      <div id="insights-filters" hidden={!filtersOpen}>{filtersOpen && <div className="public-filters">
        <div className="public-filter-fields">
          <label>Author<input className="public-input" maxLength={200} value={draft.author} onChange={event => setDraft({ ...draft, author: event.target.value })} /></label>
          <label>Department<select className="public-input" value={draft.department_id} onChange={event => setDraft({ ...draft, department_id: event.target.value })}><option value="">All departments</option>{departments.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <fieldset className="public-year-range"><legend>Year range</legend><div className="public-year-inputs"><input className="public-input" aria-label="From year" placeholder="From" type="number" min={1000} max={9999} value={draft.year_from} onChange={event => setDraft({ ...draft, year_from: event.target.value })} /><span aria-hidden="true">–</span><input className="public-input" aria-label="To year" placeholder="To" type="number" min={draft.year_from || 1000} max={9999} value={draft.year_to} onChange={event => setDraft({ ...draft, year_to: event.target.value })} /></div></fieldset>
          <label>Type<select className="public-input" value={draft.document_type} onChange={event => setDraft({ ...draft, document_type: event.target.value })}><option value="">All types</option>{["paper", "thesis", "report", "other"].map(type => <option key={type} value={type}>{type[0].toUpperCase() + type.slice(1)}</option>)}</select></label>
        </div>
        <div className="public-filter-actions"><Button type="submit"><Search size={16} /> Search</Button><Button variant="outline" type="button" onClick={resetFilters}><X size={16} /> Clear filters</Button></div>
      </div>}</div>
    </form>
    {departmentError && <p role="alert">Department options could not load. <button className="insights-text-action" onClick={() => setRefresh(value => value + 1)}>Retry departments</button></p>}
    <div className="insights-toolbar">
      <label className="insights-select-visible"><input type="checkbox" aria-label="Select visible documents" checked={allVisibleSelected} disabled={loading || !!error || !documents.length}
        ref={node => { if (node) node.indeterminate = someVisibleSelected && !allVisibleSelected; }} onChange={selectVisible} /> Select visible</label>
      <span role="status">{selected.length} of {MAX_INSIGHTS_DOCUMENTS} selected</span>
      {!!selected.length && <button className="insights-text-action" onClick={() => setSelected([])}><X size={15} /> Clear selection</button>}
    </div>
    {error ? <div className="library-empty" role="alert"><h2>Insights unavailable</h2><p>{error}</p><Button onClick={() => setRefresh(value => value + 1)}>Retry</Button></div> : loading ? <div className="library-empty" role="status"><Loader2 className="animate-spin" /><p>Loading research...</p></div> : documents.length ?
      <table className="library-table public-library-table insights-catalog-table" aria-label="Research documents">
        <colgroup><col style={{ width: "43%" }} /><col style={{ width: "22%" }} /><col style={{ width: "25%" }} /><col style={{ width: "10%" }} /></colgroup>
        <thead><tr>{["Title", "Author", "Department", "Year"].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>{documents.map(document => { const checked = selected.some(row => row.id === document.id); return <tr key={document.id} data-selected={checked}>
          <td><div className="public-document-cell"><span className="document-icon" aria-hidden="true"><File strokeWidth={1.6} /><span>{document.file_name.split(".").pop()?.slice(0, 4)}</span></span>
            <div className="public-document-summary"><div className="public-document-title"><button className="document-name" title={document.title} aria-label={`Details for ${document.title}`} onClick={() => setDetails(document)}><span className="document-label">{document.title}</span></button>
              <label className="icon-button insights-document-select"><input type="checkbox" aria-label={`Select ${document.title}`} checked={checked} disabled={!checked && selected.length >= MAX_INSIGHTS_DOCUMENTS} onChange={() => toggle(document)} /></label>
            </div><span className="public-document-kind">{document.scope} / {document.document_type || "Document"} / {documentSize(document.file_size)}</span></div></div></td>
          <td><span className="public-table-value">{document.authors_text || "Not recorded"}</span></td><td><span className="public-table-value">{document.department_name || "Not assigned"}</span></td><td>{document.publication_year || "Not recorded"}</td>
        </tr>; })}</tbody>
      </table> : <div className="library-empty"><BookOpen size={36} /><h2>{Object.values(filters).some(Boolean) ? "No matching research" : "No ready documents in this scope"}</h2>{Object.values(filters).some(Boolean) && <Button variant="outline" onClick={resetFilters}>Clear filters</Button>}</div>}
    <div className="library-footer"><p role="status">{!loading && !error ? `${documents.length} document${documents.length === 1 ? "" : "s"} on this page` : ""}</p>
      <div className="library-tools"><nav className="library-tools" aria-label="Insights pages"><button className="icon-button" aria-label="Previous page" disabled={loading || !!error || cursors.length === 1} onClick={() => setCursors(values => values.slice(0, -1))}><ChevronLeft size={20} /></button><span className="text-sm">Page {cursors.length}</span><button className="icon-button" aria-label="Next page" disabled={loading || !!error || !hasMore} onClick={() => setCursors(values => [...values, documents[documents.length - 1].id])}><ChevronRight size={20} /></button></nav><button className="icon-button" aria-label="Refresh Insights" disabled={loading} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={17} /></button></div>
    </div>
    {details?.scope === "public" && <PublicDocumentDetails id={details.id} onClose={() => setDetails(null)} />}
    {details?.scope === "private" && <PrivateInsightsDetails id={details.id} onClose={() => setDetails(null)} />}
    <Dialog open={mode !== null} onOpenChange={open => { if (!open) closeWorkflow(); }}><DialogContent className="insights-dialog" onCloseAutoFocus={event => { if (actionTrigger.current) { event.preventDefault(); actionTrigger.current.focus(); } }}>
      <DialogHeader><DialogTitle>{mode === "compare" ? "Compare documents" : "Analyse research"}</DialogTitle><DialogDescription>{mode === "compare" ? "Compare selected papers using cited passages. Results are saved privately and source access is checked again when reopened." : "Build research profiles and a bounded, cited synthesis. Results are saved privately and source access is checked again when reopened."}</DialogDescription></DialogHeader>
      {validationError && <p role="alert">{validationError}</p>}
      {mode === "analyse" ? <AnalysisWorkflow selected={selected} scope={scope} toggle={toggle} onClose={closeWorkflow} onStarted={setLastAnalysis} /> : comparison ? <><ComparisonResult run={comparison} /><div className="insights-dialog-actions"><Button variant="outline" onClick={() => { setComparison(null); setSavedId(null); requestKey.current = null; closeWorkflow(); }}>Close comparison</Button>{comparison.status === "processing" && <Button asChild><a href={`/dashboard/insights?comparison=${comparison.id}`}>Reload saved comparison</a></Button>}</div></> : savedId ? <><p role="status">{validating ? "Loading saved comparison..." : "Saved comparison unavailable."}</p><Button disabled={validating} onClick={() => setReloadSaved(value => value + 1)}>Retry saved comparison</Button></> : <>
        <div className="insights-picker" role="group" aria-label="Selected documents">{selected.map(row => <label key={row.id}><input type="checkbox" checked disabled={validating} onChange={() => toggle(row)} /><span>{row.title}<small>{row.scope} / {row.authors_text || "Author not recorded"}</small></span></label>)}</div>
        <fieldset className="insights-options"><legend>Compare by</legend>{dimensions.map(dimension => <label key={dimension}><input type="checkbox" disabled={validating} checked={chosenDimensions.includes(dimension)} onChange={() => setChosenDimensions(previous => previous.includes(dimension) ? previous.filter(item => item !== dimension) : [...previous, dimension])} />{comparisonCriteria[dimension]}</label>)}</fieldset>
        <label className="insights-field">Research question (optional)<textarea rows={2} maxLength={1000} disabled={validating} value={question} onChange={event => setQuestion(event.target.value)} /></label>
        <p className="insights-workflow-note">Select {minimum}–{MAX_INSIGHTS_DOCUMENTS} documents. Only selected papers contribute evidence. Missing information will be marked explicitly.</p>
        {validating && mode === "compare" && <p role="status">Retrieving each paper's evidence and generating the comparison. Closing this dialog does not cancel server processing.</p>}
        <div className="insights-dialog-actions"><Button variant="outline" onClick={closeWorkflow}>Cancel</Button><Button disabled={validating || selected.length < minimum || !chosenDimensions.length} onClick={() => void prepare()}>{validating ? "Comparing papers..." : "Generate comparison"}</Button></div>
      </>}
    </DialogContent></Dialog>
  </section>;
}
