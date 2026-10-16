"use client";

import { useRef, useState } from "react";
import { BarChart3, Check, ChevronDown, FileText, Filter, LockKeyhole, Search, Sparkles, X } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ResearchDocument, researchDate, sampleDocuments } from "./sample-documents";

// Added by ChatGPT: selection and workflow limits apply equally to the table and modal picker.
const MAX_DOCUMENTS = 5;
const dimensions = ["Research questions", "Methodology", "Key findings", "Limitations"];
const analysisTypes = ["Research overview", "Research gaps", "Contradictions"];
type Mode = "compare" | "analyse";
const initialFilters = { department: "", author: "", type: "", from: "", to: "" };

export function Insights() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sort, setSort] = useState("newest");
  const [selected, setSelected] = useState<number[]>([]);
  const [details, setDetails] = useState<ResearchDocument | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [step, setStep] = useState<"configure" | "workspace">("configure");
  const [pickerQuery, setPickerQuery] = useState("");
  const [chosenDimensions, setChosenDimensions] = useState(dimensions);
  const [analysisType, setAnalysisType] = useState(analysisTypes[0]);
  const [question, setQuestion] = useState("");
  const [activeTab, setActiveTab] = useState("Documents");
  const actionTrigger = useRef<HTMLButtonElement | null>(null);
  const selectedDocuments = sampleDocuments.filter((document) => selected.includes(document.id));
  const invalidDates = Boolean(filters.from && filters.to && filters.from > filters.to);
  const filterCount = Object.values(filters).filter(Boolean).length;
  const visible = sampleDocuments.filter((document) => {
    const matchesQuery = `${document.name} ${document.author} ${document.department}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (!filters.department || filters.department === document.department)
      && (!filters.author || filters.author === document.author) && (!filters.type || filters.type === document.type)
      && (!filters.from || document.date >= filters.from) && (!filters.to || document.date <= filters.to);
  }).sort((a, b) => sort === "name" ? a.name.localeCompare(b.name) : sort === "oldest" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
  const allVisibleSelected = visible.length > 0 && visible.every((document) => selected.includes(document.id));
  const someVisibleSelected = visible.some((document) => selected.includes(document.id));
  const minimum = mode === "compare" || analysisType === "Contradictions" ? 2 : 1;
  const canContinue = selected.length >= minimum && (mode !== "compare" || chosenDimensions.length > 0);

  // Added by ChatGPT: filtering never silently discards selections from other departments.
  const toggleDocument = (id: number) => setSelected((previous) => previous.includes(id)
    ? previous.filter((item) => item !== id) : previous.length < MAX_DOCUMENTS ? [...previous, id] : previous);
  const selectVisible = () => setSelected((previous) => Array.from(new Set([...previous, ...visible.map((document) => document.id)])).slice(0, MAX_DOCUMENTS));
  const resetFilters = () => { setFilters(initialFilters); setQuery(""); };
  const openWorkflow = (nextMode: Mode, trigger: HTMLButtonElement) => {
    actionTrigger.current = trigger;
    setMode(nextMode); setStep("configure"); setPickerQuery(""); setActiveTab("Documents");
  };

  return (
    <section className="insights-page list-page" aria-label="Insights">
      {/* Added by ChatGPT: reference heading and action pair inherit the shared theme. */}
      <div className="dashboard-heading insights-heading">
        <h1>Insights</h1>
        <div className="insights-actions">
          <button className="primary-action premium-action" onClick={(event) => openWorkflow("compare", event.currentTarget)}><BarChart3 size={22} aria-hidden="true" />Compare</button>
          <button className="primary-action premium-action" onClick={(event) => openWorkflow("analyse", event.currentTarget)}><Sparkles size={22} aria-hidden="true" />Analyse</button>
        </div>
      </div>
      <aside className="insights-preview-banner" aria-label="Insights preview">
        <span className="insights-preview-lock"><LockKeyhole size={18} aria-hidden="true" /> Coming soon</span>
        <div><strong>Advanced research insights are in development</strong>
          <p>Compare studies side by side, surface research gaps and contradictions, and explore evidence-backed findings. The records below are a sample preview; live corpus analysis is not connected yet.</p>
        </div>
      </aside>
      <div className="library-search insights-search">
        <Search size={24} aria-hidden="true" />
        <input type="search" aria-label="Search documents" placeholder="Search documents..." value={query} onChange={(event) => setQuery(event.target.value)} />
        <button className="insights-filter-toggle" aria-label={`Filters${filterCount ? ` (${filterCount} active)` : ""}`} title="Filter documents" aria-expanded={filtersOpen} aria-controls="insights-filters" onClick={() => setFiltersOpen(!filtersOpen)}>
          <Filter size={24} />{filterCount > 0 && <span>{filterCount}</span>}
        </button>
      </div>

      {/* Added by ChatGPT: native labeled controls provide keyboard and mobile date/filter support. */}
      {filtersOpen && <div id="insights-filters" className="insights-filters">
        {(["department", "author", "type"] as const).map((key) => <label key={key}>{key === "type" ? "Document type" : key === "author" ? "Author" : "Department"}
          <select value={filters[key]} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })}>
            <option value="">All {key === "type" ? "types" : `${key}s`}</option>
            {Array.from(new Set(sampleDocuments.map((document) => document[key]))).sort().map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>)}
        <label>From date<input type="date" value={filters.from} max={filters.to || undefined} onChange={(event) => setFilters({ ...filters, from: event.target.value })} /></label>
        <label>To date<input type="date" value={filters.to} min={filters.from || undefined} onChange={(event) => setFilters({ ...filters, to: event.target.value })} /></label>
        {invalidDates && <p role="alert" className="text-destructive">The end date must be on or after the start date.</p>}
      </div>}
      <div className="insights-toolbar">
        <div className="insights-summary"><span className="insights-sample-label">Sample corpus</span>
          <span role="status">{visible.length} documents{selected.length > 0 ? ` / ${selected.length} selected` : ""}</span>
          {(query || filterCount > 0) && <button className="insights-text-action" onClick={resetFilters}><X size={15} />Clear filters</button>}
        </div>
        <div className="insights-table-tools">
          <select className="library-select" aria-label="Sort documents" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="name">Name A-Z</option>
          </select>
          <DropdownMenu.Root>
            <DropdownMenu.Trigger className="insights-selection-menu"><FileText size={19} />Select Documents<ChevronDown size={18} /></DropdownMenu.Trigger>
            <DropdownMenu.Portal><DropdownMenu.Content className="insights-menu" align="end" sideOffset={6}>
              <DropdownMenu.Item disabled={!visible.length} onSelect={selectVisible}>Select visible documents</DropdownMenu.Item>
              <DropdownMenu.Item disabled={!selected.length} onSelect={() => setSelected([])}>Clear selection</DropdownMenu.Item>
            </DropdownMenu.Content></DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>

      {/* Added by ChatGPT: stable desktop columns reflow into labeled records on small screens. */}
      {visible.length > 0 ? <table className="insights-table">
        <caption className="sr-only">Sample research documents</caption>
        <colgroup><col className="insights-check-col" /><col className="insights-name-col" /><col className="insights-size-col" /><col className="insights-author-col" /><col className="insights-department-col" /><col className="insights-date-col" /></colgroup>
        <thead><tr><th scope="col"><input type="checkbox" aria-label="Select all visible documents" checked={allVisibleSelected}
          ref={(node) => { if (node) node.indeterminate = someVisibleSelected && !allVisibleSelected; }}
          onChange={() => allVisibleSelected ? setSelected((previous) => previous.filter((id) => !visible.some((document) => document.id === id))) : selectVisible()} /></th>
          {["Name", "Size", "Author", "Department", "Date"].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>{visible.map((document) => <tr key={document.id} data-selected={selected.includes(document.id)}>
          <td className="insights-row-check"><input type="checkbox" aria-label={`Select ${document.name}`} checked={selected.includes(document.id)} onChange={() => toggleDocument(document.id)} /></td>
          <td className="insights-row-name"><button className="document-name" onClick={() => setDetails(document)}>
            <span className="document-icon" aria-hidden="true"><FileText strokeWidth={1.5} /><span>PDF</span></span><span>{document.name}</span>
          </button></td>
          <td data-label="Size">{document.size}</td><td data-label="Author">{document.author}</td><td data-label="Department">{document.department}</td><td data-label="Date">{researchDate(document.date)}</td>
        </tr>)}</tbody>
      </table> : <div className="library-empty"><Search size={32} /><h2>No matching documents</h2><Button variant="outline" onClick={resetFilters}>Clear filters</Button></div>}
      {selected.length > 0 && <div className="insights-selection-footer"><span>{selected.length} of {MAX_DOCUMENTS} documents selected</span><button className="insights-text-action" onClick={() => setSelected([])}><X size={16} />Clear selection</button></div>}

      {/* Added by ChatGPT: metadata only; these sample records have no associated PDF or download endpoint. */}
      <Dialog open={details !== null} onOpenChange={(open) => { if (!open) setDetails(null); }}>
        <DialogContent><DialogHeader><DialogTitle className="pr-6 leading-snug">{details?.name}</DialogTitle><DialogDescription>Sample document</DialogDescription></DialogHeader>
          {details && <><dl className="document-details"><dt>Author</dt><dd>{details.author}</dd><dt>Department</dt><dd>{details.department}</dd><dt>Type</dt><dd>{details.type}</dd><dt>Size</dt><dd>{details.size}</dd><dt>Date</dt><dd>{researchDate(details.date)}</dd></dl>
            <Button variant="outline" onClick={() => toggleDocument(details.id)}>{selected.includes(details.id) ? <Check size={18} /> : <FileText size={18} />}{selected.includes(details.id) ? "Remove from selection" : "Select document"}</Button></>}
        </DialogContent>
      </Dialog>

      {/* Added by ChatGPT: the full configuration flow stays in memory and never calls a backend. */}
      <Dialog open={mode !== null} onOpenChange={(open) => { if (!open) setMode(null); }}>
        <DialogContent className="insights-dialog" onCloseAutoFocus={(event) => { event.preventDefault(); actionTrigger.current?.focus(); }}>
          <DialogHeader><DialogTitle>{mode === "compare" ? "Compare documents" : "Analyse research"}</DialogTitle>
            <DialogDescription>{step === "configure" ? `Sample corpus / ${selected.length} documents selected` : "Sample workspace / Analysis service not connected"}</DialogDescription>
          </DialogHeader>
          {step === "configure" ? <>
            <div className="insights-picker-search"><Search size={18} /><input type="search" aria-label="Find documents to select" placeholder="Find a document or author..." value={pickerQuery} onChange={(event) => setPickerQuery(event.target.value)} /></div>
            <div className="insights-picker" role="group" aria-label="Documents for this workspace">
              {sampleDocuments.filter((document) => `${document.name} ${document.author}`.toLowerCase().includes(pickerQuery.trim().toLowerCase())).map((document) => <label key={document.id}>
                <input type="checkbox" checked={selected.includes(document.id)} onChange={() => toggleDocument(document.id)} />
                <span>{document.name}<small>{document.author} / {document.department}</small></span>
              </label>)}
              {!sampleDocuments.some((document) => `${document.name} ${document.author}`.toLowerCase().includes(pickerQuery.trim().toLowerCase())) && <p className="p-4 text-sm">No matching documents.</p>}
            </div>
            {mode === "compare" ? <fieldset className="insights-options"><legend>Compare by</legend>{dimensions.map((dimension) => <label key={dimension}><input type="checkbox" checked={chosenDimensions.includes(dimension)} onChange={() => setChosenDimensions((previous) => previous.includes(dimension) ? previous.filter((item) => item !== dimension) : [...previous, dimension])} />{dimension}</label>)}</fieldset>
              : <label className="insights-field">Analysis focus<select value={analysisType} onChange={(event) => setAnalysisType(event.target.value)}>{analysisTypes.map((type) => <option key={type}>{type}</option>)}</select></label>}
            <label className="insights-field">Research question <span className="text-muted-foreground font-normal">(optional)</span><textarea rows={2} maxLength={1000} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="e.g. How do the studies differ in their approach to crop resilience?" /></label>
            <p className="insights-workflow-note" role="status">{selected.length < minimum ? `Select at least ${minimum} document${minimum === 1 ? "" : "s"} to continue.` : mode === "compare" && !chosenDimensions.length ? "Choose at least one comparison dimension." : `${selected.length} documents ready for this sample workspace.`}</p>
            <div className="insights-dialog-actions"><Button variant="outline" onClick={() => setMode(null)}>Cancel</Button><Button disabled={!canContinue} onClick={() => { setStep("workspace"); setActiveTab("Documents"); }}>Open {mode === "compare" ? "comparison" : "analysis"}</Button></div>
          </> : <>
            <div className="insights-workspace-heading"><span className="insights-sample-label">{mode === "compare" ? "Comparison" : analysisType}</span><Button variant="outline" size="sm" onClick={() => setStep("configure")}>Edit selection</Button></div>
            {question.trim() && <p className="insights-question">{question.trim()}</p>}
            <div className="insights-tabs" role="group" aria-label="Workspace views">{["Documents", ...(mode === "compare" ? chosenDimensions : [analysisType])].map((tab) => <button key={tab} aria-pressed={activeTab === tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
            {activeTab === "Documents" ? <div className="insights-comparison-scroll" tabIndex={0} role="region" aria-label="Selected document comparison"><table className="insights-comparison">
              <caption className="sr-only">Selected sample document metadata</caption><thead><tr><th scope="col">Document</th>{selectedDocuments.map((document) => <th scope="col" key={document.id}>{document.name}</th>)}</tr></thead>
              <tbody>{(["author", "department", "type", "date", "size"] as const).map((field) => <tr key={field}><th scope="row">{field.charAt(0).toUpperCase() + field.slice(1)}</th>{selectedDocuments.map((document) => <td key={document.id}>{field === "date" ? researchDate(document.date) : document[field]}</td>)}</tr>)}</tbody>
            </table></div> : <div className="insights-pending"><Sparkles size={30} /><h2>{activeTab}</h2><p>Analysis service not connected. No findings have been generated for these sample documents.</p><p className="text-sm">{activeTab === "Contradictions" ? "Conflicting claims need source passages and citations before they can be assessed." : activeTab === "Research gaps" ? "Research gaps need evidence from the full documents and the wider corpus." : "Document text and cited evidence are required for this analysis."}</p></div>}
            <div className="insights-dialog-actions"><Button onClick={() => setMode(null)}>Done</Button></div>
          </>}
        </DialogContent>
      </Dialog>
    </section>
  );
}
