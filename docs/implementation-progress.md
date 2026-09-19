# ResearchIQ Integration Progress

<!-- Added by ChatGPT: implementation gates and evidence for the adaptable master plan. -->

Source: `ResearchIQ_Master_Integration_Plan.pdf`, version 1.0, 15 September 2026.

## Working Agreement

- Complete and verify one feature before starting the next.
- Extend the current FastAPI/MySQL/MinIO/Chroma/Next.js application.
- Keep existing private ownership and API compatibility until each replacement is tested.
- Use Alembic for schema changes; test migrations on disposable data before applying them.
- Record deviations, tests, limitations, and the next gate here.
- A mock or sample UI is not a completed backend feature.

## Current Gate: Phase 3 Code Tested - Live Email Acceptance Pending

- Branch: `codex/master-integration`.
- Pre-integration source snapshot: `09a9485` (existing frontend work, not a stability certification).
- Deployment services: backend, frontend, MySQL, Chroma, MinIO, Nginx. They were stopped during Phase 2 and were already running when Phase 3 resumed on 19 September. This resume did not restart or reconfigure them.
- Original database revision: `3580c0dcd005`; current revision: `riq_003`.
- Initial counts: 2 users, 2 knowledge bases, 4 documents, 190 chunks, 1 chat.
- Actual configured providers: OpenAI-compatible chat, HuggingFace embeddings, Chroma vectors.
- Phase 0 completed after the real synthetic PDF upload, processing, retrieval, streamed cited answer, persistence and cleanup passed with the updated OpenRouter key.
- Backend/frontend regression tests and frontend TypeScript checks passed at the baseline repair checkpoint.
- Phase 1 is applied and verified; Phase 2 is committed at `9f4aac7`. Phase 3 code is tested at `fa75f07` and email OTP is now activated locally after explicit user approval. Brevo accepted a real OTP message; inbox receipt, successful browser sign-in, and deployed RAG acceptance still need confirmation. Stop before Phase 4.

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

That next gate completed in Phase 1. Authorization subsequently completed in Phase 2. Phase 3 is now the explicitly requested current gate, with real delivery/deployed acceptance still pending.

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

1. Schema foundation, migration reversal and data preservation: completed in Phase 1.
2. Authorization core and private access regression tests: completed in Phase 2, isolated verification only.
3. SMTP OTP and secure revocable sessions: current gate; real delivery/deployed acceptance pending.
4. System-owned public corpus.
5. Academic metadata.
6. Public catalog and bookmarks.
7. Admin ingestion and publication lifecycle.
8. Private library parity.
9. Permission-scoped retrieval.
10. Research Assistant and citation integrity.
11. Exact document-scoped retrieval.
12. Structured summary.
13. Insights on real catalog data.
14. Compare with evidence persistence.
15. Bounded Analyze workflow.
16. Contradiction interpretation.
17. Corpus-qualified candidate gaps.
18. Analysis history.
19. Cross-feature security testing.
20. RAG evaluation.
21. Deployment hardening and recovery verification.
