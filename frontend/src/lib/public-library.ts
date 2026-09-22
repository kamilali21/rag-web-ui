// Added by ChatGPT: public corpus contracts remain distinct from owner-scoped private documents.
export interface PublicDocument {
  id: number;
  knowledge_base_id: number;
  file_name: string;
  file_size: number;
  content_type: string;
  created_at: string;
  publication_status: string;
  title: string;
  authors_text: string | null;
  department_id: number | null;
  department_name: string | null;
  document_type: string | null;
  publication_year: number | null;
  is_bookmarked: boolean;
}

export interface Department { id: number; name: string; code: string; is_active: boolean }

export interface PublicMetadata {
  title: string;
  authors_text: string | null;
  abstract: string | null;
  department_id: number | null;
  document_type: string | null;
  publication_year: number | null;
  publication_date: string | null;
  supervisor: string | null;
  keywords: string[] | null;
  doi: string | null;
  language: string | null;
}

export interface CorpusEvidence {
  content: string;
  metadata: { chunk_id: string; document_id: number; file_name: string; page: number | null };
}

export const emptyPublicFilters = { search: "", author: "", department_id: "", year_from: "", year_to: "", document_type: "", bookmarked: "" };
export type PublicFilters = typeof emptyPublicFilters;
export const PUBLIC_PAGE_SIZE = 20;

export function publicDocumentsUrl(filters: PublicFilters, beforeId: number | null) {
  // One extra row detects the next page without a full-corpus count or download.
  const params = new URLSearchParams({ limit: String(PUBLIC_PAGE_SIZE + 1) });
  for (const [key, value] of Object.entries(filters)) if (value.trim()) params.set(key, value.trim());
  if (beforeId !== null) params.set("before_id", String(beforeId));
  return `/api/corpus/documents?${params}`;
}
