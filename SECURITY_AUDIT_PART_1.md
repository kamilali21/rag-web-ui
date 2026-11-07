# rAGRI search / ResearchIQ — Security Audit, Part 1

**Date:** 31 October 2026 (Asia/Karachi)  
**Repository:** `C:\Users\tayya\Projects\ResearchIQ`  
**Reviewed commit:** `995d5afef6b38fa3a336e252719c0e7ab0e0597a`, branch `master-integration`  
**Target:** an initial public deployment for 20–30 students  
**Scope:** architecture, authentication/authorization, frontend and backend application security.

## Audit boundary and method

This is an offline, read-only source review, not a penetration test or a certification.
The audit inspected route declarations, dependencies, service calls, SQL predicates,
schemas, browser rendering/storage, and supplied Docker/Nginx configuration. The
API directory contains **98 explicit router method/path declarations**, in addition
to the two app-level root/health handlers and framework documentation endpoints.

During this audit, no application code was changed, no dependencies installed, no
migrations/tests/exploits executed, and no HTTP/provider/network requests made.
The only audit file created is this document. Actual `.env` secrets, SQL dumps,
private documents and credential-bearing safety snapshots were not read. Source
configuration credential defaults were redacted when inspected. Findings do not
contain keys, passwords, cookies or private research.

Before this audit began, the separately authorized maintenance work was committed
as `995d5af` and tagged `researchiq-maintenance-checkpoint-20261031`, without a push.
That work removed six obsolete test/build images (Docker image storage decreased
about 3.16 GB), unused assets/test items and a duplicate dependency declaration,
and bounded Research-profile validation retries. Its prior automated checks were
610 backend passes/44 opt-in skips and 133 frontend passes, with type/build checks.
Those are **historical maintenance results, not tests performed by this audit**.
Its live evaluation remained 12/13: Overview passed; interpretation failed.
This report does not close Phase 21 or authorize deployment.

All source paths below are relative to the repository root above. Line numbers
refer to the reviewed commit. `Confirmed` means the stated source behavior or
configuration is present; it does not mean a live exploit was executed. `Likely`
means the consequence follows plausibly but needs reproduction. `Requires
Verification` identifies a policy/runtime uncertainty. Recommendations and
verification procedures are proposals only, not actions taken.

## Phase A — Architecture and trust boundaries

### Frontend routes

The App Router contains the following pages. API authorization resides in FastAPI;
rendering a dashboard page is not itself an authorization grant.

| Browser route | Source |
| --- | --- |
| `/`, `/login`, `/register` | `frontend/src/app/page.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/app/register/page.tsx` |
| `/dashboard` | `frontend/src/app/dashboard/page.tsx` |
| `/dashboard/profile` | `frontend/src/app/dashboard/profile/page.tsx` |
| `/dashboard/knowledge`, `/dashboard/knowledge/new` | `frontend/src/app/dashboard/knowledge/page.tsx`, `frontend/src/app/dashboard/knowledge/new/page.tsx` |
| `/dashboard/knowledge/[id]`, `/dashboard/knowledge/[id]/upload` | `frontend/src/app/dashboard/knowledge/[id]/page.tsx`, `frontend/src/app/dashboard/knowledge/[id]/upload/page.tsx` |
| `/dashboard/chat`, `/dashboard/chat/new`, `/dashboard/chat/[id]` | `frontend/src/app/dashboard/chat/page.tsx`, `frontend/src/app/dashboard/chat/new/page.tsx`, `frontend/src/app/dashboard/chat/[id]/page.tsx` |
| `/dashboard/insights`, `/dashboard/insights/history` | `frontend/src/app/dashboard/insights/page.tsx`, `frontend/src/app/dashboard/insights/history/page.tsx` |
| `/dashboard/api-keys` — still exists despite hidden navigation | `frontend/src/app/dashboard/api-keys/page.tsx` |
| `/dashboard/test-retrieval/[id]` — still exists | `frontend/src/app/dashboard/test-retrieval/[id]/page.tsx` |

### API inventory and authentication

Router prefixes are declared in `backend/app/api/api_v1/api.py:5-17`, mounted at
`/api` by `backend/app/main.py:19-25`. The separate integration router is mounted
at `/openapi`; its prefix is in `backend/app/api/openapi/api.py:5-6`.

| Prefix / endpoints | Gate and source |
| --- | --- |
| `/api/auth`: GET `methods`, `me`; POST `register`, `token`, `request-otp`, `verify-otp`, `logout`, `test-token` | Registration/login/OTP are intentionally pre-authentication. Mutations require exact Origin in session mode; authenticated operations use sessions. `backend/app/api/api_v1/auth.py:26-169`. |
| `/api/knowledge-base`: GET/POST root; GET `catalog`; GET/PUT/DELETE `{kb_id}`; GET/DELETE `{kb_id}/documents/{doc_id}`; GET its `content`; DELETE `{kb_id}/uploads/{upload_id}`; POST `{kb_id}/documents/{upload,preview,process}`; GET `{kb_id}/documents/tasks`; POST `cleanup`, `test-retrieval` | `get_current_user` plus owner/private-KB predicates. `backend/app/api/api_v1/knowledge_base.py:49-578`. |
| `/api/corpus`: GET/POST root; GET `documents`, `documents/{id}`, its `content`/`metadata`; POST/DELETE its `bookmark`; PATCH metadata/document; POST `query`, `documents/upload`, `tasks/{id}/retry`, document `publish`/`unpublish`/`archive`; GET tasks/list; DELETE task/document | Reads require authenticated active user and published scope; mutations/unpublished access require corpus admin. `backend/app/api/api_v1/corpus.py:46-194`. |
| `/api/departments`: GET root/id, POST root, PATCH id | Active authenticated reads; admin mutations and inactive-list access. `backend/app/api/api_v1/departments.py:18-36`; `backend/app/services/academic.py:15-36`. |
| `/api/researcher`: GET/PUT profile; GET/PUT/DELETE profile photo; GET eligible-documents; GET/POST requests; POST request cancel/withdrawals | Current-user ownership is derived server-side. `backend/app/api/api_v1/researcher.py:26-79`. |
| `/api/researcher/admin`: GET root, `count`, `{request_id}`, `{request_id}/source`, `{request_id}/profile-photo`, `withdrawals/{withdrawal_id}/document`; PATCH `{request_id}/metadata`; POST `{request_id}/approve`, `{request_id}/deny`, `withdrawals/{withdrawal_id}/approve`, `withdrawals/{withdrawal_id}/deny` | Services require corpus admin and resolve the exact submitted source. `backend/app/api/api_v1/researcher.py:82-176`. |
| `/api/researcher/publications/{document_id}/researcher-card` and `researcher-photo` | Published-document access plus per-request card consent. `backend/app/api/api_v1/researcher.py:179-191`. |
| `/api/chat`: GET/POST root; GET/DELETE `{chat_id}`; POST `{chat_id}/messages` | Owner-only chat; saved SQL scope/history replaces client claims. `backend/app/api/api_v1/chat.py:34-157`. |
| `/api/retrieval`: POST `query`, `documents/query`, `documents/summarize` | Authenticated, SQL-authorized scope/exact document selection. `backend/app/api/api_v1/retrieval.py:25-45`. |
| `/api/insights`: GET `documents`, `documents/{document_id}`, `history`, `history/{run_id}`, `comparisons/{run_id}`, `analyses/{run_id}`, `analyses/requests/{request_id}` (UUID); POST `selection`, `comparisons`, `analyses` | Catalog permissions and owner-only saved runs. `backend/app/api/api_v1/insights.py:23-105`. |
| `/api/ai-settings`: GET/PUT/DELETE root; POST `check` | Current user only; no admin override. `backend/app/api/api_v1/ai_settings.py:23-74`. |
| `/api/api-keys`: GET/POST root; PUT/DELETE `{id}` | Owner-checked browser authentication; legacy reusable application keys. `backend/app/api/api_v1/api_keys.py:14-85`. |
| GET `/openapi/knowledge/{knowledge_base_id}/query` | `X-API-Key`, active/verified account and private-KB ownership. `backend/app/api/openapi/knowledge.py:11-25`; `backend/app/core/security.py:82-109`. |
| `/`, `/api/health`, `/api/openapi.json`, `/docs`, `/redoc` | Root/health/spec/docs intentionally lack account authorization. `backend/app/main.py:16-25,42-52`; production proxy exposes docs at `deploy/nginx.conf.template:32-36`. No privileged state change is provided by these endpoints. |

### Roles, libraries and publication flow

- **Researcher:** baseline role. Registration explicitly selects user fields and
  assigns researcher only (`backend/app/api/api_v1/auth.py:99-105`). Client-supplied
  `is_superuser`/`is_active` fields in the inherited input schema are not copied.
- **Admin:** explicit admin-role association **and** exact normalized active
  allowlist entry; `is_superuser` alone is not a bypass. Checked on requests in
  `backend/app/services/authorization.py:23-45`. There is no public role-assignment
  route in the reviewed routers.
- **System corpus owner:** non-login identity; authentication rejects inactive
  and system users. Corpus checks require the system-managed public KB with its
  non-login owner (`backend/app/services/authorization.py:17-20,109-119`).
- **Private Library:** ownership, private scope and non-system-managed status are
  checked together. Admins do not gain blanket private access.
- **Public Library:** “public” here means published corpus material accessible
  to authenticated users, not anonymous internet access. Management/unpublished
  reads require admin (`backend/app/services/public_corpus.py:76-115`).
- **Publication:** user submits one own ready document with metadata/consent;
  admin reviews request, copies it to the public corpus, and ingestion must produce
  indexed chunks before publishing. Private original remains separately owned.
  `backend/app/services/researcher_publications.py:201-220,395-442,535-557` and
  `backend/app/services/public_corpus.py:304-336`.
- **Withdrawal:** owner requests; admin archives public copy, retaining original
  and history. There is a transaction concern in finding P1-07.
- Admins are currently global corpus admins, not department/supervisor-scoped.
  Queue filtering contains no supervisory assignment condition
  (`backend/app/services/researcher_publications.py:288-323`). This matches the
  presently implemented role model; the planned future department role must not
  be presented as already enforced.

### Data flow and boundaries

1. **Untrusted browser → Nginx → frontend/API.** Session-mode API uses HttpOnly
   cookies; browser sends the separate CSRF value on mutations. Names, query
   strings, identifiers, metadata, file bodies and AI-provider settings are
   untrusted inputs. UI visibility does not determine access.
2. **API → MySQL.** MySQL is the authority for users, roles, sessions, ownership,
   publication/readiness, chunks and saved conversations/analyses. Vector metadata
   is not allowed to establish permission.
3. **Uploads → MinIO → parser/embeddings → MySQL/Chroma.** Server-selected object
   paths and `kb_{id}` collections associate files/vectors with SQL records. Upload
   types/bytes and DOCX expansion are checked, but parser isolation and resource
   limits remain incomplete (P1-02/03/05).
4. **Authorized selection → Chroma candidates → fresh SQL recheck → LLM.**
   `backend/app/services/retrieval_scope.py:68-128` resolves scope before retrieval,
   rechecks it afterward and reconstructs content from permitted SQL chunks.
   Chat/summary/analysis then send permitted passages to the configured model.
   Retrieved text and model output remain untrusted; valid citation IDs are not
   a proof of semantic truth or complete prompt-injection resistance.
5. **External integrations:** OpenRouter/OpenAI personal keys have fixed HTTPS
   destinations, encrypted storage and per-call context. Other LLM/embedding
   endpoints are operator configuration. SMTP delivers verification/recovery
   codes. Hugging Face uses cached local embeddings with a download fallback.
   Sources: `backend/app/services/ai_settings.py:21-44,61-125`,
   `backend/app/services/llm/llm_factory.py:20-65`,
   `backend/app/services/email_otp.py:31-54`,
   `backend/app/services/embedding/embedding_factory.py:13-52`.

### Service exposure: source configuration, not a live port scan

The standalone production Compose publishes only Nginx 80/443, places MySQL,
Chroma and MinIO on an internal data network, and forces session mode/HTTPS
(`docker-compose.production.yml:13-17,38-68,75,103-110`). Nginx overwrites client
IP headers and checks the Host (`deploy/nginx.conf.template:16,25-27`). Backend
trust is restricted to the configured proxy address. Verify these settings on
the actual host; no runtime firewall, TLS or proxy behavior was tested here.

The ordinary Compose binds DB/Chroma/MinIO ports to loopback
(`docker-compose.yml:45-46,58-59,81-83`), while the development Compose contains
unrestricted host mappings (`docker-compose.dev.yml:30-31,93-94,102-103,111-113`).
Do not deploy or merge the development file on the public host. The development
Nginx is HTTP-only (`nginx.conf:21-27`). Production MinIO traffic is internal HTTP
(`backend/app/core/minio.py:12-16`), not end-to-end TLS; moving it off-host requires
a separate transport review. Chroma's supplied production service has no explicit
authentication configuration, making private network isolation essential.

## Phase B — Authentication and authorization assessment

### Authentication controls traced

| Area | Source-grounded conclusion |
| --- | --- |
| Password storage/policy | bcrypt with generated salt; verification rejects over-72-byte inputs. New passwords require eight characters, uppercase/lowercase/digit and at most 72 UTF-8 bytes. `backend/app/core/security.py:18-34`. Policy is not a breached-password check. |
| Registration/login | Exact identity comparisons, dummy hash on missing accounts, active/system checks and verified-email requirement in session mode. Registration creates no session. `backend/app/api/api_v1/auth.py:66-166`. Account existence is disclosed (P1-09). |
| Email recovery | Purpose-bound six-digit code, HMAC with server secret and challenge ID/email, five default attempts, expiry, sent-only challenge, serialized limits, and consumed-code checks. Reset validates password and revokes browser sessions. `backend/app/services/email_otp.py:57-169`; `backend/app/core/config.py:43-46`. OTP is verification/recovery, **not per-login MFA**. |
| Sessions | Random 32-byte URL-safe token and CSRF secret; only hashes persisted; expiration/revocation and verified/active user checked on each authenticated request. Existing presented session is rotated. `backend/app/services/auth_sessions.py:68-119`; `backend/app/models/authentication.py:24-34`. |
| Cookies/CSRF | HTTPS `__Host-` cookies, Path `/`, no Domain attribute, session HttpOnly, Secure and SameSite=Lax. Mutations require exact Origin and constant-time comparison of the session-bound CSRF hash. Local HTTP exception is hostname-limited. `backend/app/services/auth_sessions.py:26-52,78-119`. A valid stolen session remains a bearer credential; these controls do not defeat arbitrary same-origin XSS. |
| Logout/reset | Logout revokes the presented session; reset revokes all account browser sessions. Legacy application keys are not revoked by reset. `backend/app/api/api_v1/auth.py:53-63`; `backend/app/services/email_otp.py:161-168`. |
| JWT/refresh | With session mode enabled, browser JWTs are ignored. Legacy mode signs HS256 JWTs with `sub` and `exp`, pins verification to the configured algorithm, and checks active/system status. No refresh-token endpoint or JWT denylist is present. Default JWT lifetime is 10,080 minutes (seven days); legacy mode has significant conditional weaknesses (P1-04). `backend/app/core/security.py:36-73`; `backend/app/core/config.py:32-38`. |
| Brute force | SQL upsert/row locks implement per-action email/IP counters across workers: send 5/email, 30/IP; other actions 20/email, 60/IP per 15 minutes, with resend cooldown and per-challenge attempts. `backend/app/services/email_otp.py:57-117,141-160`. Proxy trust accuracy and cleanup scheduling need runtime verification. |
| CORS | No permissive CORS middleware/header was found in the inspected app. Same-origin deployment is intentional; cross-origin credential access is not enabled by the application. CSRF is enforced separately, not delegated to CORS. `backend/app/main.py:16-25`; `frontend/src/lib/api.ts:15-48`. |

### Critical normal-user access matrix

“Blocked in source” means the reviewed call chain rejects unauthorized IDs; it is
not a claim that every deployed configuration or concurrency case was tested.

| Attempt by a normal user | Trace and conclusion |
| --- | --- |
| Read another user's private paper or metadata | **Blocked in source.** Private routes depend on `get_current_user`; document lookup joins KB and checks document ID, KB ID, owner, private/non-system scope. `backend/app/api/api_v1/knowledge_base.py:553-564` → `backend/app/services/authorization.py:56-83`. Catalog and preview also scope their queries (`backend/app/api/api_v1/knowledge_base.py:95-104,357-377`; `backend/app/services/private_library.py:23-35`). |
| Download an unauthorized file | **Blocked in source.** Authorization precedes MinIO read; path comes from the authorized SQL document and is checked against its KB prefix. `backend/app/api/api_v1/knowledge_base.py:113-131` → `backend/app/services/private_library.py:60-64`. Public download uses corpus publication/admin rules (`backend/app/api/api_v1/corpus.py:79-101` → `backend/app/services/public_corpus.py:103-115`). |
| Read someone else's conversations | **Blocked in source.** Chat owner and private-source membership are checked, including list reads; stale assistant evidence is filtered on reopening. `backend/app/api/api_v1/chat.py:26-31,65-88` → `backend/app/services/authorization.py:86-99`. |
| Modify another user's publication request | **Blocked in source.** Owner cancellation/withdrawal uses `(id, owner_id)`; metadata decisions require admin. `backend/app/services/researcher_publications.py:262-280,457-465`. |
| Publish directly or approve own request as a normal user | **Blocked in source.** Approve route delegates to `_require_corpus_admin` → corpus management → `require_admin`. `backend/app/api/api_v1/researcher.py:133-137` → `backend/app/services/researcher_publications.py:44-45,395-397` → `backend/app/services/public_corpus.py:76-85` → `backend/app/services/authorization.py:23-45`. An actual admin may approve their own submission; separation of duties is not currently a specified rule. |
| Access admin queue/source/photo APIs | **Blocked for normal users.** Services require corpus admin. Review source is resolved from the request's document, then owner/private-KB checks; arbitrary private document ID is not accepted. `backend/app/services/researcher_publications.py:288-364`. Access duration after cancellation needs policy verification (P1-08). |
| Change their role / become admin through profile or registration | **No route found.** Registration manually constructs the user and assigns researcher; profile schema has only profile fields, while user ID is actor-derived. `backend/app/api/api_v1/auth.py:99-105`; `backend/app/schemas/researcher.py:9-25`; `backend/app/services/researcher_publications.py:55-65`. |
| Leak private content through query scope/vector metadata | **Blocked in the traced path.** All selected IDs must resolve; retrieval is filtered and then SQL-rehydrated/rechecked. Client chat scope/history is replaced by persisted values. `backend/app/services/retrieval_scope.py:20-65,95-124`; `backend/app/api/api_v1/chat.py:98-125`. |
| Reopen someone else's comparison/analysis/history | **Blocked in source.** Saved run must match actor ID; current source permissions and hashes are checked. `backend/app/services/comparison.py:178-203`; `backend/app/services/analysis_history.py:12-48`; UUID recovery is also owner-bound (`backend/app/api/api_v1/insights.py:98-105`). |
| Read private student profile details or personal AI keys | **Blocked in normal-user routes.** Own profile/key uses actor ID. Consented public card explicitly selects name/department/degree/research area/photo, excluding Ag number/class/section. AI-key responses expose only last four characters, not ciphertext/plaintext. `backend/app/services/researcher_publications.py:48-52,500-532`; `backend/app/api/api_v1/ai_settings.py:23-52`; `backend/app/services/ai_settings.py:75-116`. Photo metadata has a separate risk (P1-12). |

Existing authorization/security test sources support the intended boundaries:
`backend/tests/test_phase2_authorization.py:223-263,320-348`,
`backend/tests/test_phase12_researcher_publication.py:69-91`,
`backend/tests/test_phase20_security.py:119-127`, and
`backend/tests/test_phase21_redteam.py:13-39,66`. They were inspected, not executed
as part of this audit.

## Phase C — Frontend security assessment

- No production `dangerouslySetInnerHTML`, DOM `innerHTML` assignment, `eval` or
  `new Function` sink was found in `frontend/src`. An `innerHTML` reference is a
  test assertion, not application rendering.
- AI Markdown uses `react-markdown`, `skipHtml`, GFM and highlighting; no raw-HTML
  plugin or custom unsafe URL transform is configured. External images are
  replaced with text. Citation text is rendered as React text, with integer IDs
  used for source links (`frontend/src/components/chat/answer.tsx:135-143,185-198,219-232`;
  `frontend/src/lib/answer-images.ts:1-4`). This is a positive control, not proof
  of zero XSS in the complete dependency chain. Model-generated ordinary links
  remain clickable; an external-link warning is a reasonable phishing safeguard.
- Normal authentication stores no session secret in browser storage. Legacy mode
  still writes JWTs to `localStorage` (P1-04). Theme preference and an analysis
  request UUID are stored locally; UUID possession does not bypass owner checks
  (`frontend/src/components/insights/analysis-workflow.tsx:64`;
  `backend/app/api/api_v1/insights.py:98-105`).
- Personal AI keys exist temporarily in form state, are sent only to the same-origin
  settings API, and are cleared after actions. They are not written to browser
  storage (`frontend/src/components/researcher/ai-provider-settings.tsx:16,22-48,63-68`).
  No `NEXT_PUBLIC` secret consumption was found in application source; the
  development Compose's `NEXT_PUBLIC_API_URL` is a URL, not a secret. This is not
  a scan of deployed JavaScript bundles or repository history.
- API helpers request `no-store`, same-origin cookies and CSRF headers
  (`frontend/src/lib/api.ts:15-48`). Redirects inspected use fixed local paths;
  no user-controlled external redirect sink was found. The helpers themselves
  accept arbitrary URL strings, so maintain same-origin call sites; adding an
  untrusted absolute URL in future could forward auth headers.
- Production proxy supplies HSTS, nosniff, SAMEORIGIN framing and referrer policy;
  there is no application-page CSP (P1-06). File responses separately use sandbox
  CSP. Local HTTP headers are not equivalent to the production template.

## Phase D — Backend security assessment

| Area | Assessment |
| --- | --- |
| Validation | Academic/researcher/selection schemas constrain fields and forbid extra fields in key workflows. Legacy preview and processing payloads have gaps (P1-03); chat accepts a generic body but validates the final message and replaces supplied history (`backend/app/api/api_v1/chat.py:95-111`). A 100 MB global proxy body cap is not an appropriate small JSON limit for every endpoint. |
| SQL injection | Reviewed user-derived queries use SQLAlchemy predicates/bind values. Public full-text terms are normalized before constructing the parameter value (`backend/app/services/public_corpus.py:150-167`). Upserts for auth/corpus are SQLAlchemy statements. No request-controlled raw SQL execution sink was identified. This is not a database-engine or stored-procedure audit. |
| Commands/deserialization | No reachable request-derived shell command, `eval`/`exec`, unsafe pickle load or unsafe YAML load was found in `backend/app`. Third-party parsers/model-loading dependencies were not internally audited. Alembic uses its Python API, not request-controlled shell execution (`backend/app/startup/migarate.py:84-100`). |
| Path traversal | Current upload names reject slash, backslash, colon and control characters; allowed extensions are fixed. Object staging uses random keys; downloads use authorized DB paths and KB-prefix checks. `backend/app/services/upload_validation.py:14-49`; `backend/app/api/api_v1/knowledge_base.py:275-318`; `backend/app/services/private_library.py:60-64`. No confirmed current HTTP path-traversal route was found. Historical stored filenames and parser behavior still warrant controlled verification. |
| SSRF | Personal provider settings cannot choose arbitrary endpoint URLs. Server-configured providers and MinIO are trusted-operator inputs; document parsers receive local temporary files. No direct user-controlled HTTP URL fetch was found. Whether third-party Markdown/DOCX/PDF parsing follows external resources is unverified; no external-resource probe was performed. |
| Errors/debug/logs | API 422 responses omit submitted values and generic 500 responses avoid stack traces (`backend/app/core/http_privacy.py:28-47`). FastAPI is not instantiated with `debug=True` (`backend/app/main.py:16-20`). Residual raw logging exists (P1-10); generic responses do not sanitize infrastructure logs. |
| Timeouts | Current OpenAI/personal clients set 45-second SDK timeouts; rewrite has a 20-second deadline; SMTP is bounded. Alternate LLM/embedding/MinIO constructors do not set comparable explicit application deadlines (`backend/app/services/llm/llm_factory.py:20-65`; `backend/app/services/chat_service.py:237-243`; `backend/app/core/minio.py:12-17`; `backend/app/services/embedding/embedding_factory.py:32-47`). Library defaults are not established here. Nginx's 180-second read timeout does not ensure underlying work stops. |
| Background tasks/races | Private tasks run in FastAPI's background thread pool, not a durable external job queue (`backend/app/api/api_v1/knowledge_base.py:462-479`). Public tasks use BackgroundTasks too. Restart/cancellation/retry behavior and resource admission need verification. Row locks protect many lifecycle transitions; nested withdrawal commits create P1-07. |
| Startup privilege | API startup can run migrations automatically (`backend/app/main.py:28-39`; `backend/app/startup/migarate.py:84-93`). Production DB grants should be reviewed and migration authority separated from the normal runtime account. No migration was run by this audit. |
| AI trust | Current retrieval and citation/source checks protect identity/scope; prompt instructions alone cannot ensure scientific faithfulness or eliminate injection. Full AI adversarial evaluation is outside this read-only Part 1. The previous live interpretation failure is a reliability issue, not proof of an authorization exploit. |

## Findings

### P1-01 — Legacy application keys are recoverable, long-lived credentials

**Severity:** High. **Confidence:** Confirmed.

- **Evidence:** `backend/app/services/api_key.py:21-39` generates a random key,
  stores it verbatim and performs plaintext equality lookup.
  `backend/app/models/api_key.py:10-15` has no expiry/hash field.
  `backend/app/schemas/api_key.py:16-22` includes `key`; list/update/delete routes
  return this projection (`backend/app/api/api_v1/api_keys.py:14-27,46-85`). Password
  reset revokes only browser sessions (`backend/app/services/email_otp.py:163-168`).
- **Exploit scenario:** a read-only DB/backup leak, or a compromised owner browser
  session that lists keys, yields a reusable credential. It remains valid for
  private retrieval after a password reset unless the key is separately disabled.
- **Impact:** private research extraction using the victim's API-key identity.
  This key does not automatically authenticate the admin/browser APIs. Personal
  AI-provider keys use a different encrypted design and are not this finding.
- **Remediation:** disable the legacy surface before launch if unused, or migrate
  to hash-at-rest/show-once keys with scopes, rotation/expiry and a deliberate
  reset/revocation policy. Keep owner checks and do not silently break integrations.
- **Verification:** later, on disposable accounts/database, verify listing never
  reveals raw keys, a DB-only leak cannot authenticate, scopes/expiry apply and
  reset/revoke behavior matches policy. No such test was run here.

### P1-02 — No application-level admission budget for expensive authenticated work

**Severity:** High. **Confidence:** Confirmed.

- **Evidence:** generation routes go straight from authentication to services:
  `backend/app/api/api_v1/chat.py:90-129`, `backend/app/api/api_v1/retrieval.py:42-45`,
  `backend/app/api/api_v1/insights.py:78-90`. Private uploads/process scheduling are in
  `backend/app/api/api_v1/knowledge_base.py:260-345,390-479`. The explicit shared
  rate limiter is authentication-only (`backend/app/services/email_otp.py:57-88`).
  Production proxy configuration has no request/concurrency quota
  (`deploy/nginx.conf.template:1-37`); Compose declares no service memory/CPU limits
  (`docker-compose.production.yml:5-84`).
- **Exploit scenario:** a verified account repeatedly submits different AI jobs,
  uploads or collection/query operations. Authentication and individual input
  bounds still permit sustained expensive work. Self-registration is not limited
  to an invitation list in `backend/app/api/api_v1/auth.py:66-109`.
- **Impact:** exhausted shared free-provider quota, possible configured-provider
  cost, CPU/RAM/disk exhaustion and denial of service to legitimate students.
  Framework thread-pool defaults are not a per-user quota; BYOK does not remove
  local parsing/embedding costs.
- **Remediation:** shared per-user/IP admission and concurrency limits, daily AI
  and storage budgets, bounded queue/backpressure, endpoint-specific body limits
  and cancellation/deadline policy. Budget the application default provider too.
- **Verification:** later use controlled low-rate synthetic requests to confirm
  excess work is rejected before provider/parser execution, across workers and
  distinct request UUIDs, while another user's normal work remains available.

### P1-03 — Preview input can cause excessive synchronous parsing/output

**Severity:** High. **Confidence:** Confirmed.

- **Evidence:** `backend/app/schemas/knowledge.py:89-92` leaves document-list length,
  duplicate IDs, chunk size and overlap unconstrained. The async route loops over
  every supplied ID (`backend/app/api/api_v1/knowledge_base.py:347-388`). The awaited
  async helper performs synchronous MinIO download, parser loading, splitting and
  materialization of **all** chunks (`backend/app/services/document_processor.py:187-235`).
  PDF acceptance checks a header, not page/text expansion (`backend/app/services/upload_validation.py:33-34`).
- **Exploit scenario:** a user previews their own large or repeatedly selected
  document with extremely small chunks, or submits a computationally difficult
  otherwise accepted PDF. No unauthorized document is needed.
- **Impact:** blocking the API event loop and disproportionate allocation/response
  size. Parser resource exhaustion is plausible; no malicious PDF was executed.
- **Remediation:** bounded distinct IDs, validated chunk-size/overlap relationship,
  page/extracted-text/chunk/output caps, and deadline/resource-limited parsing
  outside the API event loop. A byte-size cap alone is insufficient.
- **Verification:** later use small benign fixtures to assert invalid/boundary
  options get 422 before loading, preview output is capped, deadlines terminate
  work and health/auth requests remain responsive. Do not stress the live server.

### P1-04 — Unsafe legacy authentication can be enabled by configuration

**Severity:** High. **Confidence:** Confirmed, conditional on legacy mode.

- **Evidence:** `backend/app/core/config.py:32-38` contains a nonempty built-in JWT
  secret fallback, seven-day JWT lifetime and `EMAIL_OTP_ENABLED=False` default.
  `backend/app/core/security.py:46-73` switches to JWT authentication when disabled.
  Origin/password-policy/rate-limit/verification gates in registration/login are
  conditional (`backend/app/api/api_v1/auth.py:73-79,132-165`). Legacy logout does
  not revoke a JWT (`backend/app/api/api_v1/auth.py:53-63`). The frontend saves legacy tokens in localStorage
  (`frontend/src/components/auth/password-login.tsx:39-45`).
- **Exploit scenario:** deploying outside the intended production profile with
  legacy mode and an unset/customarily reused signing secret permits forged
  identities; with a strong secret, long-lived stolen JWTs still survive logout.
  Disabling email mode also removes the normal login throttles/verification gate.
- **Impact:** conditional account impersonation and weaker recovery/revocation.
  **This is not a claim that the current session deployment accepts forged JWTs.**
  The supplied production Compose explicitly forces session mode
  (`docker-compose.production.yml:13-17`).
- **Remediation:** fail closed on insecure production authentication settings;
  remove/explicitly prohibit unsupported legacy mode for public deployment and
  eliminate built-in credential fallbacks. If retained, independently harden its
  policy, required JWT claims, lifetime, revocation and browser storage.
- **Verification:** later run a disposable configuration matrix proving production
  cannot start in legacy mode and JWTs are rejected in session mode. Never test
  guessed credentials against real accounts.

### P1-05 — Parser process runs with unnecessarily broad container privilege

**Severity:** Medium. **Confidence:** Confirmed in supplied build configuration.

- **Evidence:** `backend/Dockerfile:1-35` copies/runs the backend without a non-root
  `USER`. `docker-compose.production.yml:5-30` has no user override/read-only root
  or capability-drop policy. Untrusted document parsing executes in the same
  application process (`backend/app/services/document_processor.py:293-304`).
- **Exploit scenario:** if an uploaded-document parser/dependency vulnerability
  enables code execution, it executes with the backend's filesystem, environment
  and network privileges. No parser RCE is confirmed by this audit.
- **Impact:** larger compromise boundary: research storage, runtime secrets and
  writable application/container files. Container root alone does not prove host
  escape; `no-new-privileges` is already present and is beneficial.
- **Remediation:** non-root backend, least capabilities, explicit writable paths
  and resource-limited parser isolation; test model-cache/upload permissions.
- **Verification:** later inspect the built image/runtime user and mounts, then
  run normal synthetic ingestion under reduced privilege. Do not exploit a parser.

### P1-06 — No CSP for application HTML pages

**Severity:** Medium. **Confidence:** Confirmed in supplied configuration.

- **Evidence:** `frontend/next.config.js:4-15` defines no security headers;
  `deploy/nginx.conf.template:18-21` supplies other headers but no CSP. CSP found
  on API file responses is only a file sandbox, e.g.
  `backend/app/api/api_v1/knowledge_base.py:127-131`, not an application-page policy.
- **Exploit scenario:** a future UI/dependency injection defect has no CSP
  script/connect restriction as a second layer. This is defense-in-depth weakness,
  **not a confirmed existing XSS exploit**.
- **Impact:** potentially greater execution/exfiltration impact from such a defect.
  Cross-origin framing is already restricted by production `X-Frame-Options:
  SAMEORIGIN`; this finding does not claim that control is absent.
- **Remediation:** introduce a tested nonce/hash-based Next.js-compatible policy,
  initially report-only, including script/connect/object/base/form/frame controls;
  preserve streaming, source previews and required auth behavior.
- **Verification:** later inspect actual document response headers and normal flows
  in staging, including browser console violations and framing tests. No browser
  or network test was performed in Part 1.

### P1-07 — Withdrawal decision is not one atomic transaction

**Severity:** Medium. **Confidence:** Likely; race not reproduced.

- **Evidence:** `backend/app/services/researcher_publications.py:479-496` locks a
  pending withdrawal, calls `archive_document`, then reacquires and sets its
  decision. `backend/app/services/public_corpus.py:229-240` commits inside that
  call, releasing the original transaction's lock before the decision is saved.
  The reacquired request is not checked again for pending status.
- **Exploit scenario:** two authorized admins approve/deny the same request during
  that interval. A denial can be recorded after archival, or one decision can
  overwrite the other's status/reviewer. A normal user cannot reach these APIs.
- **Impact:** inconsistent publication/withdrawal status and unreliable decision
  attribution; potential inappropriate continued visibility expectations.
- **Remediation:** let one transaction own archival plus withdrawal decision;
  avoid nested commits, enforce conditional pending-state transitions and keep
  an immutable decision event where required.
- **Verification:** later use two controlled sessions against disposable MySQL to
  verify exactly one decision succeeds and archival/status/reviewer remain
  consistent after failures and concurrency. Do not race live publication data.

### P1-08 — Historical request keeps admin access to current private source/profile

**Severity:** Medium. **Confidence:** Requires Verification of intended policy.

- **Evidence:** cancellation sets status to cancelled
  (`backend/app/services/researcher_publications.py:262-269`), but admin detail,
  photo and source reads at `326-364` require a request/owner match without checking
  request status. They load the current profile and source, not only a historical
  audit snapshot. A denied request behaves similarly.
- **Exploit scenario:** an authorized global admin uses a known cancelled/denied
  request ID to continue viewing its private source/current private profile.
- **Impact:** potential access beyond the duration a student expects when cancelling
  publication. Access remains limited to a submitted source; this is not arbitrary
  private-library access and may be intentional retention policy.
- **Remediation:** define review-access expiry separately from audit-history retention.
  If cancellation/denial should revoke source access, enforce that state in all
  review reads while retaining appropriately minimized history.
- **Verification:** obtain the policy decision, then later check a synthetic
  cancelled/denied request's source/photo/profile access against that policy.

### P1-09 — Registration discloses account existence

**Severity:** Low. **Confidence:** Confirmed.

- **Evidence:** `backend/app/api/api_v1/auth.py:83-97` returns distinguishable
  existing-email and existing-username errors. OTP issuance uses generic wording,
  but eligible requests synchronously send SMTP while ineligible requests return
  early (`backend/app/services/email_otp.py:104-130`). Timing/error enumeration
  through SMTP is only a potential additional signal, not measured here.
- **Exploit scenario:** an unauthenticated requester probes known university email
  addresses/identifiers within the allowed rate budget or across source IPs.
- **Impact:** membership disclosure useful for targeted phishing/password attacks;
  it does not itself authenticate the requester.
- **Remediation:** use consistent account-enrollment responses/workflows where
  practical; retain strong rate limits and avoid recipient-dependent public errors.
- **Verification:** later compare response shapes/statuses for disposable existing
  and nonexistent users, and assess timings without probing real student identities.

### P1-10 — Private filenames/paths and raw infrastructure exceptions reach logs

**Severity:** Low. **Confidence:** Confirmed for metadata/raw logging; secret leakage unproven.

- **Evidence:** `backend/app/services/document_processor.py:251,273-283` logs original
  filenames, object/temp paths and some raw storage exceptions. Startup logs raw
  database/migration exceptions (`backend/app/startup/migarate.py:39-41,99-101`).
  Safer category-only handling exists elsewhere and for final task responses.
- **Exploit scenario:** a log reader or exported support bundle exposes research
  filenames/paths; a future provider/driver exception could include sensitive
  details. No actual secret-bearing log was inspected or disclosed in this audit.
- **Impact:** research metadata exposure and conditional credential/detail leakage
  beyond the app's owner-only UI boundary.
- **Remediation:** identifiers plus bounded error categories, tested redaction and
  restricted retention/access. Review proxy query-string logs for the GET retrieval
  integration without assuming they are sanitized.
- **Verification:** later trigger benign fixture failures with synthetic canary
  filenames/credentials and inspect protected staging logs; never log real keys.

### P1-11 — Runtime environment includes infrastructure-level credentials

**Severity:** Medium. **Confidence:** Confirmed in supplied production template.

- **Evidence:** backend receives the entire production environment file
  (`docker-compose.production.yml:7`). Its example includes application and root
  MySQL credentials plus storage credentials (`deploy/production.env.example:18-23`).
  MinIO uses the same storage variables as its **root** credentials
  (`docker-compose.production.yml:60-65`), while the backend uses them for requests
  (`backend/app/core/minio.py:12-16`).
- **Exploit scenario:** compromise of the API/parser process exposes credentials
  with greater administrative reach than its document bucket operations need.
- **Impact:** larger storage-control and secret-compromise boundary. Actual MySQL
  root remote-host permissions were not inspected; remote root login is not asserted.
- **Remediation:** separate root/bootstrap secrets from the backend environment;
  use a scoped MinIO service account and narrowly privileged DB runtime user;
  reserve migration authority for controlled deployment operations.
- **Verification:** later inspect only credential names, account grants and policy
  capabilities in staging; verify the backend cannot administer storage accounts
  or use DB privileges outside its intended runtime needs. Do not print values.

### P1-12 — Consented public profile photos retain original embedded metadata

**Severity:** Medium. **Confidence:** Likely privacy exposure; uploaded metadata unexamined.

- **Evidence:** image validation decodes/verifies the photo but returns only its
  MIME/extension (`backend/app/services/researcher_publications.py:72-91`). Storage
  writes the original bytes (`94-106`), and consented published-photo access serves
  the stored object (`523-532`). No re-encoding/EXIF removal occurs on that path.
- **Exploit scenario:** a student uploads a JPEG containing GPS/device metadata and
  later consents to its public researcher card. Another authenticated user downloads
  the published photo and reads metadata that the UI never displays.
- **Impact:** unintended location/device/timestamp disclosure. Public photo access
  correctly requires consent; the concern is hidden metadata, not bypassing consent.
- **Remediation:** safely re-encode bounded decoded pixels into an approved format,
  stripping location/comments/other unnecessary metadata before storage.
- **Verification:** later use a benign synthetic photo with fake metadata; confirm
  the visible photo survives and sensitive metadata is absent from stored/served
  bytes. No student's photo was inspected here.

## 1. Executive summary

**Part 1 is complete as a static audit. Public deployment should remain gated.**
Twelve findings were recorded: four High, six Medium and two Low. Nine are
source/configuration-confirmed, two Likely, and one Requires Verification. No
Critical finding, normal-user cross-owner document access, arbitrary SQL execution,
command execution or current browser XSS exploit was confirmed. Absence of a
confirmed exploit is not assurance that none exists.

Strong controls include server-enforced ownership, fresh SQL retrieval checks,
revocable hashed sessions, bound CSRF tokens, explicit admin allowlisting, scoped
publication review, encrypted personal AI keys and safe text/Markdown rendering.
Priority gaps concern legacy application credentials, resource abuse and parsing,
unsafe legacy authentication configuration, and operational privilege boundaries.
The separate Phase 21 live interpretation failure remains unresolved; it is not
reclassified as a security vulnerability to inflate this report.

## 2. Authentication security verdict

**Reasonable session-mode foundation; conditional public-release approval only.**
Require the production session/HTTPS configuration, preserve Origin/CSRF checks,
address legacy application-key handling (P1-01), and prohibit insecure JWT fallback
(P1-04). Verify cookies, proxy trust, recovery/logout revocation and multi-worker
rate limits on the real deployment. This is not per-login MFA and not a guarantee
against stolen valid sessions or same-origin code execution.

## 3. Authorization security verdict

**No confirmed normal-user IDOR/BOLA in the traced flows.** Owner and publication
predicates are present through services/SQL, including saved results and API-key
retrieval. Admin does not imply unrestricted private-library access. Resolve the
withdrawal race (P1-07) and cancelled-request review-access policy (P1-08). Do not
claim department/supervisor isolation until it is implemented and independently
tested. Repeat the access matrix with synthetic users before public release.

## 4. Frontend security verdict

**Positive rendering/storage controls, with remaining hardening work.** Raw AI HTML
and automatic external images are disabled; current session credentials are not
stored in localStorage. The legacy JWT path remains conditional risk. Add and
verify an application CSP (P1-06), retain safe source-link construction, inspect
deployed bundles for accidental secrets, and validate actual HTTPS/framing/cache
headers. Client navigation checks are not counted as authorization.

## 5. Backend security verdict

**Permission controls are stronger than resource/operational isolation.** No
direct request-controlled command/raw-SQL/unsafe-deserialization sink was found.
Preview parsing and expensive authenticated actions need explicit admission and
resource budgets. Reduce backend/container/storage privilege, complete transaction
and logging review, and verify third-party parser/network behavior in an isolated
environment. No vulnerability database/dependency/image scan was performed offline.

## 6. P0 issues blocking public deployment

Here **P0 means required before this app's public launch**, not a claim that every
item has Critical severity.

1. **P1-01:** disable or safely migrate the exposed legacy plaintext application-key
   surface; decide stolen-key revocation on password/account recovery.
2. **P1-02 and P1-03:** enforce realistic AI/upload/storage/concurrency budgets and
   bounded, off-event-loop previews before accepting arbitrary verified accounts.
3. **P1-04 deployment condition:** use the standalone HTTPS/session production
   configuration; reject insecure fallback settings and keep DB/vector/object
   services inaccessible from the internet. Verify actual TLS/cookie/proxy behavior.
4. Establish parser/runtime and secret least privilege (P1-05/P1-11), or explicitly
   document and accept a narrowly scoped pilot exception with equivalent containment.
   Neither exception nor deployment approval is granted by this report.

Other findings require scheduled remediation or documented policy/risk decisions.
The application is not declared production-ready merely because it serves only
20–30 intended students: public self-registration changes the threat population.

## 7. Issues requiring runtime verification

All items below are **future authorized staging checks**, not executed actions:

- Actual Compose file/image digests, service user/capabilities, CPU/RAM/disk limits,
  port exposure, firewall/private-network policy and absence of dev overrides.
- TLS chain/renewal, Host rejection, correct trusted proxy IP handling, Secure/
  HttpOnly/Host-only cookie behavior, CSRF failure behavior, logout/reset replay,
  expiry and concurrent authentication limits. Confirm expired auth-data cleanup.
- Two researchers plus admin access matrix: private IDs/downloads/chats/history,
  unpublished/archived papers, consented profile projection, API keys and exact
  request-scoped admin access, including stale/deleted/revoked sources.
- Durable/bounded job behavior after client disconnect/restart; parser and provider
  timeouts/cancellation; healthy service behavior under the intended 20–30 users.
- Withdrawal concurrent decisions and crash recovery on disposable MySQL (P1-07).
- Cancelled/denied review-access retention policy and implementation (P1-08).
- Rendered Markdown/link handling, built client bundles, CSP/framing/cache headers,
  logout navigation and browser back/cache behavior. No visual pass is claimed.
- Actual DB grants, MinIO bucket/service-account policy, Chroma network/auth scope,
  secret-file permissions, backup access/encryption and restore capability.
- Photo metadata stripping and parser external-resource behavior using benign
  synthetic fixtures. Do not use real student documents or credentials.
- Runtime/dependency/image vulnerability scanning and supported-version review
  with current advisories require a separately authorized online audit. No current
  CVE-free or dependency-safe claim is made in this offline Part 1.

**End of Part 1. No automatic fixes, Part 2/3 tests, public deployment or push were performed.**
