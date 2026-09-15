"use client";

import { File } from "lucide-react";
import { formatDistanceToNow, isValid } from "date-fns";
import { documentDate, documentSize, documentStatus, LibraryDocument } from "@/lib/library";

// Added by ChatGPT: the same responsive document rows are used for Library and collection views.
export function LibraryTable({ documents, onSelect }: {
  documents: LibraryDocument[];
  onSelect: (document: LibraryDocument) => void;
}) {
  return (
    <table className="library-table" aria-label="Library documents">
      <colgroup><col style={{ width: "40%" }} /><col style={{ width: "18%" }} /><col style={{ width: "26%" }} /><col style={{ width: "16%" }} /></colgroup>
      <thead><tr><th scope="col">Name</th><th scope="col">Size</th><th scope="col">Created</th><th scope="col">Status</th></tr></thead>
      <tbody>
        {documents.map((document) => {
          const { status, label } = documentStatus(document);
          const created = documentDate(document.created_at);
          const extension = document.file_name.split(".").pop()?.slice(0, 4) || "file";
          return (
            <tr key={document.id}>
              <td>
                <button className="document-name" title={document.file_name} onClick={() => onSelect(document)} aria-label={`Details for ${document.file_name}`}>
                  <span className="document-icon" aria-hidden="true"><File strokeWidth={1.6} /><span>{extension}</span></span>
                  <span className="document-label">{document.file_name}</span>
                </button>
              </td>
              <td>{documentSize(document.file_size)}</td>
              <td>{isValid(created) ? <time dateTime={created.toISOString()} title={created.toLocaleString()}>{formatDistanceToNow(created, { addSuffix: true })}</time> : "Unknown"}</td>
              <td><span className="document-status" data-status={status}>{label}</span></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
