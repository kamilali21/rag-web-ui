"use client";
import { EvidenceInterpretation } from "@/lib/research-analysis";
import { Citations } from "./comparison-result";

export function EvidenceInterpretations({ items }: { items: EvidenceInterpretation[] }) {
  return <section aria-label="Evidence interpretation">
    <h3 className="font-semibold mb-2">Evidence interpretation</h3>
    <p className="insights-workflow-note">These are relationships within retrieved passages, not verdicts on scientific validity. Context differences may affect comparability; they do not establish the cause of a disagreement.</p>
    {!items.length && <p className="document-summary-unavailable">No cross-paper relationship could be supported by the retrieved evidence. This does not establish that the papers agree or that contradictions do not exist.</p>}
    <div className="analysis-sections">{items.map((item, index) => <section key={index} aria-label={`Evidence relationship ${index + 1}`}>
      <span className="interpretation-label">{item.label}</span>
      <h4 className="font-semibold mt-2">{item.claim} <Citations sources={item.supporting} /></h4>
      <dl className="interpretation-roles">{(["supporting", "contradicting", "qualifying"] as const).map(role => <div key={role}>
        <dt>{role[0].toUpperCase() + role.slice(1)} evidence</dt>
        <dd>{item[role].length ? <ul>{item[role].map(source => <li key={source.evidence_id}>{source.file_name} <Citations sources={[source]} /></li>)}</ul> : <span className="document-summary-unavailable">Not identified in retrieved evidence.</span>}</dd>
      </div>)}</dl>
      <p className="comparison-claim"><strong>Interpretation: </strong>{item.interpretation.text} <Citations sources={item.interpretation.citations} /></p>
      {!!item.context_factors.length && <div className="interpretation-factors"><h4 className="font-semibold">Context to consider</h4>{item.context_factors.map(factor => <p key={factor.key}><strong>{factor.title}: </strong>{factor.text} <Citations sources={factor.citations} /></p>)}</div>}
    </section>)}</div>
  </section>;
}
