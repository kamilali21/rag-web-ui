import { InsightsDocument } from "./insights";

export const comparisonCriteria: Record<string, string> = {
  objective: "Research objective/question", methodology: "Methodology", context: "Study area/context",
  population: "Population/sample", dataset: "Dataset", variables: "Variables", techniques: "Models/techniques",
  findings: "Main findings", limitations: "Limitations", conclusion: "Conclusion", future_work: "Future work",
};
export type ComparisonEvidence = { evidence_id: string; document_id: number; knowledge_base_id: number;
  scope: "public" | "private"; file_name: string; page: number | null; excerpt: string; evidence_hash: string };
export type ComparisonRun = {
  id: number; status: "processing" | "complete" | "failed" | "insufficient_evidence"; error_message: string | null;
  result: null | { documents: InsightsDocument[]; question: string; notice: string;
    compatibility: { label: string; explanation: string; citations: ComparisonEvidence[] };
    criteria: { criterion: string; title: string; values: { document_id: number; unavailable: boolean;
      claims: { text: string; citations: ComparisonEvidence[] }[] }[] }[] };
};
export function comparisonRequestId() {
  // getRandomValues also works on the existing local HTTP deployment.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
