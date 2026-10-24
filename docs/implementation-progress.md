# ResearchIQ Integration Progress

<!-- Added by ChatGPT: implementation gates and evidence for the adaptable master plan. -->

Source: version 1.0 of `ResearchIQ_Master_Integration_Plan.pdf` (15 September
2026), governed by the appended 17 October amendment and 19 October future-extension note at
`output/pdf/ResearchIQ_Master_Integration_Plan.pdf`. The dated original remains
byte-identical; the Projects-root working copy is synchronized to the amendment.

## Working Agreement

- Complete and verify one feature before starting the next.
- Extend the current FastAPI/MySQL/MinIO/Chroma/Next.js application.
- Keep existing private ownership and API compatibility until each replacement is tested.
- Use Alembic for schema changes; test migrations on disposable data before applying them.
- Record deviations, tests, limitations, and the next gate here.
- A mock or sample UI is not a completed backend feature.

## Current Gate: Phase 17 - Contradiction / Evidence Interpretation (not started)

### Analyse recovery correction - 24 October 2026

- Corrected bounded profile-output handling and SDK malformed-completion retry;
  added owner-checked request recovery and **Resume last analysis** in Insights.
- 74 affected backend tests and 22 Insights tests passed; TypeScript and frontend
  production build passed. Deployed frontend/backend and checked served assets.
- Full synthetic fixture passed: Analyse 54.37s, Compare 25.36s, saved recovery,
  permission/revocation checks and original SQL/object/vector snapshot equality.
- Receipt: [Phase 16 correction](phase16-analyze.md). Recovery tag:
  `researchiq-analyze-recovery-20261024`. No schema/model-setting change or push.

### Phase 16 closure - 23 October 2026

- Added selected-paper research profiles, bounded related public discovery and
  seven cited synthesis sections, with saved evidence, permission rechecks and
  reopening inside Insights. No schema change; database remains at `riq_007`.
- Backend regression: 444 passed, 43 skipped; final affected suite after provider
  corrections: 69 passed. Frontend: 109 passed; TypeScript and production build passed.
- Synthetic Analyse passed in 83.65 seconds. A separate final comparison regression
  passed in 27.95 seconds after correcting mandatory reasoning, transient routing
  and SDK truncation handling. Original SQL/object/vector snapshots matched after cleanup.
- Frontend and backend source deployed; health, served assets and anonymous access
  checks passed. Browser visual inspection remains unavailable.
- Receipt: [Phase 16](phase16-analyze.md). Tag: `researchiq-phase16-analyze-20261023`.

### Phase 15 closure - 22 October 2026

- Implemented exact-document comparison of 2-5 selected papers, structured
  criteria, validated citations, compatibility interpretation and owner-private
  saved results/evidence snapshots. Analyse is the next gate.
- Backend: 413 passed, 43 skipped; focused comparison: 30 passed. Disposable
  MySQL migration: 1 passed. Frontend: 103 passed; TypeScript and production build passed.
- Deployed frontend and backend source; applied additive revision `riq_007`
  after a local SQL backup. All values in the 22 original tables were unchanged
  immediately after migration. Health, served comparison assets and anonymous
  API rejection were verified.
- The user clarified on 22 October that declining live acceptance was accidental.
  Synthetic public/private upload/indexing, provider comparison (6.28 seconds),
  citations, saved reopening/idempotency, PDF access and revocation checks passed.
  Cleanup confirmed original SQL rows, MinIO objects and vector IDs unchanged.
  Browser visual inspection remains unavailable; frontend rendering tests pass.
- Receipt and recovery notes: [Phase 15](phase15-comparison.md). Annotated tag:
  `researchiq-phase15-compare-20261022`.
- Restored Library publication request actions and removed only the admin
  dashboard submission shortcut in `c506539`, tagged
  `researchiq-library-actions-20261021`.

### Phase 14 closure - Insights on Real Catalog Data - 19 October 2026

- Replaced sample Insights papers with an authenticated, bounded real catalog:
  published/ready Public, owner-only ready Private, and their Both union.
- Search, academic filters, cursor pagination and up-to-five selection reuse
  Library styling. Compare/Analyse configuration revalidates exact IDs and opens
  a temporary metadata workspace; no generated analysis or persisted runs yet.
- Full backend: 383 passed, 42 skipped. Full frontend: 99 passed; corrected
  Insights tests rerun: 9 passed. TypeScript and production frontend build passed.
  Local deployment/served assets and health verified. Live nginx acceptance passed
  on nine real public papers plus isolated synthetic ownership/readiness fixtures.
- Existing application rows matched before/after synthetic cleanup; schema stays
  `riq_006`; no Chroma changes. Browser visual inspection remains unavailable.
- Checkpoint and deployment receipt: [Phase 14](phase14-insights.md), annotated
  tag `researchiq-phase14-insights-20261019`. Includes the approved dashboard and
  Phase 13 reliability [follow-up](dashboard-summary-followup-20261019.md).
- Added future department/supervisor review scoping and similarity/plagiarism
  assistance to the working PDF and [planning note](future-supervision-and-similarity-review.md).
  These remain deferred, without renumbering or changing current permissions.

### Phase 13 closure - Structured Document Summaries - 17 October 2026

- Phase 13 adds temporary structured summaries through
  `POST /api/retrieval/documents/summarize`; no database schema, Alembic
  revision, chat history, or saved-summary state was added.
- Summaries contain objective, methods/context, key findings, limitations, and
  implications/conclusion. Retrieval is restricted to the exact requested
  document and existing scope rules: private documents must be owner-owned and
  ready; public documents must be published and ready.
- The service treats document text as untrusted, validates structured model
  output, maps every evidence ID back to retrieved SQL-backed chunk metadata,
  rejects unknown citations, and rechecks current access after generation.
  Unsupported sections are explicitly marked as not identified in evidence.
- Added a Summarize action to ready private and published public document
  details. Unpublished corpus drafts do not show it. Citation links open the
  source PDF at the cited page. Results are temporary and not saved.
- Phase 13 API tests: 15 passed, 1 opt-in provider test skipped by default.
  The opt-in test was run against fabricated paper text in isolated SQLite
  fixtures with the configured free provider: 1 passed; citations matched the
  exact source document and no chat messages were created. Fixture teardown
  removed all synthetic records.
- Full backend regression: 352 passed, 42 skipped. Frontend: 90 tests across
  16 suites passed; TypeScript passed; optimized Docker production build
  passed. Existing Next.js ESLint-option and Tailwind line-clamp warnings remain.
- No database migration or user-data changes were made. Recovery checkpoint:
  `researchiq-phase13-summary-20261017`.
- Next gate is Phase 14: Insights on real catalog data.

### Phase 12 closure - Researcher Portfolio and Publication Requests - 17 October 2026

- Phase 12 implementation and synthetic acceptance completed on 16 October;
  the controlling amendment on pages 24-26 of the working Master Plan formally
  closes the gate and records the approved Phase 13-22 renumbering.
- The dated original PDF remains unchanged. The amended working PDF is committed
  under `output/pdf/ResearchIQ_Master_Integration_Plan.pdf` and synchronized to
  the Projects-root working copy.
- Closure relies on the Phase 12 verification receipt below and the recovery tag
  `researchiq-phase12-recovery-20261016`; no completed phase numbers or historic
  tags were rewritten.
- Phase 13 is the next gate: implement temporary, citation-backed structured
  single-document summaries with exact Phase 11 retrieval in both library
  detail views. Chat commands and saved summary history are out of scope.

### Researcher portfolio and publication requests - 16 October 2026

- The approved Phase 12 insertion shifts the previously planned Phases 12-21 to
  13-22. Completed phase numbers and historical tags stay unchanged. The dated
  original Master Integration Plan PDF remains unchanged; the working-copy
  amendment is now recorded in the 17 October closure entry above.
- Added profile/request/withdrawal models, revision `riq_006`, and scoped APIs.
  Admin review reads only the document attached to a request; generic private
  library routes remain owner-only.
- Approval stages a separate managed-public-corpus copy and publishes only after
  indexing succeeds. Per-request consent controls the limited public researcher
  card. Approved withdrawals use the existing archive lifecycle.
- Added the Profile page, private-library Request publication dialog, public
  Library Requests action and pending badge, and consented researcher card.
- Removed API Keys from dashboard navigation, moved Profile to the final
  position, and marked Insights as a coming-soon sample preview. Live corpus
  analysis remains unconnected; the sample page explains the planned features.
- Phase 12 implementation, all tests and synthetic live acceptance passed.
  Live migration `riq_006` followed the disposable-MySQL gate and a verified
  backup; pre/post SQL totals match, and exact synthetic fixtures were removed.
  Frontend: 80 tests, TypeScript and production build pass. The free-model router
  `openrouter/free` replaced the pinned model after it returned 404. The backend
  and frontend were refreshed; the Profile page route returns HTTP 200. The
  recovery snapshot is tagged `researchiq-phase12-recovery-20261016`; the PDF
  amendment remains a Phase 12 closure gate. The follow-up navigation/Insights
  changes pass 6 focused Jest tests, and the production build passes. Do not
  Phase 12 was not formally closed until the working-plan amendment on 17 October.

### Chat reliability and dashboard maintenance — 17 October 2026

- Configured OpenRouter's `openrouter/free` router and added one bounded,
  pre-output 429 retry that respects `Retry-After` up to five seconds. Disabled
  overlapping SDK retries for OpenRouter; citation and source checks remain.
- Updated the user's dashboard publication count and publication-request
  shortcut, dark-mode library filters, Insights lock indicator, profile sidebar
  card and account popover. Sign out is available inside the profile popover
  and on the Profile page using the existing logout flow.
- Backend chat/retrieval tests: **51 passed**; frontend: **87 passed**; focused
  account-menu tests: **4 passed**; TypeScript passed. The Docker production
  frontend build passed. Only the frontend container was rebuilt/restarted;
  `/dashboard` returned HTTP 200.
- Browser visual acceptance and a real corpus-chat replay were unavailable in
  this session. A synthetic JSON-mode provider check passed; no user prompt or
  research document was sent. This maintenance checkpoint does not close Phase
  12 at that historical checkpoint; its working-plan amendment later closed the
  gate on 17 October.
- Recovery tag: `researchiq-chat-dashboard-20261017`.

### Security cleanup and deployment preparation - 9-10 October 2026

Maintenance scope and verification are recorded in
[security-cleanup-20261009.md](security-cleanup-20261009.md). The migration helpers
and recovery manifest were committed at `48761da`
(`researchiq-windows-migration-20261009`); private SQL dumps remain local/ignored.
The separate production Compose configuration is prepared for a future domain
and server. It does not mark Phase 19 or 21 complete or advance the feature gate.
Frontend checkpoint image `researchiq-frontend:security-20261010` builds;
Jest **76/76** and TypeScript pass. The current Windows frontend was left on
its prior image. ESLint has existing errors and warnings documented in the
cleanup report; this checkpoint does not claim a clean lint run or public launch.

### Chat citation placement and branding - 9 October 2026

- Completed the interrupted corpus-chat checkpoint: `ac5a04f`, tagged
  `researchiq-chat-corpus-20261008`.
- Keep provider JSON object mode, with short separately cited answer blocks.
  Validate the entire envelope before output; preserve reference validation,
  source rechecks, bounded output, legacy block compatibility and saved messages.
- Replaced the RAG Web UI chat avatar with a native emerald book/lime leaf mark.
  No frontend request, authentication, dependency or schema changes.
- Backend **322 passed / 40 skips**; disposable MySQL **126 passed**. Live
  current Both-scope conversation replay produced five separately cited claims
  and reopened identically; temporary fixtures removed, original rows preserved.
- Frontend **74 passed**, TypeScript and production build passed. Deployed image
  `researchiq-frontend:chat-polish-20261009`; live bundle/SVG/hero checks passed.
  Final warm cited-answer/reopen check passed in 16.09s. Checkpoint tag:
  `researchiq-chat-polish-20261009`. Browser visual acceptance remains unavailable.
- Detailed status, phase evidence, security boundaries and next formal task:
  `docs/project-status-20261009.md`. Summary/Compare/Analyze/Gap workflows were
  assessed but not begun; Phase 12 and later phases remain unfinished.

### Corpus-chat runtime correction - 8 October 2026

- Fixed missing embedding weights after container recreation with a persistent,
  verified MiniLM cache and local-first loading. No embedding/index change.
- Query rewriting now fails back to the user's question instead of blocking
  retrieval; provider requests are bounded. Added exact greeting typo handling.
- With approval, pinned the zero-cost `apodex/apodex-1.1-mini:free` model and used
  supported JSON object output. Application citation/permission checks remain
  strict. No frontend, authentication, schema or research-data change.
- Full backend **314 passed / 40 skips**; disposable MySQL **118 passed**.
  Real Public history replay, broad question, follow-up, Private/Both cited
  answers and saved reopening passed. Temporary fixtures removed; original
  research rows/conversations preserved. Backend deployed.
- Checkpoint `researchiq-chat-corpus-20261008`; details, initial failed attempts,
  measured latency, provider limits and recovery: `docs/chat-reliability.md`.
  Phase 12 has not started.

### Chat reliability correction — 7 October 2026

- Reproduced the reported greeting failure: the live model emitted an uncited
  greeting that the research-answer validator rejected. Complete greetings now
  bypass providers after authorization, while research questions remain cited.
- Added one pre-output retry for malformed generation, filtered conversational
  noise/error messages from model history, and reused the local embedding model
  with serialized initialization. No authentication/schema/provider change.
- Full backend **307 passed / 40 skips**; disposable MySQL **111 passed**.
  Live greetings, synthetic PDF processing, cited answer, follow-up and saved
  reopening passed; fixtures removed and existing research preserved.
- Backend fix deployed; details and measurements: `docs/chat-reliability.md`.
  Phase 12 has not started.

### Phase 11 completion and authentication hero checkpoint — 7 October 2026

- Completed `POST /api/retrieval/documents/query` using the existing exact-selection
  service. Required bounded integer IDs, complete-selection authorization, current
  readiness/publication, native vector filters and fresh SQL evidence checks;
  existing broad-scope routes and chat behavior remain unchanged.
- Full isolated backend suite: **295 passed, 40 environment-specific skips**.
  Focused Phase 9–11 suite: **98 passed, 1 MySQL-only skip**; disposable MySQL:
  **99 passed**. No production schema change; revision is still `riq_005`.
- Deployed backend route and passed live Public/Private/Both exact retrieval,
  SQL citation metadata, foreign-user denial, validation and session/CSRF/origin
  checks. Restored the checksum-verified original MiniLM cache after a first
  attempt encountered missing weights. No LLM call or research-data mutation.
- Every original research row, MinIO object and Chroma vector was preserved.
  Temporary sessions removed; an independently verified concurrent revocation of
  an existing session explains the aggregate fingerprint mismatch.
- Included the previously deployed public auth hero and supplied UAF photograph.
  Frontend evidence: **74 tests**, TypeScript and production build passed; live
  login/register checks passed. Authentication handlers/forms are unchanged.
  Browser visual sign-off remains unavailable.
- Checkpoint tag: `researchiq-phase11-verified-20261007`. Details and receipts:
  `docs/phase11-document-scoped-retrieval.md` and `docs/auth-hero-presentation.md`.
- At the Phase 11 checkpoint, the next task was Phase 12 structured
  single-document summary with citations. The approved 16 October insertion
  places researcher publication workflow at Phase 12, so the summary is now
  Phase 13 and remains unstarted.

### Phase 11 started — 6 October 2026

- Phase 10 completion checkpoint: `903619e`, tag
  `researchiq-phase10-verified-20261006`.
- Added exact document-ID selection to the existing permission-scoped retrieval
  service. Missing/foreign/not-ready selections fail before vector search;
  selected IDs constrain both native filters and fresh SQL evidence checks.
- Combined Phase 9/10/11 regression: 72 passed, 1 MySQL-only skip; MySQL: 73 passed. Read-only
  live checks returned only the selected private/public document's chunks.
- This is an incremental service checkpoint. Next: authenticated API/schema
  integration and acceptance for exact selection, before closing Phase 11.
- Details: `docs/phase11-document-scoped-retrieval.md`.

### Phase 10 completion — 6 October 2026

- Research Assistant reuses chat with persisted Public/Private/Both scope,
  SQL-authorized evidence, structured citation validation and saved-source checks.
- Final focused regression: 60 passed, 1 MySQL-only skip. Final disposable MySQL
  gate: 113 passed. Frontend: 74 passed plus production build/type checks.
- Live synthetic acceptance passed all three scopes, cited streams, follow-up,
  abstention, saved reopening, PDF access and publication withdrawal.
- All original data was preserved; two concurrently added messages in an existing
  conversation explain the aggregate hash difference and were independently
  reconciled. Exact test fixtures and temporary sessions were removed.
- Deployed the corrected error UI and backend. With user approval, switched the
  overloaded NVIDIA model to the free router. Three final requests needed one
  explicit retry; provider reliability remains a documented limitation.
- Details, backups, deployment and receipts: `docs/phase10-research-assistant.md`.
- Next: Phase 11 exact document selection through the existing retrieval service.

### Phase 9 completion - 5 October 2026

- Public/Private/Both searches now constrain native vector queries to SQL-permitted
  documents, then recheck authorization/readiness/publication in a fresh snapshot.
  Existing public queries, private/API-key retrieval and private chat share it.
- Full backend suite: 220 passed, 39 skips; final focused Phase 9 suite: 26 passed;
  disposable MySQL authorization/public-corpus/retrieval gate: 80 passed.
- The 4 October live gate verified both users/all scopes, hidden drafts/foreign
  files, publication withdrawal, PDF download, real cited streaming and saved-chat
  reopen. Container recreation lost its final receipt; exact fixture/session
  removal was independently confirmed afterward.
- The 5 October repeat was interrupted by a stalled cold model download. Its
  exact test fixture was recovered and deleted; all three original documents,
  original SQL rows and MinIO/Chroma fingerprints are unchanged, sessions removed,
  revision `riq_004`. The failed repeat and successful cleanup receipts are kept.
- Runtime model recovery is ongoing; Phase 10 needs fresh live acceptance before
  its checkpoint. Browser tools still expose no connected browser.
- Details and recovery evidence: `docs/phase9-scope-aware-retrieval.md`.
- Next existing-plan task: reuse chat for Research Assistant source scopes and
  validate citations against deterministic SQL-backed evidence IDs.

### Phase 9 started - 4 October 2026

- Phase 8 completion checkpoint: `ad8960e`, tag
  `researchiq-phase8-verified-20261004`.
- Added SQL source resolution for Public/Private/Both: latest Ready documents,
  current-user private ownership, canonical published corpus, no admin bypass,
  invalid/empty scope fail-closed behavior. No vector/LLM call is made here.
- Seven authorization tests and six read-only live MySQL checks for two users
  passed. No session/data/schema changes and no live chat behavior change.
- Next existing-plan task: constrain existing vector searches to this permitted
  document set before retrieval, then recheck SQL permission before exposing
  evidence. Phase 9 remains in progress; Phase 10 has not started.
- Details: `docs/phase9-scope-aware-retrieval.md`.

### Phase 8 completion - 4 October 2026

- Completed Private Library SQL search/filter/pagination, persistent staged and
  failed-upload visibility, owner-only content viewing and exact-file deletion.
  Storage failures retain retryable references and display Failed. Active jobs
  cannot be deleted; private access has no admin override.
- Reused ingestion, original KB routes and existing SQL/MinIO/Chroma stores.
  Schema remains `riq_004`; no production migration or auth/code redesign.
- Validation: 194 backend regression tests passed (39 environment-specific
  skips); final Phase 8 MySQL suite passed all 12 checks in the isolated
  `researchiq_phase2_test` schema; all 70 frontend tests, TypeScript and
  production build passed. An existing OTP UI test now waits for its effect
  before asserting cooldown; authentication code is unchanged.
- Live synthetic PDF: upload, pending/ready catalog, SQL/chunk/vector agreement,
  authenticated PDF content, retrieval, streamed cited answer, saved-chat reopen,
  cross-owner 404s, real parser failure visibility, file/upload/collection cleanup.
  All original SQL records, both existing documents, MinIO object fingerprints
  and Chroma vector fingerprints match before/after. Four temporary sessions and
  the exact synthetic collection/chat were removed.
- Cold embedding startup took roughly five minutes, exceeding the initial
  240-second test deadline. Resumed the same completed job; no worker was killed.
  The final receipt normalizes JSON tuple/list representation before comparison.
- Deployed `researchiq-frontend:phase8-final-20261004` and restarted only backend;
  frontend is healthy and live bundles expose the catalog, deletion, pagination
  and filter disclosure. Browser inventory still reports no connected browser
  even after the user attached the page; rendered-browser acceptance is not
  claimed. This completion uses automated UI and live API acceptance.
- Backup/rollback and scope boundaries: `docs/phase8-private-library.md`.
  Next existing-plan task: Phase 9 Public/Private/Both authorization and vector
  retrieval constraints, starting with SQL resolution of permitted sources.

### Phase 8 started - 4 October 2026

- Re-read the full master plan, Phase 7 workflow and current history. Completed
  the three requested frontend corrections at `ed5a0ee` before beginning Phase 8.
- Mapped the existing owner-scoped KB routes, authorization helpers, uploader,
  private catalog, task polling, chat and collection lifecycle to the plan in
  `phase8-private-library.md`. No new architecture or replacement ingestion.
- First increment: filter existing private document rows by their latest
  processing status, combining with filename/category/collection selection;
  display backend `completed` as Ready. Clear resets the new filter too.
- Twenty-three frontend tests and TypeScript passed. Live read-only API checks
  passed for two existing verified users: identity, owned collections/documents,
  and foreign-private-KB denial (six checks, one current document examined).
  Exact temporary maintenance sessions were deleted in a finally block; no
  documents, roles or pre-existing sessions were changed.
- Phase 8 remains in progress. Persistent pre-document task visibility, safe
  per-document deletion and server-side personal catalog filtering/pagination
  remain unfinished. No Phase 9 or later workflow was started.
- Production build passed; only frontend was recreated with
  `researchiq-frontend:phase8-status-20261004`. Live HTTP/bundle checks confirm
  the public disclosure and private state filter are served. The other five
  services stayed running. Browser visual acceptance remains pending.

### Final requested frontend corrections - 4 October 2026

- Restored work interrupted after `ac6a1e6`: compact public document rows by
  placing bookmark beside both title and type/size, with single-line desktop
  titles/metadata and the shared 54px row minimum. Mobile can still wrap.
- Added the right-hand search-bar filter toggle, initially collapsed, with
  expanded state, keyboard support and active-filter count. Search remains
  available through Enter or the search icon while collapsed. Filter drafts
  and applied state survive hiding/showing the panel.
- Private/Public Library now share full-width search bars. No API, schema,
  data, authentication or RAG change. Twenty-two frontend tests, TypeScript
  and production build passed. Frontend image: `researchiq-frontend:rows-20261004`.
- Browser inventory is still empty. The user installed VS Code's
  `techer.open-in-browser`, which launches files but does not provide this chat
  with browser automation. Visual acceptance is not claimed. Existing warning
  classes are unchanged. Phase 8 is authorized after these corrections.

### Bounded frontend polish - 3 October 2026

- Second screenshot follow-up: restored the Private Library header upload glow.
  Public/Private Library, corpus management and the Insights selection footer
  now share a full-height flex list layout with auto top margin on footers.
  Short/empty pages place controls at the bottom; long pages keep them after
  content without overlaying rows. Thirty-six affected frontend tests,
  TypeScript and production build passed. Deployed only frontend image
  `researchiq-frontend:footers-20261003`; live HTTP/CSS check passed and frontend
  is healthy. Rendered browser verification remains unavailable in this session.

- Follow-up from the user's screenshot: replaced the oversized three-column
  filter grid with a compact wrapping desktop row, grouped From/To under Year
  range, and aligned Search/Clear with the controls. Narrow screens retain a
  two-column layout. Restored the original `primary-action premium-action`
  animated glow on both Public Query corpus and Add Documents as requested.
  All filter behavior remains unchanged. Fifteen Public Library tests,
  TypeScript and production build passed. Deployed only frontend image
  `researchiq-frontend:filters-20261003` (`4d092bf4a199`); live Nginx served the
  new styles and frontend was healthy. Other containers stayed running.
  This supersedes the earlier public-button hierarchy/three-column layout below.

- Applied the user's separate frontend-only audit before substantial Phase 8:
  reused existing buttons, clarified public action hierarchy, aligned filters,
  associated bookmarks with titles, top-aligned public rows, muted missing
  metadata, and separated refresh from pagination. Visible branding is now
  `rAGRI search` in the shared desktop/mobile shell, password and email login,
  registration, browser title and chat logo alternative text.
- Sidebar invisibility/background truncation was not reproduced in a browser.
  Source already used a full-height fixed sidebar and a mobile drawer below
  1024px. Shared CSS now explicitly sets navigation contrast, prevents shrinking
  and permits viewport scrolling; sign-out retains its bottom placement.
- Verification: 45 tests passed in four relevant suites (`library`,
  `public-library`, `corpus-manager`, `email-login`); TypeScript passed with
  `--noEmit --incremental false`; the production Next.js build passed. Existing
  Next.js config, Browserslist and redundant line-clamp warnings remain.
- The packaged image served login, registration and Library HTML successfully
  with the new browser title in an isolated container with no network or mounts.
  The temporary container was stopped afterward. This checks HTTP packaging,
  not authenticated interaction or visual layout.
- The verification Dockerfile lives outside the repository in the recovery
  directory. Image: `researchiq-frontend:polish-20261003`; previous local image
  retained as `researchiq-frontend:pre-polish-20261003`. No host dependencies,
  package/lockfile, backend, API, database, auth behavior or routing changed.
- On resuming the interrupted task, Docker had no application containers.
  The full stack was not restarted. At that checkpoint, browser visual acceptance
  and deployment remained pending; this was not a new phase.
  No unrelated Phase 8 implementation was started.
- After the user restarted the stack, confirmed it still served the old frontend
  image `997b8c5f6013`. Deployed the tested polish image `d9dbee5c7076` using
  `docker compose up -d --no-deps --no-build frontend`; other services stayed
  running. Live Nginx checks returned HTTP 200, the `rAGRI search` title and new
  Library CSS; unauthenticated `/api/auth/me` still returned 401. Frontend healthy.
  Chrome and in-app browser connection attempts both returned unavailable, so
  authenticated visual/interaction acceptance is still pending.

### Windows stale-test cleanup and Phase 7 live API acceptance - 3 October 2026

- The user cancelled recovery of the old Linux MinIO/Chroma stores and explicitly
  authorized removal of old disposable documents proven to have neither source
  objects nor vectors. No Linux restore or index rebuild was performed.
- Removed document IDs `1,2,3,4,9,10,11,18,19,23,24,25,26,27`, their 571 chunks,
  dependent tasks/uploads, five academic metadata rows and one bookmark. Also
  removed the old failed task `1`/upload `1`, whose source was absent. Public
  documents used the existing archive-first deletion service. Private documents
  required exact ORM cleanup: the existing API only deletes whole private KBs,
  which would also destroy the protected new document in KB 1.
- Preserved document `28` (`Getting started with OneDrive.pdf`, KB 1), task `28`,
  upload `26`, all five chunks, its exact MinIO bytes and five vector payloads.
  All users, roles, allowlisting, pre-existing authentication/session records,
  departments, KBs, conversations, messages and `riq_004` were unchanged by
  value-hash comparison. No orphan upload rows remain. Empty KBs were retained.
- Before cleanup, saved a complete MySQL dump and protected-data receipts outside
  the repository at `C:/Users/tayya/Projects/ResearchIQ-recovery/20261003-cleanup/`.
  The dump SHA-256 is `27d28adc0eb87fd0626ae9c8f8917971a3036ba03525f4bca459a548ea5a1e94`.
  These private backup/receipt files must not be committed.
- The user reports a fresh Windows PDF upload, successful processing/indexing,
  retrieval and correct generated answer, persisted after refresh. A transient
  post-answer rendering error was reported; no reproducible failure has been
  established and no broad debugging or code change was undertaken.
- Completed a bounded live HTTP gate through existing Nginx using temporary
  maintenance sessions for existing admin/researcher identities. Fifty asserted
  responses (including status polling, not fifty independent tests) covered real
  public upload/ingestion, draft hiding, inbox filters, metadata validation/edit,
  department create/edit/deactivate, rename, publish/unpublish, content download,
  real Chroma evidence, bookmarks, terminal archive and deletion. Researcher
  management and invalid-CSRF requests were denied. A synthetic failed task with
  a valid retained source retried through the actual endpoint/background worker
  and completed successfully. This is not live SMTP/password-issuance testing.
- Removed exact synthetic documents `29,30`, tasks `29,30`, department `5` and
  temporary sessions. Full post-gate receipts matched all protected SQL rows,
  MinIO object bytes and vectors. Final state: one document, five chunks, one
  task, one upload, no public documents/bookmarks; seven users retained.
- Existing automated evidence remains 196 MySQL passes, 184 SQLite passes/12
  skips, 66 frontend tests and TypeScript/build success at the recovered Phase 7
  checkpoint. These suites were not rerun on Windows: application code was not
  changed, and the running images do not include pytest/Jest/TypeScript tooling.
- The user confirmed the refresh check worked: Private Library retains the new
  OneDrive PDF, Public Library has no old files, and Manage corpus opens. Together
  with the recorded automated and live evidence, this closes Phase 7. The local
  completion tag is `researchiq-phase7-verified-20261003`. Historical pending
  statements below describe the earlier Linux checkpoint, not the current gate.
- The next existing plan task is mapping current owner-scoped KB functionality
  into Private Library UI/APIs. The user requested a bounded frontend usability
  and visible-branding pass before substantial Phase 8 work.

- Branch: `codex/master-integration`.
- Pre-integration source snapshot: `09a9485` (existing frontend work, not a stability certification).
- Deployment services: backend, frontend, MySQL, Chroma, MinIO, Nginx. The password-flow revision recreated only backend/frontend and reloaded unchanged Nginx configuration. Data services remained running.
- Original database revision: `3580c0dcd005`; current revision: `riq_004`.
- Initial counts: 2 users, 2 knowledge bases, 4 documents, 190 chunks, 1 chat.
- Actual configured providers: OpenAI-compatible chat, HuggingFace embeddings, Chroma vectors.
- Phase 0 completed after the real synthetic PDF upload, processing, retrieval, streamed cited answer, persistence and cleanup passed with the updated OpenRouter key.
- Backend/frontend regression tests and frontend TypeScript checks passed at the baseline repair checkpoint.
- Phase 1 is applied and verified; Phase 2 is committed at `9f4aac7`. The user confirmed Phase 3 complete at `0860607`; Phase 4 is checkpointed at `eee6c37`. On 21 September the user explicitly authorized their own admin appointment and Phase 5. Do not begin Phase 6.

### Phase 7 Admin Workflow - 22 September 2026

<!-- Added by ChatGPT: authorized only after Phase 6 completion and its separate checkpoint. -->

- Started from tested Phase 6 commit `c912772`, tag `researchiq-phase6-tested-20260922`. Preserved the two unrelated citation edits. No branch reset, file discard or data-volume change.
- Added an admin-only paginated processing inbox and terminal archive endpoint; reused existing upload, academic metadata, department, rename, publish/unpublish, retry, content and safe deletion services. No migration or new dependency; schema remains `riq_004`.
- Management UI separates publication from processing. Includes server filters, cursor pages, refresh/polling, draft upload, metadata entry/edit, department reference maintenance, filename changes, explicit lifecycle confirmations, failed-source retry and permanent deletion. Private mode and the published-only researcher catalog remain unchanged.
- User delegated archive design. Chosen policy: Unpublish is reversible; Archive permanently hides the document identity, retaining resources until deletion. Existing archived deletion tombstones are never restorable. This uses the current schema and protects partial-cleanup safety; confirmations state the distinction.
- CRUD dialogs use a shared 760px maximum form width / 500px confirmation width, 18px headings, 14px controls, scrollable bodies and fixed footer actions. Browser inspection prompted stable accessible names for textarea/select controls and a consistent mobile upload-button size.
- Automated gate: **196 passed on disposable MySQL 8**, **184 passed, 12 MySQL-only skipped on SQLite**, **66 frontend tests passed**, and TypeScript passed. Production image compilation passed; final layout image deployment/live acceptance is in progress. An initial SQLite-only test fixture needed an explicit timestamp instead of MySQL's `now()` default; corrected and the complete gate rerun.
- Retained verified Phase 6 image `rag-web-ui-frontend:phase6-tested-20260922` and ignored mode-0600 backup `.local/backups/pre-phase7-20260922.sql`. A host/application restart between continuations removed temporary test runners/scripts but preserved the working tree and protected acceptance state; no implementation was restarted. Disposable suites were recreated independently of production.
- New real uploads appeared after the first Phase 7 fixture snapshot. They are preserved. A fresh read-only receipt excluding exact synthetic IDs/paths was captured before live mutation testing, so cleanup verification will not mistake legitimate new user data for test leftovers.
- Final live acceptance, exact fixture cleanup and Phase 7 checkpoint are pending. Phase 8 has not started. Contracts, archive rationale and operational limitations are in `docs/phase7-admin-workflow.md`.

### Phase 6 Public Library - 22 September 2026

<!-- Added by ChatGPT: public/private catalog gate, including both explicit scope clarifications. -->

- Completed the original Public/Private toggle with separate, unmounted-on-switch data flows. Public reads the canonical published UAF corpus; Private retains original collections, uploads, filters and owner-only APIs. No private documents are copied into the corpus.
- Added server-side academic search/filtering, bounded cursor pagination, fresh metadata/open/download dialogs and existing corpus evidence queries with clickable source details. MySQL uses the Phase 1 FULLTEXT index; short tokens and author substrings use bounded scoped filters. No public chat/source-scope, compare or analyze features were added.
- User explicitly authorized basic admin upload and personal public-document bookmarks. Only effective admins see Add Documents in Public; completion remains a draft. Save/unsave and Saved only use the existing bookmarks table, current session ownership and CSRF enforcement. Unpublished bookmarks remain stored but hidden; final document deletion cascades them.
- No migration, dependency, Docker configuration, volume or `.env` change. Schema remains `riq_004`; Chroma remains mounted at `/data`. Existing system ownership, auth and private isolation are unchanged.
- Combined Phase 6/5/4/3/2 and baseline/provider suite: **192 passed on disposable MySQL 8**; **180 passed, 12 MySQL-only skipped on SQLite**. Frontend: **55 tests passed**, TypeScript and production frontend image build passed. Existing tooling/deprecation warnings remain unrelated.
- Recreated only backend/frontend after confirming zero active ingestion jobs, then reloaded unchanged Nginx. Original `http://127.0.0.1.nip.io` health passed. Preserved pre-change source tag `researchiq-pre-phase6-20260922` (`6ee4063`), frontend image `rag-web-ui-frontend:pre-phase6-20260922`, and ignored restricted SQL backup `.local/backups/pre-phase6-20260922.sql`.
- Real Chrome acceptance passed for researcher widths 1366/1024/390 and admin 1366: both modes, private filters/details/upload dialog, public metadata filters, persistent save/unsave/Saved only, opening the actual rendered PDF, real corpus evidence and source popups, admin native-file upload and unpublished completion. No JS errors or horizontal overflow. Screenshots were inspected. The first private display fixture omitted its required file hash; only that synthetic fixture was corrected before rerunning the complete checks.
- Live tests used temporary maintenance sessions and synthetic research, not real inbox/password issuance or a new LLM conversation. Actual parser/MinIO/embedding/Chroma ingestion and retrieval passed. Removed exact synthetic users, sessions, department, private display fixture, public documents/tasks/bookmarks, objects and vectors. All pre-existing non-auth table hashes, object receipts and vector counts matched afterward.
- Dedicated checkpoint: `researchiq-phase6-tested-20260922`. The two pre-existing citation edits remain outside the commit; nothing pushed and no branches removed. Contracts and limitations are in `docs/phase6-public-library.md`.
- The user subsequently authorized Phase 7 admin workflow, after this gate. Disposable test infrastructure is retained for that next gate, not attached to production data.

Phase 6 files: corpus API/service; new backend Phase 6 tests; Library wrapper;
new public-library contracts, component and dialogs; scoped CSS; Library and Public
Library frontend tests; this progress log and `docs/phase6-public-library.md`.

### Phase 5 Academic Metadata - 21 September 2026

<!-- Added by ChatGPT: explicit appointment, previous-gate acceptance and academic metadata wiring. -->

- Confirmed the requested username/email identify the same active, verified human account (user ID 1, `mkamilali`). At the user's explicit request, added its admin role and active exact-email allowlist entry in one transaction; retained the researcher role, password, sessions, verification, superuser=false and all ownership. No domain-based promotion or other account changes. The allowlist records the requesting account as `added_by`. Code rollback does not undo this separate authorized data operation.
- Closed Phase 4's remaining live service gate using a uniquely named synthetic document: real MinIO upload/copy, parser/chunker, configured embeddings, Chroma indexing, draft hiding, admin publication/download/retrieval/rename/unpublication, researcher mutation denial and cleanup passed. An initial inspector snapshot mistake was corrected by ending its MySQL read transaction; both attempts cleaned their fixtures. All pre-existing table hashes and private vector counts matched afterward. This was service-level acceptance, not a new password/OTP or LLM conversation.
- Read the master Phase 5 definition, Phase 4 checkpoint, current progress, migrations, existing academic/department models, session/authorization policies and tests before implementation. The existing schema and indexes suffice: no migration, provider change, new dependency or UI change.
- Added bounded academic metadata read/PATCH contracts, normalized department reference reads/admin create/edit/deactivate, active-department validation and partial-update year/date consistency. Academic edits reuse corpus/document locks and cannot change ownership, publication, filenames, source files or embeddings. Private metadata remains inaccessible through these public-corpus endpoints, even to admins.
- No unofficial UAF department seeds or fabricated bibliography. Initial titles remain ingestion filenames until curated. No Phase 6 search/bookmarks/Public Library UI, Phase 7 forms, private metadata workflow, compare/analyze or LLM metadata extraction.
- Pre-change source checkpoint: `researchiq-pre-phase5-20260921` at `eee6c37`. The two unrelated citation edits remain preserved and outside Phase 5.
- Combined Phase 5/4/3/2 and baseline/provider gate: **168 passed on disposable MySQL 8**; **156 passed, 12 MySQL-only skipped on SQLite**. This includes 43 Phase 5 cases (41 passed / 2 skipped on SQLite): validated round trips, atomic PATCH/clear semantics, immutable file/vector identity, department deactivation/history, duplicate conflict handling, current-role revocation, private/draft isolation, session/CSRF and MySQL concurrent creates/disjoint edits. Existing dependency deprecation warnings remain unrelated.
- Frontend regression tests: **41 passed**; `npx tsc --noEmit --incremental false` passed. No frontend source was changed for Phase 5, so no frontend rebuild or temporary preview was needed. The two unrelated citation changes remain outside this checkpoint.
- Before deployment, confirmed zero active ingestion jobs and saved ignored mode-0600 backup `.local/backups/pre-phase5-20260921.sql`. Restarted only `rag-web-ui-backend-1`; health through the original Nginx URL passed, and anonymous department access returned 401. Frontend/data services, Docker files, volumes and `.env` were not modified. Chroma remains on the existing `rag-web-ui_chroma_data:/data` mount.
- Live HTTP acceptance through Nginx passed using short-lived maintenance sessions for the explicitly appointed admin and a synthetic researcher: department create/deactivate/read, upload/processing, academic edit/validation, researcher denial, private-ID denial, draft hiding, publish/read/download, real configured embedding/Chroma retrieval, unpublish and delete. These sessions test deployed authorization/CSRF, not password/OTP issuance. No real email or LLM call was made.
- Removed the exact synthetic sessions, researcher/private fixture, department, document, upload/task, objects and vector chunks. All pre-existing non-auth table hashes and private vector counts matched before/after. Final read-only checks confirmed zero corpus documents/chunks/tasks/vectors/objects and the requested admin+researcher roles with superuser=false. No actual UAF documents or department list were imported. Both disposable test containers were stopped and removed; the six existing application services remain running.
- Dedicated tested checkpoint tag: `researchiq-phase5-tested-20260921`; nothing pushed, previous branches/tags preserved. API contracts, validation limits and recovery boundaries are in `docs/phase5-academic-metadata.md`. Phase 6 has not been started.

Phase 5 checkpoint files:

- `backend/app/api/api_v1/api.py`, `backend/app/api/api_v1/corpus.py`, `backend/app/api/api_v1/departments.py`
- `backend/app/schemas/academic.py`, `backend/app/services/academic.py`
- `backend/tests/test_phase5_academic_metadata.py`
- `docs/implementation-progress.md`, `docs/phase5-academic-metadata.md`

Repeat the Phase 5 gate in the same isolated runtime by adding
`tests/test_phase5_academic_metadata.py` before the Phase 4/3/2 and baseline files
in the combined command below. The guarded MySQL fixture still requires
`127.0.0.1/researchiq_phase2_test` at `riq_004`, never the production database.

### Phase 4 Public Corpus - 20 September 2026

<!-- Added by ChatGPT: backend corpus foundation and explicitly approved minimal lifecycle endpoints. -->

- Inspected the Master Integration Plan, Phase 3 checkpoint, current migrations, authorization/ingestion/retrieval code and regression tests before changing code. Preserved both uncommitted citation files and all previous branches/tags.
- Clarified the plan's scope mismatch: Phase 4 originally provisions only the shared KB, while lifecycle workflows appear in Phase 7. The user explicitly chose **minimal working backend lifecycle endpoints now**. No Public Library UI, academic metadata editing, departments, bookmarks, compare/analyze or public/private chat-source modes were implemented.
- Startup idempotently creates the dedicated inactive, passwordless `researchiq_system` owner and one `UAF Research Corpus` (`public`, system-managed). Unique-owner locking serializes provisioning; colliding human identities or malformed ownership fail closed. Existing private KBs are never adopted, transferred or changed. No migration/schema/dependency change; head remains `riq_004`.
- Added explicit `/api/corpus` backend routes and a corpus service. Researchers discover the corpus and read/download/query published documents. Explicit role plus current exact-email allowlisting is required for upload, draft review, filename edits, publish/unpublish, retry and deletion. The legacy private KB/chat/API-key routes retain their original owner-only boundaries. Browser session/Origin/CSRF enforcement remains unchanged.
- Reused the existing parser/chunker/embedding/vector/MinIO pipeline with an opt-in public-processing flag. Partial public documents are linked to their task early; failed sources remain retryable; successful staging copies are removed. Private processing uses its unchanged defaults. Publication uses only the existing lifecycle fields on the metadata row, with the required title initialized from the filename; actual academic metadata remains Phase 5.
- Deletion archives before external cleanup, deletes exact chunk IDs in bounded batches, and retains hidden records if cleanup fails. Retrying is idempotent; deletion tombstones cannot be republished. Filename edits do not move source files or change chunk IDs, and original storage names remain protected against overwrite.
- Public retrieval is bounded and SQL-authorized after the vector call. Draft/private/stale chunks and forged vector text cannot become returned evidence. Corpus scope/ownership and publication are rechecked; returned content/document identity comes from authorized SQL chunks. This is evidence retrieval, not a new LLM pipeline or public chat implementation.
- Removed only the manual **Verify email** shortcut from sign-in and renamed the recovery action/heading to **Reset password**. Automatic verification for unfinished/future registrations remains enforced. Read-only live inspection found 5 human accounts, 4 verified, and no effective admins; no account verification or role/allowlist rows were changed.
- Combined Phase 4/3/2 and baseline/provider regression gate: **125 passed on disposable MySQL 8**; **115 passed, 10 MySQL-only skipped on SQLite**. After the final draft-initialization locking adjustment, all **29 Phase 4 MySQL tests passed again**. Frontend: **41 tests**, TypeScript, local production build and deployment image build passed. Existing Next/deprecation warnings remain unrelated. Disposable test containers were removed.
- Deployed on the existing `http://127.0.0.1.nip.io` URL by recreating only backend/frontend and validating/reloading Nginx. Login/register/health returned 200; anonymous corpus/document/content/identity requests returned 401. OTP remains enabled. No temporary preview, SMTP messages or live LLM calls were used for these checks; `.env`, Docker configuration and volumes were not changed.
- Post-deployment receipts match all 16 tracked pre-existing non-auth tables, excluding only the newly provisioned system owner/corpus. Private Chroma counts remain `kb_1=185`, `kb_2=203`, with persistence at `/data`. On 21 September a read-only live service check confirmed corpus ID 8, public/system-managed scope, inactive passwordless system ownership and an empty researcher query result. The new corpus contains no imported research yet.
- Deployed Chrome checks passed at 1366px and 390px: removed verification shortcut, updated reset-password action and recovery view, no horizontal overflow or JavaScript errors. These checks made no credential submissions or email requests.
- Pre-change source tag: `researchiq-pre-phase4-20260920` at `0860607`; retained frontend image `rag-web-ui-frontend:pre-phase4-20260920`. Private database backup `.local/backups/pre-phase4-20260920.sql` and data/vector receipts are ignored and mode 0600; never commit or share them.
- Operational boundaries: no live admin exists, so live authenticated admin upload/publish/delete acceptance requires an explicit appointment, not automatic promotion. In-process BackgroundTasks can strand jobs after a process crash, admin writes serialize per corpus, and bounded post-filtering can reduce retrieval recall when drafts dominate candidates. These limits and the exact API are documented in `docs/phase4-public-corpus.md`.
- Dedicated tested checkpoint tag: `researchiq-phase4-tested-20260921`. The two pre-existing citation files remain outside this checkpoint; no branches were removed and nothing was pushed. Phase 5 has not been started.

Phase 4 checkpoint files:

- `backend/app/api/api_v1/api.py`, `backend/app/api/api_v1/corpus.py`
- `backend/app/main.py`, `backend/app/services/public_corpus.py`
- `backend/app/services/document_processor.py`, `backend/tests/test_phase4_public_corpus.py`
- `frontend/src/components/auth/password-login.tsx`, `frontend/src/components/auth/email-login.tsx`
- `frontend/src/components/auth/__tests__/email-login.test.tsx`
- `docs/implementation-progress.md`, `docs/phase4-public-corpus.md`, `docs/phase3-authentication.md`

Repeat the combined backend gate in an isolated test runtime:

```sh
EMAIL_OTP_ENABLED=false SQLALCHEMY_DATABASE_URI=sqlite:// python -m pytest tests/test_phase4_public_corpus.py tests/test_phase3_authentication.py tests/test_phase2_authorization.py tests/test_baseline_regressions.py tests/test_minimax_unit.py -q
```

MySQL uses the existing guarded `PHASE2_TEST_DATABASE_URI` fixture at
`127.0.0.1/researchiq_phase2_test`, initialized to `riq_004`. It deletes fixture
rows and must never be pointed at the live database. Frontend verification remains
`npm run test:ci -- --runInBand --silent`, `npx tsc --noEmit --incremental false`,
and `RAG_NEXT_DIST_DIR=.next-check npm run build`.

### Phase 3 Registration And Password Sign-In Revision - 19 September 2026

<!-- Added by ChatGPT: user-directed correction of the initial passwordless design. -->

- Restored username/email/password registration and confirmation in the existing styling. New accounts are unverified Researchers; no automatic account creation or sign-in occurs at OTP verification. Email/username plus password is the routine login path, with the existing opaque session cookies, CSRF, Origin, rotation and revocation protections. Browser JWTs remain rejected while email verification is enabled.
- Registered-only verification and separate `reset_password` challenges reuse the existing indexed OTP/rate-limit tables. Unknown, inactive and system addresses receive a generic response but no email/account. Old `login` challenges cannot be redeemed. Verification requires the registration password as well as the emailed code; password setup/reset requires its own code and confirms a new password. Reset preserves account IDs/roles/research, revokes browser sessions and invalidates outstanding challenges; API keys remain separately managed credentials.
- OTP-only accounts can set a password using inbox proof without creating duplicate accounts or losing documents. Previously unverified password accounts verify once. Password login and registration have separate database-backed identity/IP limits, new-password validation is enforced server-side, and oversized bcrypt input fails safely. Existing-user locking serializes password sign-in against password replacement without gap-locking unknown users.
- Added migration `riq_004`: nullable `users.email_verified_at`, backfilled only from successfully issued OTP-era sessions, not used/exhausted OTP records. Active status remains a separate administrative control. Browser sessions and API-key owners require verified email in enabled mode. Roles/allowlisting/private ownership policies are unchanged.
- **96 backend tests passed on disposable MySQL 8**, including all Phase 3 checks, 27 Phase 2 authorization tests and 22 baseline/provider regressions. **91 passed / 5 MySQL-only skipped on SQLite**. Two migration downgrade/re-upgrade cycles preserved every pre-existing column value in the disposable data; tests distinguish successful session proof from exhausted OTPs and cover concurrent signups/send/verify.
- **40 frontend tests passed**, TypeScript passed, and the production build passed. Isolated headless Chrome at 1366x900 and 390x844 exercised registration, one-time verification, password login and recovery with mocked APIs, without overflow or JavaScript errors. No preview server was started. Existing deprecation/Next configuration warnings remain unrelated to this change.
- The MySQL test inspector was updated to end repeatable-read snapshots before checking separately committed HTTP results. No production isolation or security assertions were weakened. Historical migration fixtures now target `riq_004` and correctly restore it after guarded partial downgrades; the dedicated Phase 3 migration round-trip was run, not the full historical clone-only Phase 1 suite.
- Pre-change source tag: `researchiq-pre-password-flow-20260919` at `88f0918`. Retained frontend image: `rag-web-ui-frontend:pre-password-flow-20260919`. Private backup: `.local/backups/pre-password-flow-20260919.sql` (ignored, mode 0600), with a separate read-only table-count/hash receipt. These contain sensitive data and must not be committed or shared.
- Deployed to the existing `http://127.0.0.1.nip.io` URL by rebuilding frontend and recreating only backend/frontend. Startup applied `riq_004`; Nginx validation/reload passed. Post-migration hashes matched all 16 non-auth tables, including all prior user/password/role columns, 2 knowledge bases, 7 documents, 388 chunks, 4 chats and 52 messages. No vectors were rebuilt and Chroma remains mounted at `/data`.
- Live anonymous checks passed: login/register 200, anonymous identity 401, unregistered OTP verification 400, unregistered password login 401, wrong-Origin login 403. A unique unregistered OTP request returned the generic 200 response and produced **zero users and zero OTP challenges**. Only expected rate-limit records were written; no real email was sent in this revision's automated checks. Read-only deployed Chrome checks passed on desktop/mobile for password login, registration and recovery, without JavaScript errors or overflow.
- Revised inbox acceptance remains a user step: register/verify a new account or set the existing OTP-only account's password using the live inbox, then confirm repeated password login/logout and a cited chat. The automated RAG checks use deterministic provider fixtures, not a new live-provider chat. `EMAIL_OTP_ENABLED` remains enabled; `.env` and credentials were not edited. The two pre-existing citation changes remain preserved and excluded from the authentication checkpoint. No Phase 4 work.
- Tested revision checkpoint: `researchiq-phase3-password-flow-tested-20260919`. Nothing pushed; the development branch and earlier tags remain intact. Disposable test containers were stopped and removed.

The sections below describe earlier checkpoints and are historical where their
passwordless login or migration-head descriptions differ from this revision.

### Local OTP Activation - 19 September 2026

<!-- Added by ChatGPT: activation evidence, distinct from successful inbox/sign-in acceptance. -->

- The user supplied Brevo credentials locally and explicitly authorized activation. Verified SMTP authentication over certificate-checked TLS without displaying credentials. Only the non-secret `EMAIL_OTP_ENABLED` flag was changed to `true` in the ignored `.env`; credential values were not edited or committed.
- The frontend image build completed during the interrupted activation and was confirmed running on resume. Recreated only the backend with the enabled flag and reloaded the existing Nginx configuration after `nginx -t` passed. No data service was recreated by this activation.
- Live checks through Nginx passed: `/api/auth/methods` reported `email_otp: true`, `/login` returned 200, anonymous `/api/auth/me` returned 401, legacy password login returned 403, and an OTP request with an invalid Origin returned 403.
- A real `/api/auth/request-otp` request to the user-confirmed inbox returned 200 after Brevo SMTP accepted the message. This created the expected OTP/rate-limit records, not a new user or research document. SMTP acceptance is not proof of inbox receipt; the user was asked to complete email verification directly in the login page without sharing the code in chat.
- Existing URL remains `http://127.0.0.1.nip.io/login`. The explicit local HTTP exception is enabled; production still requires HTTPS. Chroma remains mounted at `/data`; MySQL/MinIO/research data and existing private ownership were not changed.
- Recovery references: source tag `researchiq-pre-otp-activation-20260919` at the tested code commit, and retained frontend image `rag-web-ui-frontend:pre-otp-20260919`. An explicit rollback must account for the documented security implications of re-enabling legacy passwords/JWTs; do not remove volumes.
- No application source changes were needed for activation. The user's two uncommitted citation changes remain preserved and excluded from activation documentation changes. Phase 4 is not started.

### Phase 3 Email OTP And Sessions - 19 September 2026

<!-- Added by ChatGPT: resumed implementation, isolated evidence and a separate live acceptance gate. -->

- Preserved and reviewed every existing Phase 3 file; no reset, restore, clean or source restart. Starting commit remains `9f4aac7`, tagged `researchiq-phase2-tested-20260916`.
- Added request/verify OTP, method discovery, `/api/auth/me`, and server-side logout using the existing `email_otps`, `auth_sessions`, and `auth_rate_limits` tables. No schema/migration change or new application dependency.
- SMTP uses verified STARTTLS or TLS with bounded timeouts. Six-digit codes are HMAC-hashed, expire after five minutes, have bounded attempts, and are single-use. Pending/failed deliveries cannot authenticate; resends invalidate earlier challenges. Provider exceptions never expose codes or credentials.
- Database-serialized email/IP limits and cooldowns work across workers. IP limits are checked before allocating arbitrary new email keys. Forwarded IPs are trusted only from explicitly configured proxy peers. A bounded, opt-in cleanup command targets expired auth rows only; it was not run on deployment data.
- Opaque random sessions and bound CSRF tokens are stored as hashes. Sessions are HttpOnly, fixed-expiry and revocable; login rotates the presented browser session. Cookie-authenticated mutations require exact Origin and CSRF; logout remains available to a disabled account holding its valid session/CSRF pair.
- Secure host-only cookies are the default. The user explicitly approved an HTTP development exception, restricted to the documented loopback hostnames with separate cookie names. This is not production transport security.
- `EMAIL_OTP_ENABLED=false` preserves legacy password/JWT login. Enabling OTP disables password registration, password token issuance and browser JWT authentication without an automatic fallback. API-key ownership checks and the Phase 2 role/allowlist policy are unchanged. Successful legacy login clears stale OTP cookies during an explicit maintenance rollback.
- New verified users receive only Researcher. Existing active accounts keep their IDs/roles. University domains and allowlisting alone never grant Admin, and Admin never bypasses private ownership. Exact normalized identity checks reject legacy MySQL accent-equivalent email collisions.
- Frontend email/code form, resend countdown, change-email, recoverable errors, session-checked dashboard, server logout, and current CSRF credentials for JSON and streamed chat are implemented in the existing styling. Invalid/missing login-method responses cannot expose a password fallback.
- The resume fixed malformed-method fallback, disabled-account logout, unnecessary rate-row allocation after IP throttling, stale-cookie interference with legacy rollback, and a MySQL whole-second rounding edge that could report a 61-second resend cooldown. Removed an unnecessary missing-user locking read that could gap-lock concurrent signups; email serialization and unique constraints still protect identity creation. The earlier test inspector's MySQL repeatable-read snapshot was corrected rather than weakening assertions.
- Removed exactly three user-authorized command-fragment artifacts: `earchiq-rag-baseline-v1..HEAD -- \\` contained only a generated Git name/status listing; `pect  \\` and `ted Phase 1 schema foundation and rollback guards` matched standard `less --help` byte-for-byte. They were untracked, so their removal is not a tracked Git deletion.
- Preserved the user's changes to `frontend/src/lib/citations.ts` and its test file. They are not Phase 3 work and are excluded from the checkpoint. No other branch was removed or moved; nothing is pushed.
- Docker definitions/volumes, existing research data, `.env` secrets, Chroma `/data` persistence, collection naming, embeddings and citation parsing are unchanged. A read-only request to the running backend confirmed `{"email_otp":false}`.

#### Isolated Verification

- **84 backend tests passed on MySQL 8**: 35 Phase 3 checks, 27 Phase 2 authorization checks, and 22 baseline RAG/provider checks. The existing migrations initialized a disposable RAM-backed database at `riq_003`. No live database or `.env` was mounted into tests.
- **80 passed, 4 skipped on SQLite**. The four MySQL-only checks cover concurrent send, concurrent verify, concurrent distinct-user signup, and legacy accent-insensitive email collation; all four passed on MySQL.
- Checks cover hashed storage, TLS/failure handling, OTP expiry/reuse/attempts/resends, email/IP limits, exact cooldown boundaries, cookie flags, CSRF/Origin, rotation/revocation, disabled/system accounts, role isolation, legacy cutover/rollback, bounded cleanup, and private-resource access.
- Cookie-authenticated two-collection chat exercised the actual HTTP route, authorization, RAG service, citation stream and SQL persistence. External vector/embedding/LLM services were deterministic fixtures, not live-provider verification.
- **36 frontend tests passed** in seven suites, including the two additional pre-existing user citation cases. TypeScript and the production build passed using isolated `.next-check` output; the running frontend build was not replaced.
- Headless Chrome checked the built email/code screens at 1366x900 and 390x844: resend disabled state, invalid-code feedback, change-email interaction, no horizontal overflow and no JavaScript errors. Assets/API fixtures were intercepted in the browser; no preview server, exposed port or live authentication request was used.
- Existing Pydantic/SQLAlchemy/Starlette deprecations and legacy Next.js configuration warnings remain; they did not fail tests or build and were not broadened into unrelated changes.
- Tested source checkpoint: `researchiq-phase3-tested-20260919`, on `codex/master-integration`. This is a code/test checkpoint, not a live-verification tag.

Repeat the backend checks from `backend/` in an isolated test environment:

```sh
EMAIL_OTP_ENABLED=false SQLALCHEMY_DATABASE_URI=sqlite:// python -m pytest tests/test_phase3_authentication.py tests/test_phase2_authorization.py tests/test_baseline_regressions.py tests/test_minimax_unit.py -q
```

For MySQL, the same fixture accepts `PHASE2_TEST_DATABASE_URI` only at
`127.0.0.1/researchiq_phase2_test`, initialized through `riq_003`. It deletes
fixture rows between tests: use a disposable database only. Frontend commands:
`npm run test:ci -- --runInBand --silent`, `npx tsc --noEmit --incremental false`,
and `RAG_NEXT_DIST_DIR=.next-check npm run build`.

#### Pending Live Gate

Follow `docs/phase3-authentication.md`: local activation and a real SMTP send are now recorded above. Confirm actual inbox receipt and browser session/logout, then test a synthetic upload/retrieval/cited chat with the deployed providers. The isolated code-verification run sent no real email; the subsequent explicitly approved activation did. No synthetic research records were added during activation. Neither the code checkpoint nor SMTP acceptance alone completes live acceptance or permits Phase 4.

### Phase 2 Authorization Core - 16 September 2026

<!-- Added by ChatGPT: scoped implementation, policy decisions and repeatable evidence. -->

- Starting checkpoint: `ad733e4`, the user's Chroma persistence fix (`chroma_data:/data`). The user reports `kb_1`/`kb_2` rebuilt and working. Docker configuration, Chroma/indexing code, migrations, existing data and `.env` were left unchanged.
- Existing uncommitted frontend citation changes and three unrelated untracked root files were preserved and excluded from the Phase 2 commit.
- Added `app/services/authorization.py`: normalized exact-email matching, active-human validation, effective Researcher/Admin roles, researcher assignment for new registrations, reusable private KB/document/chat filters and guards, and an institutional-corpus administrator guard.
- Effective content admin requires BOTH an explicit `user_roles` admin assignment AND an active exact normalized `admin_allowlist` entry. University domains, client-supplied roles, JWT role claims and `is_superuser` alone never grant content-admin privileges. Runtime role/allowlist checks are not cached in a token; removal/deactivation takes effect on the next request.
- This dual requirement is intentional: legacy password registration has no verified-email proof, so allowlisting alone would let someone claim a professor's email. Only a trusted out-of-band role assignment can satisfy the second condition until verified identity provisioning is implemented later. No role-management endpoint or automatic admin promotion was added.
- Existing active users without a role row keep baseline researcher permissions without a data backfill. New password registrations atomically receive the existing researcher role; no existing account/role/allowlist data was modified.
- JWT, password and API-key authentication reject inactive/system accounts. JWT subjects must be nonempty strings. API keys are checked against their current owner's state before last-use updates. API-key logs no longer print reusable secrets. The OAuth2 documentation now points to the existing `/api/auth/token` route.
- Private KB reads/updates/deletes, upload/preview/processing/task access, document details, JWT/API-key retrieval and chat creation now share ownership/scope rules. Missing and unauthorized research resources return 404; retrieval handlers preserve authorization errors instead of converting them to 500.
- Admin and superuser flags never bypass another user's private ownership. Temporary-file cleanup is limited to the caller's private uploads. Nested document/upload/task IDs stay constrained to the authorized collection.
- Saved-chat reads/listing reject invalid foreign-source associations. Chat streaming rechecks sources at the endpoint and again in the RAG service, before message persistence, embeddings, vectors or LLM calls. The service requires the actor and the exact chat source set. Existing collection naming, retrieval merger and citation stream format are unchanged.
- `get_current_admin` is reusable by future protected routes. `require_corpus_admin` requires a public, system-managed KB owned by an inactive, non-superuser system identity without a password. It provides authorization only: no system user/corpus was created, and legacy routes remain private-only. Public catalog, admin ingestion UI and published-document retrieval remain later phases.

#### Verification And Limits

- **49 tests passed on SQLite and again on MySQL 8**: 27 Phase 2 checks plus 22 baseline RAG/provider regressions. MySQL tests used the existing migration chain through `riq_003` in a disposable RAM-backed database, without touching persistent deployment volumes.
- HTTP tests use real JWT authentication, dependencies, routes and ORM operations. They cover explicit-role/allowlist conjunction, revocation using the same token, email/domain/alias boundaries, self-promotion attempts, disabled/system accounts, private ID guessing by researchers/admins/superusers, nested IDs, cleanup isolation and API-key access.
- A permitted two-collection HTTP chat passed the actual authorization and RAG service path, streamed valid citations and persisted the answer. External embeddings/vector/LLM providers were deterministic test doubles; denied requests were verified not to reach providers or write messages.
- The first test pass exposed incorrect test URLs for the existing API-key route (`/openapi/knowledge`, not `/openapi/knowledge-base`); those fixtures were corrected. Final SQLite and MySQL runs passed without failures. Existing dependency deprecation warnings remain unrelated to this phase.
- No live OpenRouter/Chroma acceptance run or deployment restart was performed: application containers were stopped, and this request forbids changes to existing data. This checkpoint certifies Phase 2 code and isolated tests, not a new live-provider verification.
- No schema change means no database downgrade is needed to reverse Phase 2 code. The pre-Phase-2 source checkpoint is `ad733e4`, which retains the Chroma persistence fix. Preserve unrelated working changes before any recovery operation.
- At the Phase 2 checkpoint, Phase 3 and later features had not been started. Phase 3 status is recorded separately above.

From `backend/`, with development dependencies installed:

```sh
python -m pytest tests/test_phase2_authorization.py tests/test_baseline_regressions.py tests/test_minimax_unit.py -q
```

The authorization tests default to in-memory SQLite. Optional `PHASE2_TEST_DATABASE_URI` must target `127.0.0.1/researchiq_phase2_test`, initialized with Alembic at `riq_003`. This opt-in mode deletes test rows between fixtures and must only be used with a disposable schema; all other database names/hosts are refused. No production `.env` is needed for these tests.

### Citation Checkpoint - 16 September 2026

- `researchiq-development`, `origin/researchiq-development` and `feature/researchiq-shell` remain at `42ed804`. Integration work is on `codex/master-integration`; nothing has been pushed.
- `researchiq-frontend-checkpoint-20260915` preserves the earlier frontend snapshot (`09a9485`). `researchiq-phase0-verified-20260915` preserves the live RAG gate (`36a2330`).
- `fd4b997`, tagged `researchiq-citations-verified-20260916`, consolidates saved/live evidence decoding, handles UTF-8, restores blue source popups and preserves ordinary Markdown links. Unknown references never receive invented evidence.
- 21 frontend tests, TypeScript, production build and five real Markdown-renderer checks passed. Browser verification on the existing server opened a synthetic saved answer's document name, excerpt and page. The synthetic account/doc/chat were removed.
- After Docker restarted, a stale draft model caused `users.is_system` queries before schema migration. Restarting the backend with baseline source resolved it before further work; no migration or user-data change resulted from the failed request.

### Phase 1 Disposable Verification - 16 September 2026

- Three ordered migrations: `riq_001` roles/departments; `riq_002` authentication storage and nullable passwords; `riq_003` private scope, academic catalog and bookmarks.
- Corrections to the plan: create departments before their foreign keys; add non-login system identity constraint, session/CSRF hash storage, shared rate-limit storage, OTP delivery state, and separate publication state. These are schema foundations only, not activated authentication or publication features.
- Existing users are backfilled as researchers, never content admins. Existing KBs remain private with their original owner. The legacy registration endpoint stays unchanged; assigning roles for newly registered users belongs to Phase 2.
- Explicit unique/FK/check constraints, cascade tests, expiry indexes, catalog composite indexes and real MySQL FULLTEXT search verified. Normalized allowlist/OTP email equality uses binary collation; application normalization is still a later gate.
- 46 backend tests passed: 24 migration tests plus 22 baseline/provider regression tests. A restored real-data clone survived upgrade, downgrade and re-upgrade with every original column value preserved. Downgrade guards reject data loss. A second empty database passed the complete migration chain.
- Test command: `PHASE1_TEST_DATABASE_URI=<disposable MySQL URI> python -m pytest tests/test_phase1_migrations.py tests/test_minimax_unit.py tests/test_baseline_regressions.py -q`. The migration suite refuses non-test host/database names and otherwise skips when not explicitly configured. Restore the clone at `3580c0dcd005` before each run; tests leave it at `riq_003`.
- Schema checkpoint commit: `7cc9697`. Phase 2 is not authorized in this run.

### Phase 1 Live Completion - 16 September 2026

- Briefly paused the API, created `.local/backups/pre-phase1-apply-20260916.sql`, applied the three verified migrations and restarted the existing backend. Every original column value compared equal immediately before and after migration.
- Restored the final maintenance-window backup into isolated MySQL and repeated the value-by-value comparison after live acceptance: all ten original tables matched. Disposable databases/containers and synthetic test records were removed.
- The running database is at `riq_003`. Original counts: 2 users, 2 KBs, 4 documents, 190 chunks, 1 chat, 24 messages, 5 upload records, 5 processing records and 1 API key. Only 2 role definitions and 2 researcher assignments were added; other Phase 1 tables remain empty.
- Real post-migration acceptance passed: registration/sign-in, PDF upload, MinIO storage, extraction/preview, processing, relational persistence, configured embeddings, Chroma retrieval, OpenRouter answer streaming, valid document/page citations, saved conversation and synthetic fixture cleanup.
- An initial smoke attempt reached the restarting backend before startup completed and received 502 without creating a fixture. After API readiness was confirmed through Nginx, the complete test passed.
- Frontend remains deployed on `http://127.0.0.1.nip.io`; no temporary preview or port change. Existing frontend health checks and backend API response passed.
- Recovery instructions are in `docs/phase1-recovery.md`. The final verification tag is `researchiq-phase1-verified-20260916`. Source tags and SQL backups serve different purposes; neither is a substitute for future coordinated object/vector backups.
- Phase 1 is the schema foundation, not a claim that the entire ResearchIQ platform is production-secure or complete. Authorization, OTP delivery/session handling, system-owner provisioning and public discovery remain future gates.

### Verified On 15 September 2026

- 22 backend tests passed: 17 existing provider unit tests and 5 new baseline regression tests.
- 13 frontend tests passed using the normal test command after configuring a 15-second interaction timeout.
- Frontend TypeScript check passed.
- Real synthetic test passed registration, login, PDF upload, MinIO storage, PDF extraction, async processing, relational persistence, embeddings and Chroma retrieval.
- Real streamed answer failed: `https://openrouter.ai/api/v1/chat/completions` returned HTTP 401 Unauthorized for configured model `openrouter/free`.
- The synthetic chat, collection, PDF objects, vectors, task and user were removed. Original counts remain 2 users, 2 knowledge bases, 4 documents, 190 chunks and 1 chat.
- Database backup: ignored local file `.local/backups/baseline-20260915.sql`, restricted directory and file permissions. No schema migration has been applied.
- Source fixes are loaded by the existing backend container; no temporary server or changed port.

### Phase 0 Completion

The user updated the OpenRouter key, and the backend was recreated to load it. On 15 September 2026 the complete live acceptance test passed, including citation indices resolving to the synthetic document and page, saved answer verification and cleanup. The earlier 401 failure is resolved.

That next gate completed in Phase 1. Authorization subsequently completed in Phase 2. Later authentication and corpus results supersede this historical entry; see the current gate above.

### Repeatable Checks

```sh
# Frontend, from frontend/
npm run test:ci -- --runInBand --silent
npx tsc --noEmit

# Backend, from backend/, with requirements-dev.txt installed in the test environment
python -m pytest tests/test_minimax_unit.py tests/test_baseline_regressions.py -q

# Opt-in live acceptance test; uses configured providers and synthetic data
python -m tests.baseline_smoke
```

The live smoke script defaults to `http://nginx/api` inside Docker. Set `BASELINE_API_URL` when running elsewhere. It does not send existing research documents to an external provider.

## Plan Corrections To Carry Forward

1. Preserve `/api` compatibility. The running application uses `/api`, while the plan's examples use `/api/v1`. Do not silently break chat, uploads, API keys, or frontend calls by renaming the prefix.
2. Create `departments` before an `admin_allowlist.department_id` foreign key.
3. Add the omitted nullable password migration and explicit non-login system-account rule.
4. Revocable sessions need server-side session persistence, expiry, rotation and CSRF protection. OTP identity verification alone does not provide these.
5. Secure cookies require HTTPS. The present `http://127.0.0.1.nip.io` deployment must be addressed before claiming production-secure authentication.
6. Publication/archive state is missing from the proposed schema. Processing completion and publication are different states; only ready, published public documents may be discovered or retrieved.
7. OTP cooldown/rate-limit accounting must work across API workers and concurrent requests. A table containing only OTP hashes is insufficient for IP limits and delivery failures.
8. Admin allowlist removals must revoke effective content-admin permission; resolving a role only once at sign-in is insufficient.
9. Persist analysis runs/evidence as part of the first real analysis workflow, before history UI. Do not postpone recoverability until every analysis type is implemented.
10. Security tests belong to each feature gate, not only Phase 19.

## Baseline Repairs Verified By Regression Tests

- All selected nonempty knowledge bases contribute through the existing LangChain retriever merger.
- New Chroma insertions use relational chunk IDs; repeated inserts target the same vector IDs.
- Knowledge-base deletion uses the vector-store contract and recursively cleans MinIO object prefixes.
- Migration startup compares the installed database revision with migration-script head and disposes its check connection pool.
- Global LangChain debug output was removed to avoid logging private evidence.
- Chat no longer duplicates the current question in history or mutates the caller's message payload.
- Successful streams emit a completion frame; failures roll back and return a valid JSON error frame without internal provider details.
- Removed the empty backend-root package marker that made pytest import `/app/__init__.py` instead of the actual `/app/app` package in Docker.

## Deferred Findings For Their Feature Gates

- Historical vectors may still use generated IDs. Before per-document deletion/reindexing, reconcile existing Chroma IDs through chunk metadata; do not assume new insert behavior repairs old vectors.
- Ingestion retries, partial failures, repeated chunks, processing-state filters and publication need attention before public corpus support.
- Embedding models are reconstructed for each call, causing repeated HuggingFace requests and avoidable latency. Add bounded, concurrency-safe reuse when stabilizing ingestion/retrieval.
- Multi-collection streaming is covered by deterministic regression tests; the live single-PDF acceptance path also passed with the configured provider.

## Remaining Sequential Gates

1-11. Completed at the historical evidence and tags recorded above.
12. Researcher profile, publication requests, consent and approved withdrawal: complete.
13. Structured single-document summary with citations: complete; see the 17 October closure receipt above.
14. Insights on real catalog data: complete; see the 19 October receipt.
15. Compare with evidence persistence: complete; see 22 October receipt.
16. Bounded Analyze workflow: complete; see 23 October receipt.
17. Contradiction interpretation.
18. Corpus-qualified candidate gaps.
19. Analysis history.
20. Cross-feature security testing.
21. RAG evaluation.
22. Deployment hardening and recovery verification.
### Mobile Library correction - 4 October 2026

Before resuming Phase 9, fixed mobile actions so the admin icon does not consume
an equal button column, labels stay on one line, and whole actions can wrap.
Kept the original glowing treatment. Mobile public cards now use a consistent
right-edge bookmark and a compact, single metadata row; desktop rules unchanged.
The 24 Library/Public Library tests and production build/type checks passed.
Deployed frontend-only image `researchiq-frontend:mobile-20261004`; live CSS
asset check passed. Browser visual inspection remains unavailable.
