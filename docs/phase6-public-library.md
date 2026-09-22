# Phase 6: Public Library

<!-- Added by ChatGPT: public discovery and personal bookmarks using the existing corpus. -->

## Scope

The existing Library toggle now separates the published institutional catalog from
the original private collection workflow. Both modes keep the existing styling.
Researchers can browse, open/download, bookmark and query published evidence.
Explicitly authorized admins also have the basic uploader requested for this gate;
uploads remain drafts. Management forms belong to Phase 7.

## Contracts

- `GET /api/corpus/documents` retains its array response and descending ID cursor.
  New parameters: `search`, `author`, `department_id`, `year_from`, `year_to`,
  `document_type`, `bookmarked`. Pages remain bounded to 100; the UI fetches 21
  rows to display 20 and detect another page without a whole-corpus count.
- The compact response adds academic fields and the current user's
  `is_bookmarked`. A joined query avoids per-document metadata requests.
- Search uses the existing MySQL FULLTEXT index for normalized prefix words.
  Author substrings and short acronyms use escaped scoped substring filters.
  SQLite is a test fallback, not an exact replacement for MySQL tokenization.
- `POST` / `DELETE /api/corpus/documents/{id}/bookmark` are idempotent, session
  owner-derived and CSRF protected. No user ID is accepted. Only published
  canonical-corpus documents are eligible, even for admins. Existing bookmarks
  disappear from results when unpublished and return if republished; final
  document deletion cascades them. No copies of source files are created.
- `GET /api/corpus/documents/{id}/content?inline=true` allows PDF/plain-text
  viewing after the same authorization checks. Other types remain downloads.
  Markdown is plain text; responses disable caching and MIME sniffing.
- Query uses the existing `/api/corpus/query` evidence endpoint. Clickable source
  results open freshly authorized metadata. This is not the later public chat,
  selected-document retrieval, compare or analysis workflow.

## Boundaries

No migration, dependency, Docker configuration, volume or secret changes. The
canonical system owner, published-only retrieval checks and original private
collection IDs remain unchanged. Browser file links use existing session cookies.
Unrelated citation edits are preserved but excluded from this checkpoint.

The uploader uses the existing in-process background worker; durable queue/crash
recovery remains a deployment limitation. Closing the dialog retains progress
while Public remains mounted; switching mode does not cancel server ingestion.
Large-scale substring-search performance needs measured evaluation, not a claim
of constant-time lookup. HTTPS hardening remains the existing deployment gate.

## Verification

- Combined Phase 6/5/4/3/2 and baseline/provider tests: 192 passed on disposable
  MySQL 8; 180 passed, 12 MySQL-only skipped on SQLite.
- Frontend: 55 tests passed; TypeScript and production image build passed.
- Live browser acceptance and preservation receipts are recorded in
  `implementation-progress.md` when the gate closes.

## Recovery

Pre-change source: `researchiq-pre-phase6-20260922` at `6ee4063`.
Retained frontend image: `rag-web-ui-frontend:pre-phase6-20260922`.
Ignored restricted SQL backup: `.local/backups/pre-phase6-20260922.sql`.
Source/image checkpoints do not replace coordinated database/object/vector
backups. Preserve unrelated working changes before any recovery operation.
