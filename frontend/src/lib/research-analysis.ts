import { InsightsDocument } from "./insights";
import { ComparisonEvidence, ComparisonRun } from "./comparison";

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
