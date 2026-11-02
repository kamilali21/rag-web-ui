# rAGRI search / ResearchIQ — Final Production Security Audit

**Review started:** 1 November 2026; **completed:** 2 November 2026 (Asia/Karachi)
**Repository:** `C:\Users\tayya\Projects\ResearchIQ`
**Branch / HEAD:** `master-integration` / `995d5afef6b38fa3a336e252719c0e7ab0e0597a`
**Audience:** project owner and release operator; initial 20–30-student pilot
**Inputs:** `SECURITY_AUDIT_PART_1.md`, `SECURITY_AUDIT_PART_2.md`, `SECURITY_AUDIT_PART_3.md`.

## 1. Executive summary

**Security posture: MODERATE. Pilot readiness: NOT READY for public exposure.**

The application has meaningful server-side controls: owner-checked private data,
published-only corpus access, request-scoped admin review, revocable hashed sessions,
Origin/CSRF enforcement, encrypted personal AI credentials, permission-checked RAG
and constrained output rendering. No confirmed Critical exploit, general normal-user
IDOR, SQL injection or model-driven code execution was found in the reviewed paths.
This is not proof that no vulnerabilities exist.

Operational controls lag behind application authorization. Shared resource abuse,
unbounded previews, plaintext legacy application keys, broad parser/runtime privilege,
non-durable jobs and unverified multi-store recovery block launch. Production network
and TLS templates are promising but have not been accepted on a public host. ARM64
compatibility, exact release dependency vulnerabilities and host controls remain unknown.

### Verdict metrics

| Metric | Result |
| --- | --- |
| Unique consolidated findings | **29** after deduplication |
| Severity totals | **0 Critical, 6 High, 21 Medium, 2 Low** |
| Confidence totals | **18 Confirmed, 5 Likely, 6 Requires Verification** |
| Confirmed Critical findings | **0** |
| Confirmed High findings | **5**: F01, F02, F03, F04, F15 |
| Important qualification | F04 is an unsafe-profile/legacy-mode condition; F15 is a source-confirmed unauthenticated internal-store boundary. Neither proves current public exposure. F24 is High impact but Requires Verification, not a sixth confirmed High. |
| Findings explicitly requiring policy/runtime verification | F08, F18, F24, F26, F27, F29; the five Likely findings also need controlled reproduction. Deployment acceptance remains necessary even for source-confirmed findings. |
| Public deployment verdict | **Do not launch until the P0 gates below are satisfied.** No acceptance exception is granted by this report. |

Scope is offline source/configuration review, not a penetration test, certification,
comprehensive secret-history scan or current CVE clearance. No audit exploit/load
tests, external services, installs, migrations or deployment were used. Only the two
final-report files were created during Part 3. Existing auth/tunnel fixes and their
prior tests are outside this audit; they were not silently committed or extended.
No secret values are included. File references are repository-relative. Part 1 used
the earlier commit lines; current auth references below account for the later local
origin/cookie patch. Other retained finding evidence was reviewed against the same
unchanged application baseline.

## 2. Architecture and attack surface

```text
Untrusted browser / uploaded papers / prompts
                    |
             HTTPS Nginx edge
          /                     \
 Next.js frontend             FastAPI
 (no store access)           /   |    \
                          MySQL Chroma MinIO
                         authority vectors files
                              |
             permitted SQL evidence + history
                              |
             fixed personal / operator LLM provider
```

Production has app and internal data networks. Backend is the bridge; host/Docker
operators can access both. External integrations include model APIs, optional remote
embeddings, SMTP and HF model downloads. The production frontend has no direct store
network or provider key. Nginx exposes 80/443 only in the supplied production profile
(`docker-compose.production.yml:28,34,51-75,103-110`).

The API prefixes cover authentication, private collections/documents, public corpus,
departments, researcher profiles/publication requests, chats, retrieval/summaries,
insights/history, personal AI settings and legacy application keys
(`backend/app/api/api_v1/api.py:5-17`). The integration retrieval API remains under
`/openapi` (`backend/app/api/openapi/api.py:5-6`). Public docs/health are exposed by
the app/proxy; hidden UI tabs do not disable their endpoints.

MySQL defines authority. Private owner + scope + non-system predicates, active user
checks, role/allowlist admin checks and exact submitted-source review are enforced
in services. Chroma supplies candidates; fresh SQL ownership/readiness and chunk
rehydration prevent vector metadata from granting user access. An operator/API
compromise or direct store access bypasses that application boundary. Uploaded
paper text and model output are always untrusted, including a paper approved for
publication. Approval establishes visibility, not scientific truth.

## 3. Consolidated findings table

Priority: **P0** before public exposure; **P1** before expanding the pilot; **P2**
production hardening; **P3** long-term improvement. Priority is not severity. Some
P0 entries require evidence/acceptance rather than a proven code fix. Policy choices
that affect student consent should be resolved before real data even where code
remediation is P1. No new feature phases or historical checkpoints are renumbered.

| ID | Finding | Severity | Confidence | Priority | Origin |
| --- | --- | --- | --- | --- | --- |
| F01 | Plaintext, long-lived legacy application keys | High | Confirmed | P0 | P1-01 |
| F02 | Missing per-user/global AI, job and storage admission | High | Confirmed | P0 | P1-02 + P2-03 |
| F03 | Unbounded synchronous preview work | High | Confirmed | P0 | P1-03 |
| F04 | Unsafe dev/legacy deployment condition | High | Confirmed, conditional | P0 | P1-04 + P3-01 |
| F05 | Root backend/parser with broad runtime privileges | Medium | Confirmed | P0 | P1-05 |
| F06 | No application-page CSP | Medium | Confirmed | P2 | P1-06 |
| F07 | Non-atomic withdrawal decision | Medium | Likely | P1 | P1-07 |
| F08 | Historical review retains current private-source/profile access | Medium | Requires Verification | P1 | P1-08 |
| F09 | Registration account enumeration | Low | Confirmed | P2 | P1-09 |
| F10 | Private metadata/raw exception logging | Low | Confirmed | P1 | P1-10 |
| F11 | Infrastructure-level secrets available to backend | Medium | Confirmed | P0 | P1-11 |
| F12 | Profile photos retain embedded metadata | Medium | Likely | P1 | P1-12 |
| F13 | Cited output may still obey injected/false evidence | Medium | Likely | P1 | P2-01 |
| F14 | Retry can resend evidence after revocation | Medium | Likely | P1 | P2-02 |
| F15 | Chroma raw-content API relies on network isolation | High | Confirmed, conditional reachability | P0 | P2-04 |
| F16 | Staging cleanup can lose MinIO object references | Medium | Confirmed | P1 | P2-05 |
| F17 | Failure-path local temp cleanup gaps | Medium | Confirmed | P1 | P2-06 |
| F18 | Source removal is not snapshot/backup erasure | Medium | Requires Verification | P1 | P2-07 |
| F19 | SQL connections can remain occupied across LLM waits | Medium | Likely | P1 | P2-08 |
| F20 | Unbounded history materialization/list inputs | Medium | Confirmed | P1 | P2-09 |
| F21 | Unlocked backend builds/model artifacts | Medium | Confirmed | P1 | P3-02 |
| F22 | Stale CI/package-manager release gates | Medium | Confirmed | P1 | P3-03 |
| F23 | No durable crash recovery for persisted jobs | Medium | Confirmed | P0 | P3-04 |
| F24 | Coordinated encrypted off-host restore unproven | High | Requires Verification | P0 | P3-05 |
| F25 | Incomplete readiness/reboot supervision | Medium | Confirmed | P1 | P3-06 |
| F26 | Host log bounds/disk monitoring unestablished | Medium | Requires Verification | P1 | P3-07 |
| F27 | ARM64 image/dependency/capacity acceptance absent | Medium | Requires Verification | P0 for ARM deployment | P3-08 |
| F28 | Preflight omits personal-key encryption readiness | Medium | Confirmed | P1 | P3-09 |
| F29 | Exact release vulnerability/support status unknown | Medium | Requires Verification | P0 verification gate | P3-10 |

Deduplication: P2-03 expands P1-02 and is counted only as F02; P3-01 expands P1-04
and is counted only as F04. Root/parser, broad credentials, vector isolation,
missing quotas and cross-store failure paths are cross-referenced rather than
counted again in infrastructure sections. New Part 3 findings cover distinct build,
CI, recovery, readiness, retention, architecture and release-verification mechanisms.

## 4. Confirmed Critical findings

**None confirmed.** The audit did not demonstrate unauthenticated RCE, arbitrary
cross-user private retrieval, admin escalation or production JWT forgery. Default
credentials and raw-store exposure would be serious if deployed, but their presence
in development source does not establish a current internet exploit. Zero confirmed
Critical findings is not a clean bill of health or evidence that the app is deployable.

## 5. Confirmed High findings

### F01 — Legacy application keys are plaintext, long-lived and recoverable

**Severity:** High. **Confidence:** Confirmed. **Priority:** P0.

- **Evidence:** `backend/app/services/api_key.py:21-39`; `backend/app/models/api_key.py:10-15`;
  `backend/app/schemas/api_key.py:16-22`; `backend/app/api/api_v1/api_keys.py:14-27`;
  `backend/app/services/email_otp.py:163-168`.
- **Impact / scenario:** DB/backup disclosure or a compromised owner session can
  recover reusable keys for private integration retrieval. Password reset revokes
  browser sessions, not these keys. This is separate from encrypted personal LLM keys.
- **Remediation:** disable unused legacy key/integration routes at the server, or
  migrate to hash-at-rest/show-once scoped keys with expiry/rotation/revocation policy.
- **Verification:** disposable-account tests for list masking, hashed lookup,
  reset/revoke/expiry and unchanged owner boundaries; no raw key in DB/API/logs.

### F02 — Expensive authenticated work lacks application admission budgets

**Severity:** High. **Confidence:** Confirmed. **Priority:** P0.

- **Evidence:** `backend/app/api/api_v1/chat.py:90-129`;
  `backend/app/api/api_v1/insights.py:78-105`; `backend/app/api/api_v1/knowledge_base.py:270-345,401-479`;
  `backend/app/services/ai_settings.py:113-125`; `docker-compose.production.yml:5-84`.
- **Impact / scenario:** one verified account repeatedly starts new jobs/streams or
  uploads files, exhausting shared provider, CPU/RAM/disk/SQL capacity. Existing
  per-call output limits and idempotent request IDs do not cap repeated new work.
- **Remediation:** atomic per-user and global call/token/storage/admission budgets,
  bounded queues/concurrency/deadlines, endpoint body limits and container ceilings.
  Include retries/multistage calls and local BYOK costs; do not add paid fallback.
- **Verification:** provider spies and benign concurrency fixtures prove rejection
  before work, correct reservation/retry accounting, cancellation and fair global limits.

### F03 — Preview accepts unbounded work and blocks the API execution path

**Severity:** High. **Confidence:** Confirmed. **Priority:** P0.

- **Evidence:** `backend/app/schemas/knowledge.py:89-92`;
  `backend/app/api/api_v1/knowledge_base.py:347-388`;
  `backend/app/services/document_processor.py:187-237`.
- **Impact / scenario:** repeated IDs, pathological chunk settings or an expensive
  own paper cause synchronous download/parsing/all-chunk materialization within an
  async route. Authorized access can still deny service to other users.
- **Remediation:** cap distinct IDs, enforce chunk/overlap relationships, bound decoded
  pages/text/chunks/output and move parsing into deadline/resource-limited execution.
- **Verification:** small benign boundary fixtures yield early 422/capped output;
  ordinary auth/health remains responsive. No malicious PDF or stress test is needed.

### F04 — Legacy authentication and development profiles are unsafe public defaults

**Severity:** High. **Confidence:** Confirmed conditional configuration. **Priority:** P0.

- **Evidence:** `backend/app/core/config.py:32-41`; `backend/app/core/security.py:46-73`;
  `docker-compose.dev.yml:30-31,84-119`; `nginx.dev.conf:104-110`;
  `docker-compose.production.yml:13-17`; `deploy/README.md:3-6`.
- **Impact / scenario:** selecting dev/legacy mode can expose storage/default
  credentials or enable JWT signing with a built-in fallback and weaker login
  controls. The current HTTPS/session production profile mitigates this condition.
- **Remediation:** enforce standalone production settings, prohibit insecure fallback
  and dev overrides, require independent secrets, and close non-web published ports.
- **Verification:** offline configuration rejection plus later staging TLS/auth/port
  checks. Do not claim current forged-token acceptance or expose stores for testing.

### F15 — Chroma has no supplied service authentication boundary

**Severity:** High. **Confidence:** Confirmed configuration; reachability unverified. **Priority:** P0.

- **Evidence:** `backend/app/services/vector_store/chroma.py:15-32`;
  `docker-compose.production.yml:54-58`; `docker-compose.dev.yml:100-106`.
- **Impact / scenario:** direct data-network/forwarded-port access can expose raw
  research passages or alter/delete vectors without FastAPI ownership checks.
  The supplied production internal network is a real mitigating control.
- **Remediation:** verify backend-only store reachability, cloud/host filtering and
  no storage tunnels; add supported service auth/TLS where the threat boundary
  requires it. Keep SQL reauthorization even with service authentication.
- **Verification:** external/untrusted-container denial and synthetic vector metadata
  poisoning tests; confirm runtime auth, tenants, ports and network membership.

## 6. Medium, Low and verification-dependent High findings

### F05 — Broad backend/parser process privilege

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P0.
- **Evidence:** `backend/Dockerfile:1-35`; `docker-compose.production.yml:5-30`;
  `backend/app/services/document_processor.py:293-304`.
- **Impact:** a hypothetical parser compromise inherits root container, secrets and
  store access. No parser RCE or host escape was confirmed.
- **Remediation:** non-root runtime, least capabilities, explicit writable paths and
  bounded parser isolation while preserving cache/upload access.
- **Verification:** inspect effective user/caps/mounts and normal synthetic ingestion
  under reduced privilege, without exploit payloads.

### F06 — Missing application-page Content Security Policy

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P2.
- **Evidence:** `frontend/next.config.js:4-15`; `deploy/nginx.conf.template:18-21`.
- **Impact:** less defense in depth against a future XSS/dependency injection; no
  current XSS proved. File-response sandbox policies are not a page CSP.
- **Remediation:** tested Next.js-compatible nonce/hash CSP, initially report-only,
  with script/connect/object/base/form/frame restrictions.
- **Verification:** staging headers, browser violation review and normal auth,
  source previews and streaming; retain existing framing/header protections.

### F07 — Withdrawal archival and decision are not atomic

**Severity:** Medium. **Confidence:** Likely. **Priority:** P1.
- **Evidence:** `backend/app/services/researcher_publications.py:479-496`;
  `backend/app/services/public_corpus.py:229-240`.
- **Impact:** nested commit releases a lock before final decision; concurrent admins
  may produce contradictory archive/decision state or overwrite attribution.
- **Remediation:** one transaction and conditional pending-state transition; no nested
  commit between decision and archival.
- **Verification:** two controlled transactions on disposable MySQL prove exactly one
  decision and consistent failure rollback. Normal users remain admin-gated.

### F08 — Cancelled/denied review may retain more private access than intended

**Severity:** Medium. **Confidence:** Requires Verification of policy. **Priority:** P1.
- **Evidence:** `backend/app/services/researcher_publications.py:262-269,326-364`.
- **Impact:** authorized admins can inspect the exact submitted private source and
  current profile after cancellation/denial; this may violate user expectations,
  but could be intentional. It is not arbitrary private-library access.
- **Remediation:** agree review-access expiry versus audit retention; gate current
  source/photo/profile access by that policy and minimize retained snapshots.
- **Verification:** synthetic cancelled/denied requests and documented policy sign-off.

### F09 — Registration reveals account existence

**Severity:** Low. **Confidence:** Confirmed. **Priority:** P2.
- **Evidence:** `backend/app/api/api_v1/auth.py:83-97`;
  `backend/app/services/email_otp.py:104-130`.
- **Impact:** distinguishable errors facilitate membership probing; SMTP timing is
  an additional unmeasured signal, not a confirmed side-channel here.
- **Remediation:** consistent enrollment/recovery responses with rate limits and
  recipient-independent public errors where practical.
- **Verification:** synthetic existing/nonexistent identities, response/status and
  timing comparison without probing real students.

### F10 — Research metadata and raw failures reach logs

**Severity:** Low. **Confidence:** Confirmed metadata logging; secret leakage unproven. **Priority:** P1.
- **Evidence:** `backend/app/services/document_processor.py:251,273-283`;
  `backend/app/startup/migarate.py:39-41,99-101`.
- **Impact:** log access/support bundles disclose filenames/paths; raw exceptions
  could add details. Actual secret-bearing logs were not read.
- **Remediation:** bounded category/ID logging, redaction, restricted access/retention;
  review GET integration query logging.
- **Verification:** harmless synthetic canary errors and protected staging-log review.

### F11 — Runtime application receives infrastructure authority

**Severity:** Medium. **Confidence:** Confirmed template. **Priority:** P0.
- **Evidence:** `docker-compose.production.yml:7,60-65`;
  `deploy/production.env.example:18-29`; `backend/app/core/minio.py:12-16`;
  `backend/app/main.py:28-39`.
- **Impact:** backend compromise exposes unnecessary bootstrap/root secrets and
  MinIO administrative authority; startup also needs migration privileges. Actual
  MySQL root remote grants are unknown.
- **Remediation:** per-service secret scopes, bucket-scoped MinIO account, non-root
  least-privilege runtime SQL identity and controlled migration identity/lifecycle.
- **Verification:** grants/policy capability tests with masked configuration; backend
  must not administer unrelated storage or use unnecessary DB privileges.

### F12 — Original photo bytes can expose embedded private metadata

**Severity:** Medium. **Confidence:** Likely. **Priority:** P1.
- **Evidence:** `backend/app/services/researcher_publications.py:72-106,523-532`.
- **Impact:** a consented public JPEG may disclose GPS/device metadata not shown by
  the UI; consent/authorization still gates the photo itself.
- **Remediation:** bounded safe decode/re-encode stripping unnecessary metadata.
- **Verification:** fake-EXIF fixture retains visible appearance but loses metadata.

### F13 — Citation validation does not establish semantic truth

**Severity:** Medium. **Confidence:** Likely. **Priority:** P1.
- **Evidence:** `backend/app/services/chat_service.py:162-207`;
  `backend/app/services/citations.py:31-43`;
  `backend/app/services/candidate_gaps.py:50-77`.
- **Impact:** instructions/falsehoods inside a permitted paper can yield apparently
  cited unsupported claims. No cross-user disclosure, tool execution or successful
  injected answer was demonstrated by this audit.
- **Remediation:** separate instruction/data roles, retain strict source/output
  checks, evaluate adversarial grounding/abstention and show uncertainty.
- **Verification:** approved synthetic injection fixtures across all four AI features,
  served models and human claim-to-evidence review. A keyword filter is insufficient.

### F14 — Revoked evidence can be resent by a captured-payload retry

**Severity:** Medium. **Confidence:** Likely. **Priority:** P1.
- **Evidence:** `backend/app/services/document_summary.py:216-260,327-395`;
  `backend/app/services/comparison.py:85-167`;
  `backend/app/services/research_analysis.py:197-199,223-232`.
- **Impact:** revocation between initial authorization and retry can allow an extra
  provider transmission before final result rejection. Not an initial cross-owner bypass.
- **Remediation:** reauthorize exact actor/sources/evidence immediately before each
  attempt/stage, including history rewrite; define already-in-flight semantics.
- **Verification:** mocked throttle, second-transaction revocation, assert no second
  payload; check final suppression and cancellation without long DB locks.

### F16 — Failed staging cleanup can leave unreferenced private objects

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P1.
- **Evidence:** `backend/app/api/api_v1/knowledge_base.py:307-335,493-512`;
  `backend/app/services/public_corpus.py:279-301`.
- **Impact:** object put then SQL failure, or failed removal followed by row deletion,
  creates orphaned private data/storage growth. Ordinary lifecycle deletion has
  stronger guards; the defect is these specific staging/expiry paths.
- **Remediation:** retain durable cleanup references, compensating/outbox retries
  and scoped reconciliation with grace periods.
- **Verification:** injected benign put/commit/remove failures on disposable fixtures;
  rerun cleanup and prove unrelated objects unchanged.

### F17 — Download exceptions bypass some local temp cleanup

**Severity:** Medium. **Confidence:** Confirmed control flow. **Priority:** P1.
- **Evidence:** `backend/app/services/document_processor.py:195-203,236-237,254-286,423-455`.
- **Impact:** allocation/download before cleanup finally can retain files/private
  bytes; early missing-task return also bypasses later session close. Exact client
  partial-file behavior and actual residue require verification.
- **Remediation:** encompassing scoped cleanup before download, guaranteed session
  close and crash-safe age-based temp retention.
- **Verification:** synthetic partial-download failure and early-exit tests verify
  no leaked file/session; never sweep arbitrary temp files.

### F18 — Source deletion/archive does not erase historical text

**Severity:** Medium. **Confidence:** Requires Verification of privacy policy. **Priority:** P1.
- **Evidence:** `backend/app/models/analysis.py:28-51`;
  `backend/app/services/comparison.py:303-312`;
  `backend/app/services/citations.py:46-47`; `docs/windows-migration-manifest.md:17-29`.
- **Impact:** private snapshots/chats/backups retain text after API redaction or
  source deletion; possible mismatch with erasure expectations, not proven leakage.
- **Remediation:** distinguish archive, deletion and erasure; agree retention/audit
  exceptions and apply authorized expiry, encryption and backup restrictions.
- **Verification:** trace a synthetic marker through deletion, redaction, expiry and
  isolated restore; obtain policy approval before accepting sensitive papers.

### F19 — SQL connection/transaction occupancy spans slow provider work

**Severity:** Medium. **Confidence:** Likely. **Priority:** P1.
- **Evidence:** `backend/app/db/session.py:5-13`;
  `backend/app/services/comparison.py:171-175,266-293`;
  `backend/app/services/document_summary.py:327-382`.
- **Impact:** slow calls compete with auth/library requests for finite connections;
  no benchmark or unbounded SQLAlchemy pool is claimed.
- **Remediation:** short transactions, release before network waits, reauthorize on
  reacquisition and configure measured pool/timeouts/stale-connection handling.
- **Verification:** provider mocks plus connection/transaction metrics and DB reconnect
  tests; auth/reads must remain available during bounded generation concurrency.

### F20 — Chat history is fully loaded before model-window truncation

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P1.
- **Evidence:** `backend/app/api/api_v1/chat.py:26-31,65-79,108-111`;
  `backend/app/models/chat.py:24,36-42`.
- **Impact:** many long own conversations cause excessive SQL/Python/response work
  despite the later 20-message LLM window. List skip/limit lack schema ceilings.
- **Remediation:** bounded metadata-only chat list, paginated owner-checked messages,
  SQL-limited recent history and storage/admission ceilings.
- **Verification:** synthetic long histories show bounded rows/payload/latency and
  unchanged owner and stale-evidence filtering.

### F21 — Rebuild/model artifacts are not fully reproducible

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P1.
- **Evidence:** `backend/requirements.txt:1-30`; `backend/Dockerfile:1-18`;
  `frontend/Dockerfile:1-22`; `backend/app/services/embedding/embedding_factory.py:13-21`.
- **Impact:** floating resolutions/base images and unnamed model revision can change
  a rebuilt checkpoint, increasing incompatibility and rollback risk.
- **Remediation:** hashed/pinned architecture-specific resolution, image/SBOM manifests
  and immutable embedding identity. Preserve current model behavior and pnpm lock.
- **Verification:** clean native builds, SBOM/model comparison and regression/retrieval
  equivalence. Existing infrastructure digests are not a dependency lock for new builds.

### F22 — Automated release checks are stale

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P1.
- **Evidence:** `.github/workflows/frontend-tests.yml:3-13,23-44`;
  `.github/workflows/test.yml:3-7,29-38`; `frontend/package.json:5`;
  `frontend/Dockerfile:1-11`. npm lockfile is absent; pnpm lock is tracked.
- **Impact:** current branch lacks these push gates, frontend install expects wrong
  package manager, and curl checks need not fail on HTTP error. No hosted CI result
  or branch-protection state was inspected.
- **Remediation:** align branch/runtime/lockfile, enforce backend/frontend/type/build
  and HTTP-status gates; review workflow permissions/action pins.
- **Verification:** disposable-runner pipeline with deliberate harmless failures;
  release must stop on failed security/regression acceptance.

### F23 — Abrupt termination abandons in-process work despite persisted status

**Severity:** Medium. **Confidence:** Confirmed mechanism. **Priority:** P0.
- **Evidence:** `backend/app/api/api_v1/knowledge_base.py:430-479`;
  `backend/app/services/document_processor.py:354-420`;
  `backend/app/services/public_corpus.py:304-321`; `backend/app/main.py:28-39`.
- **Impact:** pending/processing records survive a process exit but their execution
  does not; partial SQL/object/vector states and blocked retries/lifecycle can remain.
- **Remediation:** durable claims/leases, bounded idempotent resume or safe failure,
  source retention and scoped reconciliation. Container restart is not job recovery.
- **Verification:** disposable interruption at each state boundary, restart, reconcile
  and verify no duplicate publication, lost source or unrelated cleanup.

### F24 — Recovery of all stores and key material is not demonstrated

**Severity:** High. **Confidence:** Requires Verification. **Priority:** P0.
- **Evidence:** `deploy/README.md:10-16,68-83`;
  `docker-compose.production.yml:86-102`; `docs/phase21-rag-evaluation.md:87-88`;
  `deploy/production.env.example:27-29`.
- **Impact:** a VM/disk/account failure can lose data or restore inconsistent SQL,
  objects/vectors; missing encryption key breaks personal AI settings. Backup absence
  is not asserted merely because no accepted drill is in the repo.
- **Remediation:** encrypted off-host coordinated snapshots/exports, independent key
  recovery, version manifests, retention and owner-approved RPO/RTO.
- **Verification:** actual isolated restore and hash/ID/permission/retrieval/history/key
  checks with a dated receipt and measured recovery time/data-loss window.

### F25 — Health and restart configuration do not prove application readiness

**Severity:** Medium. **Confidence:** Confirmed source gap. **Priority:** P1.
- **Evidence:** `docker-compose.production.yml:21-27,47-50,79`;
  `backend/app/main.py:47-52`; `frontend/Dockerfile:53`; `deploy/README.md:38-41`.
- **Impact:** healthy-looking backend with failing stores, startup races or unverified
  TLS renewal can interrupt service. Store image probes/host automation are unknown.
- **Remediation:** bounded readiness vs liveness, dependency supervision, cert renewal/
  reload alerts and controlled startup migration handling.
- **Verification:** staging dependency outage/recovery, host reboot and renewal drill;
  do not restart healthy jobs just because they are long-running.

### F26 — Log growth and host disk-pressure controls require proof

**Severity:** Medium. **Confidence:** Requires Verification. **Priority:** P1.
- **Evidence:** `docker-compose.production.yml:5-84` has no logging caps;
  `docker-compose.dev.yml:20-24` does; `backend/app/main.py:11-14` enables INFO.
- **Impact:** absent daemon limits, logs/images/temp/data fill storage and impair
  database and ingestion; no runtime disk/log pressure was measured here.
- **Remediation:** bounded logs, protected retention, disk/inode alerts, capacity
  reservations and ingestion backpressure, without destructive pruning.
- **Verification:** daemon settings/metrics/alert review and harmless rotation test.

### F27 — Oracle ARM64 release compatibility/capacity is unaccepted

**Severity:** Medium. **Confidence:** Requires Verification. **Priority:** P0 on ARM64.
- **Evidence:** `docs/cleanup-and-hosting-review-20261031.md:14-16,112-115`;
  `docker-compose.production.yml:39,55,61,71`; `backend/requirements.txt:10-12,27-30`;
  `frontend/pnpm-lock.yaml:1400-1416`.
- **Impact:** AMD64/native dependency mismatch, insufficient memory/disk or embedding
  changes may prevent reliable migration. ARM64 unsupported status is not confirmed.
- **Remediation:** inspect exact multiarch manifests/wheels, native tested CPU builds,
  measured combined capacity and preserved embedding/index compatibility.
- **Verification:** native ARM64 regression, ingestion/RAG/load and restore gate;
  verify actual Oracle entitlement/capacity separately before provisioning.

### F28 — Preflight can pass without usable personal-key encryption

**Severity:** Medium. **Confidence:** Confirmed. **Priority:** P1.
- **Evidence:** `deploy/preflight.py:26-45,74`;
  `deploy/production.env.example:27-29`; `backend/app/services/ai_settings.py:61-86`.
- **Impact:** missing/changed encryption secret breaks BYOK after release/restore;
  failure is closed, not a plaintext disclosure or silent shared-provider fallback.
- **Remediation:** secret-format validation, preserved independent key backup and a
  tested re-encryption/rotation procedure; never print the key.
- **Verification:** malformed/missing and restored synthetic ciphertext tests with
  masked outputs. Deployment must actually invoke the gate.

### F29 — Current image/package advisory and support status is unknown

**Severity:** Medium. **Confidence:** Requires Verification. **Priority:** P0 verification.
- **Evidence:** historical residual advisories in `docs/security-cleanup-20261009.md:59-91`;
  current declarations `frontend/package.json:42-55`, `backend/requirements.txt:1-30`;
  production image identities `docker-compose.production.yml:39,55,61,71`.
- **Impact:** a vulnerable reachable runtime/native/parser dependency may remain;
  old advisory counts do not prove current installed exploitability.
- **Remediation:** dated exact-image SBOM/OS/Python/npm scans and reachability/support
  review, patched native release artifacts and regression gates.
- **Verification:** authorized current advisory review against actual resolved images.
  No clean CVE scan, abandoned library or specific exploitable CVE is asserted offline.

## 7. AI/RAG security assessment

SQL permissions precede retrieval and provider input; candidates are rehydrated from
authorized SQL chunks (`backend/app/services/retrieval_scope.py:20-46,49-65,74-124`).
Private-only analysis does not silently expand into other users' papers. Public
related discovery is separately bounded. No normal-user initial private-to-LLM
bypass was found. F14 limits that statement for concurrent revocation/retry.

Structured output/citation IDs, evidence consistency and source checks reduce
fabrication and stale replay, but do not prove entailment. Evidence snippets are
untrusted data. No reachable LLM shell/SQL-writing/tool agent was identified; model
text cannot approve a request or grant itself access. Rendered AI HTML and remote
images are disabled in the reviewed UI (`frontend/src/components/chat/answer.tsx:219-232`;
`frontend/src/lib/answer-images.ts:1-4`). F13 remains a semantic integrity risk.

Provider credentials are not included in prompts. Personal OpenRouter/OpenAI settings
use fixed destinations, AES-GCM with owner/provider AAD, masked views and per-call
context reset (`backend/app/services/ai_settings.py:21-44,61-125,128-169`). BYOK errors
do not silently consume the shared key. App-selected alternate endpoints are an
operator trust boundary; arbitrary user-controlled provider URLs were not found.
Provider data retention and actual served model capabilities remain external policy
questions. Shared free routing is not a guaranteed allowance or uptime contract.

The requested usage dashboard remains **design only**, as explicitly selected in
Part 2. There is no per-user allowance ledger or accurate provider-reset/context
percentage to display. A future UI must report unknowns rather than invent balances;
it must follow server-side enforcement/accounting, not replace it.

## 8. Authentication and authorization assessment

Session mode hashes random tokens/CSRF values, checks active/verified users, requires
exact Origin and session-bound CSRF on mutations, and uses Secure HttpOnly host-only
session cookies. Current source: `backend/app/services/auth_sessions.py:26-72,88-139`.
Local HTTP is explicitly loopback-limited; production forces it off. Do not copy
the laptop tunnel normalization into the public release. Password hashing/policy
is `backend/app/core/security.py:18-34`; email/OTP throttles and revocation are in
`backend/app/services/email_otp.py:57-169`. OTP recovery is not per-login MFA.

Private papers/downloads/metadata/chats, publication requests and saved analysis are
owner-checked. Admin requires role and allowlist; superuser alone is not sufficient
(`backend/app/services/authorization.py:17-45,56-119`). A normal user has no reviewed
route to assign roles, approve requests or read arbitrary private collections.
Public cards require publication/consent, and review access is exact-document-scoped.
F07/F08 remain concurrency/policy issues. Department/supervisor-scoped administration
is future work, not a protection that exists today.

Release must retest cookies, proxy trust, CSRF, login/OTP/reset/logout/revocation and
two-user/admin boundaries with synthetic accounts. Do not equate a static control
trace or earlier successful local login with acceptance of a public TLS deployment.

## 9. Database and storage security

MySQL is an appropriate relational foundation for this workload; it is not inherently
a reason to replace the architecture. Capacity/security depend on configured grants,
indexes, transactions, connection lifetimes, version support and tested backups.
The audit found SQLAlchemy/bound predicates rather than a request-controlled raw-SQL
injection sink. Actual grants/TLS/backup encryption were not inspected. Runtime
startup performs Alembic (`backend/app/main.py:28-39`), so privilege and rollback
planning must account for schema writes, not just application queries.

Chroma stores real passages and must not be publicly reachable. Its metadata filters
are defense in depth; authorization belongs to SQL. MinIO downloads are proxied after
SQL permission checks and object-prefix validation; there is no application presigned
URL path whose expiry can be certified. Bucket policy/public access is unknown, not
assumed open. Internal plaintext transport is a single-host trust assumption; move
stores off-host only after TLS/auth redesign is separately reviewed.

SQL, MinIO and Chroma do not share a transaction. Preserve durable SQL chunk/object
references, completed-only readiness and fail-closed source reads; improve cleanup
and reconciliation rather than deleting unmatched data blindly. Archive is visibility
removal, not privacy erasure. F16–F18/F23/F24 define remaining obligations.

## 10. Docker and infrastructure security

Production uses no source bind mounts, privileged containers, host networking or
Docker socket mounts. Frontend runs non-root; backend does not declare USER.
No-new-privileges covers app/proxy services, but default capabilities, writable
filesystems and unbounded resources remain. Root/non-root status of external store
images requires inspection. No container escape is confirmed.

Nginx enforces HTTPS redirect, correct hostname, TLS 1.2/1.3 and security headers
(`deploy/nginx.conf.template:4-30`). Backend trusted proxy configuration and no-proxy-
headers command are explicit (`docker-compose.production.yml:13-17`). Only proxy
ports are published. Production startup, health, reboot, renewal and daemon settings
still require acceptance; restart policies do not recover application jobs.

## 11. Secrets and dependency risks

The Part 3 bounded scan checked 320 tracked text files for selected token/private-key
formats, without exposing matches/values; none matched. Real env/dumps/TLS/safety
snapshots are ignored, and service build contexts exclude env files
(`.gitignore:70-80`; `backend/.dockerignore:1-21`; `frontend/.dockerignore:1-10`).
This does not certify all history, image layers or arbitrary secret formats.

Avoid shared all-service env files for production runtime secrets (F11). Backups
containing encrypted personal keys still require separately protected decryption
material; host-root access defeats application-level encryption isolation. Legacy
application API keys need independent remediation (F01).

Frontend has a frozen pnpm lock and explicit Next/React versions. Python is largely
minimum-version-based; base images and apt resolution float. Historical advisories
are recorded with reachability qualifications, not silently dismissed. No online
advisory or supply-chain lookup was allowed here, so present-day CVE/support status
must be verified for exact release artifacts before launch (F21/F29).

## 12. Backup and reliability assessment

Persisted named volumes are necessary but insufficient. Recoverable scope includes
SQL users/roles/sessions/chunks/history/ciphertext, MinIO originals/staging/policies,
Chroma vectors/IDs, HF model identity/cache, pending work, secrets, schema revision
and release images. All three stores must describe the same application point.
`deploy/README.md:10-16,68-83` already requires this; the audit does not certify a drill.

Recommended initial operational objectives, subject to owner agreement: daily
coordinated encrypted off-host backup, target **RPO ≤24 hours**, **RTO ≤4 hours**,
7 daily plus 4 weekly retained sets if storage permits. These are targets, not
measured capabilities. Add more frequent coverage if losing a day of submissions is
unacceptable. Retention must match privacy policy. Prove an isolated restore before
real student ingestion and repeat after meaningful schema/store upgrades.

Do not copy a running internal database directory and label it a consistent backup.
Do not treat snapshots in the same VM/account as the only disaster copy. Preserve
encryption keys independently and never use volume pruning/reset scripts as recovery.

## 13. Oracle ARM64 deployment risks

Use the current single-VM design only after native ARM64 image, dependency and
combined-resource acceptance. The historical backend is AMD64 and 18.3 GB on disk
(`docs/cleanup-and-hosting-review-20261031.md:14-16,112-115`); that is not its RAM
requirement and was not remeasured. Native PyTorch/vector/image wheels and image
manifest variants must be checked. CPU-only dependencies may reduce size but cannot
be changed casually without embedding and RAG equivalence checks.

Model cache is persistent, but the factory falls back to downloading when missing.
Preload/reproduce the exact model and check non-root filesystem permissions. Count
one resident model per process/worker when sizing. MySQL, Chroma, parsing, frontend
and model memory compete; build-time peak may exceed runtime. Low concurrency and
disk headroom must be measured on the actual allocation.

No current Oracle price/free allowance/capacity/reclamation guarantee is asserted.
Check the account's real allocation and supported Ubuntu release separately. A free
VM does not guarantee SMTP, backup capacity, model quotas or HA. An unavailable ARM
manifest is a migration blocker, not justification to expose dev services or replace
the master plan under time pressure.

## 14. Recommended controls for 20–30 students

These are proposals; none were enabled by the audit.

| Control | Initial pilot target |
| --- | --- |
| Enrollment | Controlled cohort; enforce limits server-side rather than assuming only 30 people will find public registration. |
| AI admission | 1 active workflow/user, 2 outbound calls globally, queue ≤10; atomic reservations cover retries/stages and BYOK. |
| AI allowances | Set only after verifying provider quota. Part 2's provisional feature ceilings (10 chat, 2 summary, 1 comparison, 1 analysis actions/user/day) are maximums, not guaranteed shares of a potentially smaller global pool. |
| Deadlines | Measured bounded total deadline, initially 90s chat/summary and 180s multistage; include retries and cancellation policy. |
| Ingestion | Start at 20 MiB/file, ≤3 files/batch, 50 docs or 250 MiB/user, 1 active ingest/user, 1–2 globally; cap pages/text/chunks and queue. Tune on benign research papers before enforcing. |
| Isolation | Non-root parser/runtime, minimum capabilities/egress/secrets, measured CPU/RAM/temp limits with room for stores and HF model. |
| Storage | Capacity budget includes SQL excerpts/vectors/temp/images/backups, not just PDFs; alert near 70%, refuse new ingestion before 85%, keep operational reserve. |
| Data access | Only backend reaches stores; role/owner checks and source revocation remain mandatory; no public storage ports/tunnels. |
| Host/edge | Supported patched Ubuntu, cloud MFA, key-only restricted SSH/non-root admin, cloud + host/Docker network filtering including IPv6, renewable TLS and exact origin. |
| Recovery | Encrypted off-host coordinated backup, protected independent keys, accepted restore/reboot test and documented incident/credential-revocation owner. |
| Privacy | Consent and retention policy covers provider transmissions, photos, review history, snapshots/logs/backups; never log keys or real paper contents. |
| Release | Dated native-image SBOM/advisory review, regression/type/build plus synthetic authorization/RAG/restore gates; preserve rollback images and migration compatibility. |

## 15. Prioritized remediation roadmap

This is a security gate list within the existing master plan, **not new implementation
phases**. No fixes are authorized or applied by this audit report itself.

### P0 — Must resolve or verify before public exposure

1. **F01:** disable or securely migrate legacy application-key endpoints/credentials.
2. **F02/F03:** backend-enforced expensive-work/storage/concurrency limits and bounded
   off-event-loop previews, with measured container resource ceilings.
3. **F04/F15:** standalone secure production mode, independent secrets, HTTPS/CSRF,
   exact proxy trust and demonstrated exclusion of DB/Chroma/MinIO from public access.
4. **F05/F11:** least-privilege parser/runtime and service credentials. Equivalent
   containment would need explicit documented acceptance; none is granted here.
5. **F23/F24:** safe crash-state recovery and a coordinated encrypted off-host restore
   drill. Validate F16/F17 failure cleanup within that drill; do not silently drop references.
6. **F27/F29:** native architecture, current release vulnerability/support and benign
   capacity acceptance for the actual target. Remedy reachable unacceptable findings
   discovered by that scan; an unknown CVE status is not a proven exploitable CVE.
7. Close existing **Phase 21** quality acceptance and the **Phase 22** production gate.
   The last recorded evaluation was 12/13, with interpretation failing
   (`docs/cleanup-and-hosting-review-20261031.md:170-177`). This reliability gate is
   separate from security severity and was not rerun or marked complete here.

### P1 — Before expanding the pilot

Resolve withdrawal concurrency and consent/review/retention semantics (F07/F08/F18),
photo metadata (F12), retry revocation and injection evaluations (F13/F14), cleanup
and paging/pool bounds (F16/F17/F19/F20), reproducible artifacts and release CI
(F21/F22), readiness/log/disk controls (F25/F26), encryption preflight (F28), and
metadata log minimization (F10). Required backup/TLS/reboot controls must already
pass launch checks; broader automation and alerts can mature within this priority.

### P2 — Production hardening

Roll out compatible CSP (F06), reduce enrollment enumeration (F09), mature secret
rotation, dependency update cadence, secure admin access and operational alerting.
Keep regression/visual checks for existing UI behavior instead of unrelated refactors.

### P3 — Long-term improvement recommendations (not confirmed findings)

Evaluate high availability, multi-host authenticated TLS, infrastructure-as-code,
signed artifacts/provenance, longer-running adversarial evaluation and formal incident
drills as scale/data sensitivity grows. Department/supervisor roles remain planned
features requiring their own authorization design. Do not call optional HA or the
absence of a particular product a vulnerability in a 20–30-person single-VM pilot.

## 16. Final public deployment verdict

**MODERATE security posture; NOT READY for public deployment.** The permission and
session foundations justify continued incremental hardening, not a rewrite. The
unclosed availability, credential, containment and recovery gates prevent a responsible
public-readiness claim today. There are **0 confirmed Critical** and **5 confirmed
High** findings, with the conditional configuration qualifications stated above.

### Top 10 security risks

1. Shared AI/compute/storage exhaustion — F02.
2. Unbounded synchronous document preview — F03.
3. Recoverable long-lived legacy application credentials — F01.
4. Accidental insecure legacy/dev deployment — F04.
5. Raw vector-store exposure bypassing application permissions — F15.
6. Untrusted parser running with broad backend privilege — F05.
7. Backend access to infrastructure/root secrets — F11.
8. Interrupted jobs leaving unreconciled persistent state — F23.
9. Unproven consistent off-host recovery and key restoration — F24.
10. Unverified exact release vulnerabilities/ARM64 compatibility — F29/F27.

**Minimum launch change set:** address legacy keys; enforce resource/preview limits;
reduce parser/secret privilege; add safe interrupted-job recovery; use the existing
secure standalone production configuration; prepare supported native release images;
establish and prove protected backup/key/TLS/network operations; complete synthetic
authorization/RAG acceptance and the existing phase gates. Do not defer these to a
cosmetic usage dashboard or assume BYOK removes infrastructure abuse.

**Recommended secure pilot architecture:** one supported, measured Ubuntu ARM64 VM
if its native-image/capacity gate passes; existing Compose services behind the existing
Nginx HTTPS edge; only 80/443 public, restricted SSH; frontend on app network, backend
bridging to internal MySQL/Chroma/MinIO; non-root/least-privilege app and bounded parsing;
durable named stores/cache, separately protected runtime secrets, off-host encrypted
consistent backups, bounded logs and monitoring. Use one exact HTTPS origin and
current secure sessions. No direct public store endpoint, dev override or paid-provider
fallback. A single VM remains a known availability tradeoff, not HA.

All runtime/online verification remains future authorized work. The six findings
marked Requires Verification and five Likely findings must not be presented as
successful exploits. No code/configuration was fixed, no infrastructure introduced,
and no deployment was made by this final audit.

At the user's subsequent request, these two new reports are recorded in the
documentation-only annotated checkpoint `researchiq-security-audit-final-20261102`.
It does not close Phase 21/22, approve deployment or include the existing auth/tunnel
changes. Parts 1 and 2 remain separate local audit inputs, unchanged by this commit.
