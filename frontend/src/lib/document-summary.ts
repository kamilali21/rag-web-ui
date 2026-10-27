export type SummaryScope = "public" | "private";

export interface SummaryCitation {
  id: number;
  document_id: number;
  knowledge_base_id: number;
  scope: SummaryScope;
  file_name: string;
  page: number | null;
}

export interface SummaryClaim {
  text: string;
  citations: SummaryCitation[];
}

export interface SummarySection {
  key: string;
  title: string;
  claims: SummaryClaim[];
  unavailable: boolean;
}

export interface DocumentSummary {
  run_id?: number;
  status: "complete" | "insufficient_evidence";
  message: string | null;
  document: {
    id: number;
    knowledge_base_id: number;
    scope: SummaryScope;
    file_name: string;
  };
  sections: SummarySection[];
}
