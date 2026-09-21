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

## Current Gate: Phase 5 Academic Metadata - Tested And Deployed

- Branch: `codex/master-integration`.
- Pre-integration source snapshot: `09a9485` (existing frontend work, not a stability certification).
- Deployment services: backend, frontend, MySQL, Chroma, MinIO, Nginx. The password-flow revision recreated only backend/frontend and reloaded unchanged Nginx configuration. Data services remained running.
- Original database revision: `3580c0dcd005`; current revision: `riq_004`.
- Initial counts: 2 users, 2 knowledge bases, 4 documents, 190 chunks, 1 chat.
- Actual configured providers: OpenAI-compatible chat, HuggingFace embeddings, Chroma vectors.
- Phase 0 completed after the real synthetic PDF upload, processing, retrieval, streamed cited answer, persistence and cleanup passed with the updated OpenRouter key.
- Backend/frontend regression tests and frontend TypeScript checks passed at the baseline repair checkpoint.
- Phase 1 is applied and verified; Phase 2 is committed at `9f4aac7`. The user confirmed Phase 3 complete at `0860607`; Phase 4 is checkpointed at `eee6c37`. On 21 September the user explicitly authorized their own admin appointment and Phase 5. Do not begin Phase 6.

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

1. Schema foundation, migration reversal and data preservation: completed in Phase 1.
2. Authorization core and private access regression tests: completed in Phase 2, isolated verification only.
3. SMTP OTP and secure revocable sessions: completed; user confirmed Phase 3 acceptance.
4. System-owned public corpus: tested/deployed; live service lifecycle and cleanup verified after explicit admin appointment.
5. Academic metadata: completed; tested and deployed with live API/storage/retrieval acceptance.
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
