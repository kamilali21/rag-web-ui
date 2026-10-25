"use client";
import { CandidateGap } from "@/lib/research-analysis";
import { Citations } from "./comparison-result";

export function CandidateGaps({ items }: { items: CandidateGap[] }) {
  return <section aria-label="Candidate research gaps">
    <h3 className="font-semibold mb-2">Candidate research gaps</h3>
    <p className="insights-workflow-note">Patterns in the retrieved evidence can suggest questions for further research. They do not establish novelty or absence of research elsewhere.</p>
    {!items.length && <p className="document-summary-unavailable">No supported candidate gap was identified in the retrieved evidence. This does not establish that no research gaps exist.</p>}
    <div className="analysis-sections">{items.map((item, index) => <section key={index} aria-label={`Candidate gap ${index + 1}`}>
      <span className="interpretation-label">{item.title}</span>
      <h4 className="font-semibold mt-2">{item.topic}</h4>
      <p className="insights-workflow-note">{item.qualification}</p>
      <p className="comparison-claim"><strong>Evidence pattern: </strong>{item.evidence_pattern.text} <Citations sources={item.evidence_pattern.citations} /></p>
      {item.timeframe && <p className="insights-workflow-note">Publication-date coverage: {item.timeframe.recent_papers} of {item.timeframe.dated_papers} retrieved papers fall in {item.timeframe.start_year}–{item.timeframe.end_year}. Dates alone do not determine scientific relevance or validity.</p>}
      <details className="comparison-evidence"><summary>Supporting source quotations ({item.evidence_quotes.length})</summary>
        {item.evidence_quotes.map(anchor => <article key={anchor.citation.evidence_id}><h4>{anchor.citation.file_name} <Citations sources={[anchor.citation]} /></h4><blockquote>{anchor.quote}</blockquote></article>)}
      </details>
    </section>)}</div>
  </section>;
}
