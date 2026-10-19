export type InsightsScope = "public" | "private" | "both";
export type InsightsMode = "compare" | "analyse";
export interface InsightsDocument {
  id: number; knowledge_base_id: number; scope: "public" | "private";
  title: string; file_name: string; file_size: number; content_type: string; created_at: string;
  authors_text: string | null; department_id: number | null; department_name: string | null;
  document_type: string | null; publication_year: number | null; abstract: string | null;
}
export const INSIGHTS_PAGE_SIZE = 20;
export const MAX_INSIGHTS_DOCUMENTS = 5;
export const emptyInsightsFilters = { search: "", author: "", department_id: "", year_from: "", year_to: "", document_type: "" };
export function insightsDocumentsUrl(scope: InsightsScope, filters: typeof emptyInsightsFilters, beforeId: number | null) {
  const params = new URLSearchParams({ scope, limit: String(INSIGHTS_PAGE_SIZE) });
  for (const [key, value] of Object.entries(filters)) if (value.trim()) params.set(key, value.trim());
  if (beforeId !== null) params.set("before_id", String(beforeId));
  return `/api/insights/documents?${params}`;
}
