import { InsightsDocument } from "./insights";
import { ComparisonEvidence, ComparisonRun } from "./comparison";

// Only an opaque request ID is retained, never paper text, questions or results.
// The recovery API checks the current signed-in owner and every source again.
export const lastAnalysisKey = "researchiq:last-analysis-request";
export const validAnalysisRequest = (value: string | null): value is string => !!value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);

export type AnalysisClaim = { text: string; citations: ComparisonEvidence[] };
export type AnalysisSection = { key: string; title: string; claims: AnalysisClaim[] };
export type AnalysisRun = {
  id: number; status: ComparisonRun["status"]; error_message: string | null;
  result: null | {
    documents: (InsightsDocument & { role: "selected" | "related" })[];
    profiles: { document_id: number; fields: AnalysisSection[] }[];
    sections: AnalysisSection[]; question: string; notice: string;
    coverage: { candidate_count: number; related_count: number; selected_count: number;
      evidence_count: number; candidate_limit: number; related_limit: number; enabled: boolean };
  };
};
