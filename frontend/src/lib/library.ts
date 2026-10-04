// Added by ChatGPT: typed adapter for existing private-library responses; no new backend contract.
export interface LibraryTask {
  id: number;
  status: string;
  created_at?: string;
  updated_at?: string;
  error_message?: string | null;
}

export interface LibraryDocument {
  id: number;
  upload_id?: number | null;
  file_name: string;
  file_size: number;
  content_type: string;
  knowledge_base_id: number;
  created_at: string;
  processing_tasks: LibraryTask[];
}

export interface LibraryCollection {
  id: number;
  name: string;
  description?: string | null;
  documents: LibraryDocument[];
}

// Added by ChatGPT: MySQL timestamps arrive without a timezone and represent UTC.
export function documentDate(value: string) {
  return new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : value + "Z");
}

export function documentStatus(document: LibraryDocument) {
  const latest = [...(document.processing_tasks || [])].sort((a, b) => b.id - a.id)[0];
  const status = latest?.status.toLowerCase() || "unknown";
  const labels: Record<string, string> = {
    completed: "Ready", processing: "Processing", pending: "Pending", failed: "Failed",
  };
  return { status, label: labels[status] || "Unknown" };
}

export function documentSize(bytes: number) {
  if (!Number.isFinite(bytes) || bytes < 0) return "Unknown";
  if (bytes < 1024) return bytes + " B";
  const divisor = bytes < 1024 * 1024 ? 1024 : 1024 * 1024;
  return Number((bytes / divisor).toFixed(1)) + (divisor === 1024 ? " KB" : " MB");
}

// Added by ChatGPT: these are filename shortcuts until academic metadata exists server-side.
export const filenameFilters = [
  { label: "Papers", pattern: /paper/i, description: "Find filenames containing paper" },
  { label: "Theses", pattern: /thesis|theses|dissertation/i, description: "Find filenames containing thesis, theses, or dissertation" },
  { label: "Reports", pattern: /report/i, description: "Find filenames containing report" },
] as const;
