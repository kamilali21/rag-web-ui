"use client";
import { AnalysisClaim, AnalysisRun } from "@/lib/research-analysis";
import { ComparisonEvidence } from "@/lib/comparison";
import { Citations } from "./comparison-result";

function Claims({ claims }: { claims: AnalysisClaim[] }) {
  return claims.length ? <>{claims.map((claim, index) => <p className="comparison-claim" key={index}>{claim.text} <Citations sources={claim.citations} /></p>)}</>
    : <p className="document-summary-unavailable">Not identified in retrieved evidence.</p>;
}
export function AnalysisResult({ run }: { run: AnalysisRun }) {
  const result = run.result;
  if (run.status === "processing") return <p role="status">This analysis is still processing. Reload the saved analysis shortly.</p>;
  if (run.status === "failed" || !result) return <p role="alert">{run.error_message || "Analysis could not be completed. Start a new analysis to retry."}</p>;
  const evidence = new Map<string, ComparisonEvidence>();
  [...result.sections, ...result.profiles.flatMap(profile => profile.fields)].forEach(section => section.claims.forEach(claim => claim.citations.forEach(item => evidence.set(item.evidence_id, item))));
  return <section className="analysis-result" aria-label="Evidence-backed research analysis">
    <p className="insights-workflow-note">{result.notice}</p>
    {result.question && <p className="insights-question">{result.question}</p>}
    <div className="comparison-compatibility"><strong>Evidence coverage</strong><p>{result.coverage.selected_count} selected papers · {result.coverage.related_count} related public papers · {result.coverage.evidence_count} retrieved passages</p>
      <p>{result.coverage.enabled ? `Related discovery considered ${result.coverage.candidate_count} metadata-matched candidates (limit ${result.coverage.candidate_limit}). Semantic ranking indicates relevance, not scientific quality.` : "Related public discovery was not used. Only your selected papers contribute evidence."}</p>
      <ul>{result.documents.map(doc => <li key={doc.id}>{doc.title} <span className="comparison-source-scope">{doc.role === "selected" ? "Selected" : "Related"} · {doc.scope} library</span></li>)}</ul>
    </div>
    {run.status === "insufficient_evidence" && <p role="status">There is insufficient retrieved evidence for this analysis.</p>}
    <div className="analysis-sections">{result.sections.map(section => <section key={section.key} aria-label={section.title}><h3>{section.title}</h3><Claims claims={section.claims} /></section>)}</div>
    <details className="comparison-evidence"><summary>Research profiles ({result.profiles.length})</summary>
      {result.profiles.map(profile => <article key={profile.document_id}><h3>{result.documents.find(doc => doc.id === profile.document_id)?.title}</h3>
        <div className="insights-comparison-scroll" tabIndex={0} role="region" aria-label="Research profile; scroll if needed"><table className="insights-comparison"><caption className="sr-only">Research profile for {result.documents.find(doc => doc.id === profile.document_id)?.title}</caption><thead><tr><th scope="col">Dimension</th><th scope="col">Evidence-backed profile</th></tr></thead><tbody>{profile.fields.map(field => <tr key={field.key}><th scope="row">{field.title}</th><td><Claims claims={field.claims} /></td></tr>)}</tbody></table></div>
      </article>)}
    </details>
    {!!evidence.size && <details className="comparison-evidence"><summary>Inspect evidence snapshots ({evidence.size})</summary>{Array.from(evidence.values()).map(item => <article key={item.evidence_id}><h3>{item.file_name} <Citations sources={[item]} /></h3><blockquote>{item.excerpt}</blockquote></article>)}</details>}
    <p className="insights-workflow-note">Contradiction interpretation and candidate-gap analysis are not included in this workflow.</p>
    <a className="insights-text-action" href={`/dashboard/insights?analysis=${run.id}`}>Reopen saved analysis #{run.id}</a>
  </section>;
}
