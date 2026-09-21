# Phase 4: Public Corpus

<!-- Added by ChatGPT: backend-only scope, lifecycle contracts and operational limits. -->

## Scope

The user approved moving **minimal working backend lifecycle endpoints** into
Phase 4 after the plan's Phase 7 boundary was clarified. No Public Library UI,
academic metadata editing, departments, bookmarks, compare/analyze, or chat-source
scope changes are included. Public querying here returns retrieved evidence,
not a new LLM/chat pipeline. Existing private routes and chats remain owner-only.

Startup, after Alembic, idempotently provisions:

- `researchiq_system` / `researchiq-system@internal.invalid`: inactive, system,
  not superuser, no password, no roles or API keys. It cannot sign in.
- `UAF Research Corpus`: `scope=public`, `is_system_managed=true`, owned by that
  internal account, never an individual administrator.

The existing unique user identity is the provisioning mutex. Conflicting human
identities, malformed ownership, or ambiguous system collections fail closed;
they are never converted or adopted. Existing migration head stays `riq_004`.
No schema change, new package, volume change, or private-data migration is needed.

## Authorization

All routes require the existing authenticated browser session. Cookie mutations
also require the existing exact Origin and bound CSRF token. Researcher reads
are restricted to explicitly published documents. Management requires the Phase 2
explicit admin role **and** an active exact-email allowlist entry. University email
or `is_superuser` alone is insufficient. Every service mutation checks this policy;
knowing a private document/task ID never grants access through corpus endpoints.

There is no automatic admin assignment. Administrators must be appointed through
the existing reviewed role/allowlist process. The generic private KB create/update
routes cannot create public KBs, transfer ownership, or delete the system corpus.

## API

Base: `/api/corpus`. Requests use existing session cookies, not API-key or legacy
JWT shortcuts when email verification is enabled.

| Method and suffix | Access / purpose |
| --- | --- |
| `GET /api/corpus` | Researcher: discover the shared corpus |
| `POST /api/corpus` | Admin: idempotently ensure provisioning |
| `GET /documents` | Published summaries; `limit` 1-100 and optional `before_id` |
| `GET /documents?include_unpublished=true` | Admin-only draft/archived inspection |
| `GET /documents/{id}` | Published summary; admin may set `include_unpublished=true` |
| `GET /documents/{id}/content` | Published attachment; admin may set `include_unpublished=true` to review drafts |
| `POST /query` | Researcher: `{query, top_k}`; query <=4000 chars, top_k 1-20 |
| `POST /documents/upload` | Admin: one multipart `file`, returns 202 with task ID |
| `GET /tasks/{id}` | Admin: processing state and document ID |
| `POST /tasks/{id}/retry` | Admin: retry failed retained source |
| `DELETE /tasks/{id}` | Admin: remove a failed upload and any partial document |
| `PATCH /documents/{id}` | Admin: `{file_name}` display-name edit, same file type |
| `POST /documents/{id}/publish` | Admin: expose a completed, indexed document |
| `POST /documents/{id}/unpublish` | Admin: return it to draft |
| `DELETE /documents/{id}` | Admin: hide and remove SQL/file/vector resources |

No author/title/year/department fields or generic ownership/scope setters are
accepted by these endpoints. The existing academic metadata row is used only for
publication state; its required title initially receives the filename. Actual
academic metadata workflows remain Phase 5. Missing metadata means unpublished.

## Lifecycle And Retrieval

Uploads allow PDF, DOCX, TXT and MD up to 20 MiB; filename/path checks, PDF magic
and bounded DOCX ZIP checks run before storage. The existing parser, chunker,
embedding factory, vector factory, `kb_<id>` naming and MinIO processing pipeline
are reused. Private processing retains its existing defaults. Public jobs link
partial documents to their task early, retain failed sources for retry, sanitize
failure details, and require explicit publication. Successful ingestion removes
the extra staged copy; failed removal is retried during document deletion.

Rename changes only the SQL display name, not immutable object paths/chunk IDs.
Reserved original filenames cannot be overwritten by a subsequent upload.
Deletion first durably archives the document, then removes its exact vector IDs,
permanent/staged objects and SQL rows. Cleanup failures retain a hidden,
retryable record. Archived deletion records cannot be republished.

Querying uses the existing vector collection, then checks each candidate chunk
against current SQL corpus ownership/publication. Returned text and document
identity come from authorized SQL chunks, not unchecked vector metadata.
Unpublishing during the vector call is rechecked before evidence is returned.
No LLM receives drafts/private evidence through this endpoint.

## Deliberate Limits

- Candidate retrieval is bounded to at most 100 vector hits, followed by SQL
  publication filtering. Many draft hits can reduce recall; indexed publication
  pushdown belongs in the later scope-aware retrieval work. Authorization never
  trades off for filling `top_k`.
- Rare admin writes serialize per corpus. Move to finer locks only if measured
  admin-write concurrency requires it. Reader queries do not take this mutex.
- BackgroundTasks is the existing in-process worker, not a durable queue.
  A process crash can strand pending/processing tasks. Inspect and mark only
  confirmed stopped jobs failed before retry; do not blindly reset active jobs.
  Automated recovery/worker hardening remains a deployment follow-up.
- Chroma is the deployed/tested vector backend. Other optional vector providers
  are not certified by Phase 4 live checks. No antivirus/content-disarm pipeline
  or advanced parser sandbox is introduced; only trusted admins can upload.
- Public corpus access means shared among authenticated researchers, not
  anonymous internet access. Production HTTPS, internal-only data services,
  sending quotas and general deployment hardening remain required.

## Verification And Recovery

Run the Phase 4, 3, 2 and baseline suites together using the disposable database
instructions in `implementation-progress.md`. Never point those fixtures at
production. Progress notes record actual counts/results and live-check limits.

Pre-Phase-4 source: `0860607`, tag `researchiq-phase3-password-flow-tested-20260919`.
New source rollback does not require deleting the corpus or system owner. Preserve
their rows, files, vectors and the Chroma `/data` volume. Older private-only code
simply does not expose the new corpus routes. Back up before any explicit recovery;
never drop volumes or broadly delete `kb_*` collections. The sign-in shortcut
removal does not disable verification for unfinished or future registrations.
