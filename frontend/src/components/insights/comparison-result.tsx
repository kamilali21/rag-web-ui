"use client";
import { ComparisonEvidence, ComparisonRun } from "@/lib/comparison";

function sourceUrl(source: ComparisonEvidence) {
  const path = source.scope === "public" ? `/api/corpus/documents/${source.document_id}/content?inline=true`
    : `/api/knowledge-base/${source.knowledge_base_id}/documents/${source.document_id}/content?inline=true`;
  return path + (source.page === null ? "" : `#page=${source.page + 1}`);
}
export function Citations({ sources }: { sources: ComparisonEvidence[] }) {
  return <span className="document-summary-citations" aria-label="Supporting evidence">{sources.map(source => <a key={source.evidence_id} href={sourceUrl(source)} target="_blank" rel="noopener noreferrer"
    aria-label={`Open ${source.file_name}${source.page === null ? "" : `, page ${source.page + 1}`}`} title={source.excerpt}>
    [{source.evidence_id}]{source.page === null ? "" : ` p. ${source.page + 1}`}</a>)}</span>;
}
export function ComparisonResult({ run }: { run: ComparisonRun }) {
  const result = run.result;
  if (run.status === "processing") return <p role="status">This comparison is still processing. Reload the saved comparison shortly.</p>;
  if (run.status === "failed" || !result) return <p role="alert">{run.error_message || "Comparison could not be completed. Start a new comparison to retry."}</p>;
  const evidence = new Map<string, ComparisonEvidence>();
  result.criteria.forEach(row => row.values.forEach(cell => cell.claims.forEach(claim => claim.citations.forEach(item => evidence.set(item.evidence_id, item)))));
  result.compatibility.citations.forEach(item => evidence.set(item.evidence_id, item));
  return <section className="comparison-result" aria-label="Evidence-backed comparison">
    <p className="insights-workflow-note">{result.notice}</p>
    {result.question && <p className="insights-question">{result.question}</p>}
    <div className="comparison-compatibility"><strong>Comparability: {result.compatibility.label}</strong>
      <p>{result.compatibility.explanation} <Citations sources={result.compatibility.citations} /></p>
      {["Weakly related", "Different domains"].includes(result.compatibility.label) && <p>Interpret direct comparisons cautiously: contexts, methods or outcomes may not be equivalent.</p>}
    </div>
    {run.status === "insufficient_evidence" && <p role="status">There is insufficient retrieved evidence for this comparison.</p>}
    <div className="insights-comparison-scroll" tabIndex={0} role="region" aria-label="Comparison table; scroll horizontally for more papers">
      <table className="insights-comparison"><caption className="sr-only">Evidence-backed research comparison</caption>
        <thead><tr><th scope="col">Criterion</th>{result.documents.map(doc => <th scope="col" key={doc.id}>{doc.title}<small className="comparison-source-scope">{doc.scope} library</small></th>)}</tr></thead>
        <tbody>{result.criteria.map(row => <tr key={row.criterion}><th scope="row">{row.title}</th>{row.values.map(cell => <td key={cell.document_id}>
          {cell.unavailable ? <p className="document-summary-unavailable">Not identified in retrieved evidence.</p> : cell.claims.map((claim, index) => <p className="comparison-claim" key={index}>{claim.text} <Citations sources={claim.citations} /></p>)}
        </td>)}</tr>)}</tbody>
      </table>
    </div>
    {!!evidence.size && <details className="comparison-evidence"><summary>Inspect evidence snapshots ({evidence.size})</summary>{Array.from(evidence.values()).map(item => <article key={item.evidence_id}>
      <h3>{item.file_name} <Citations sources={[item]} /></h3><blockquote>{item.excerpt}</blockquote>
    </article>)}</details>}
    <a className="insights-text-action" href={`/dashboard/insights?comparison=${run.id}`}>Reopen saved comparison #{run.id}</a>
  </section>;
}
