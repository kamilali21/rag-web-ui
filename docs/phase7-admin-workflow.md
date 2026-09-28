# Phase 7: Admin Corpus Workflow

<!-- Added by ChatGPT: current corpus services exposed through an admin-only management surface. -->

## Scope And Decisions

Public Library remains the published researcher catalog. Effective admins can
open **Manage corpus**, with a paginated upload inbox and real lifecycle actions.
No Phase 8 private-library redesign, account/role administration, public chat
scope, compare or analyze features are included.

The user delegated the archive decision to implementation judgment. This gate
keeps the existing safe terminal archive state rather than adding another schema:

| Action | Effect |
| --- | --- |
| Publish | Requires successful ingestion and indexed content; exposes the document to researchers. |
| Unpublish | Returns to draft, preserving files and allowing later publication. |
| Archive | Permanently hides that document identity, retaining its files and vectors until deletion. No restore-to-published shortcut. |
| Delete | Hides first, then cleans exact relational, object and vector resources. A cleanup failure stays hidden and can be retried. |

Archive cannot undo a deletion tombstone. This avoids accidentally making
partially deleted content public. Reversible withdrawal is **Unpublish**, not
Archive. The confirmation dialogs state these consequences before any request.
Archived rows can be inspected by authorized admins and deleted, not edited or
republished. A new upload is a new controlled ingestion, not restoration.

## Backend

- `GET /api/corpus/tasks`: admin-only inbox, descending ID cursor, `before_id`,
  `limit` (1-100), escaped title/filename `search` (200 characters), processing
  `status` and `publication_status`. Joins existing task/upload/document/metadata
  rows in one bounded result. Failed uploads without a document remain visible.
- `POST /api/corpus/documents/{id}/archive`: current corpus-admin authorization,
  existing corpus/document locks, processing conflict protection, terminal hide.
- Upload, metadata PATCH, rename, publish/unpublish, task retry, content viewing,
  deletion and department management reuse the Phase 4/5 endpoints and services.
- Server guards never trust UI role state. Enumerating tasks and requesting
  unpublished content require current explicit role plus exact allowlisting;
  private IDs remain forbidden even to admins. Unsafe cookie requests retain
  Phase 3 Origin/CSRF enforcement. Provider errors and storage paths are not
  exposed through the task inbox.

No migration, package or Docker configuration changes. Schema remains `riq_004`.
System corpus ownership, Chroma `/data`, SMTP/password/session handling and the
private RAG/citation pipeline remain unchanged.

## Frontend

- Management shows processing/publication separately, server-side filters,
  cursor pages, refresh, active-page polling, errors and empty states.
- Upload still uses the existing single-file validation and background worker.
  After Ready, metadata is entered from the row actions, then publication is
  explicitly confirmed. Failed retained uploads expose Retry processing.
- Metadata editor includes title, authors, department, type, year/date, abstract,
  supervisor, keywords, DOI and language. Only changed academic fields are
  submitted, so unrelated fields and inactive existing department references
  are preserved. Filename changes are a separate operation.
- Department creation/edit/activation uses existing normalized reference APIs;
  deactivation does not destroy historical assignments. No invented UAF seeds.
- Row actions use the existing Radix dependency. Dialogs share 18px headings,
  14px controls, a 760px maximum form width (500px confirmations), viewport
  bounds, scrollable bodies and persistent footer actions. Native validation,
  stable accessible field names, focus handling and visible save failures remain
  available on both desktop and mobile.

## Verification And Recovery

The exact final automated and live results are recorded in
`implementation-progress.md`. The regression command adds
`tests/test_phase7_admin_workflow.py` before the Phase 6/5/4/3/2 and baseline suites.
MySQL testing uses only the guarded disposable `researchiq_phase2_test` schema;
never run those fixtures on production.

Rollback source: Phase 6 `c912772`, tag `researchiq-phase6-tested-20260922`.
Retained image: `rag-web-ui-frontend:phase6-tested-20260922`.
Restricted ignored backup: `.local/backups/pre-phase7-20260922.sql`.
Code rollback does not undo actual admin publication or deletion operations.
Do not restore an old SQL backup over newer user uploads. Coordinated
database/object/vector recovery remains necessary for real data restoration.

## Remaining Limits

- The upstream worker is in-process, not a durable queue. A crash during
  processing can leave an active task requiring operator diagnosis; this UI
  retries failed tasks and does not guess that a running worker is dead.
- Admin substring search and publication filtering may scan scoped upload rows;
  pages are bounded, but large-corpus latency still needs measurement. Existing
  FK/primary-key cursor access is retained; no speculative indexes or caches.
- Department reference lists are paginated by the API and loaded together for
  selectors; extremely large department lists need a searchable selector.
- Final security/deployment hardening, malware scanning, HTTPS and durable
  job recovery are not certified by this feature checkpoint.
