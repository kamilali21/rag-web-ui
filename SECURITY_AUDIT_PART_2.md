# rAGRI search / ResearchIQ — Security Audit, Part 2

**Date:** 1 November 2026, Asia/Karachi  
**Role:** AI security and database security source review  
**Repository:** `C:\Users\tayya\Projects\ResearchIQ`  
**Baseline:** `995d5afef6b38fa3a336e252719c0e7ab0e0597a`, branch `master-integration`, plus the existing working-tree tunnel configuration and the separately requested local-login fix.  
**Scope:** AI/RAG, MySQL, Chroma, MinIO, ingestion and resource abuse. Part 3 is not included.

## Executive summary

The reviewed generation paths check SQL ownership/publication/readiness before
retrieving research text. Chroma metadata does not itself grant access: candidate
IDs are checked against fresh SQL permissions and content is reloaded from SQL.
No initial normal-user path was found that selects another user's private research
and sends it to an LLM without authorization. That conclusion has an important
limit: authorization can change while a provider call or retry is in progress;
some non-chat retries do not revalidate before resending their saved payload.

The largest practical pilot risks are shared-resource exhaustion, direct access
to an unauthenticated vector service if network isolation fails, and processing
untrusted documents without an isolated, bounded worker. Citation validation
checks references, not whether a claim is actually supported or whether the model
obeyed an instruction hidden in a paper.

This report records **9 findings: 2 High and 7 Medium**. Confidence is **5 Confirmed,
3 Likely and 1 Requires Verification**. No Critical exploit or cross-user breach
is claimed. Part 1 findings are carried forward by ID rather than counted again
unless this review adds a distinct mechanism or evidence.

### Audit boundary

The user's local-login repair was completed **before** this audit: an explicit
loopback-only secondary origin and separate local/HTTPS cookies were added;
48 authentication tests passed, 5 opt-in tests skipped, and the backend/Nginx were
restarted/reloaded. Credential-free local proxy checks accepted laptop/tunnel
origins and rejected an unrelated origin. Those were repair checks, not Part 2
security tests. No audit finding was automatically fixed.

After that boundary, only this report was created. No network requests, dependency
installations, migrations, exploit tests, load tests, database queries or storage
API calls were performed. The audit read application/configuration/test source and
`SECURITY_AUDIT_PART_1.md`. A local configuration read emitted only selected
non-secret model/provider identifiers and key-presence booleans. No keys were
printed or decrypted; SQL dumps, private papers and browser credentials were not
inspected. Current provider quotas, actual DB grants, bucket policies, runtime
image vulnerabilities and provider retention terms were not verified online.

All source paths below are relative to this repository. Line numbers refer to the
working tree at review time. **Confirmed** means the identified code/configuration
behavior exists, not that an exploit was run. **Likely** indicates a plausible
consequence requiring controlled reproduction. **Requires Verification** identifies
a policy or runtime fact that source alone cannot settle. Every verification step
below is a recommendation for later authorized staging work.

## AI/RAG security: traced data flow

### Authorization before model input

| Path | Checks and data actually sent |
| --- | --- |
| Shared retrieval | `backend/app/services/retrieval_scope.py:20-46` builds private-owner/non-system or published-system-corpus predicates and requires the latest processing task to be completed. `:49-65` rejects an entire invalid exact selection. `:74-104` resolves IDs before vector queries, releases the snapshot, then rechecks actor/permissions and joins chunk IDs back to SQL. `:110-124` returns SQL text/metadata, not vector-provided text. |
| Chat | `backend/app/api/api_v1/chat.py:98-125` replaces client history/scope with the owner's saved conversation and last 20 permitted messages. `backend/app/services/chat_service.py:74-80,92-125` checks chat/collections and scope. `:237-245` optionally sends authorized saved history to a question-rewrite model, then retrieves. `:278-288` rechecks current source permissions before each answer attempt and each emitted block. |
| Single-document summary | `backend/app/services/document_summary.py:149-164,265-268,327-359` checks exactly one ready, authorized document and its SQL chunks. At most 12 excerpts of 1,800 characters enter the summary prompt (`:51-52,347-363`). `:294-301,395-396` rechecks sources after generation. |
| Comparison | `backend/app/services/comparison.py:238-268` selects 2–5 authorized papers and retrieves each individually. `:269-285` checks document/KB/scope and caps each of eight excerpts at 1,400 characters. `:286-301` generates then rechecks sources/content. The provider helper's retry gap is P2-02. |
| Analysis / interpretation / candidate gaps | `backend/app/services/research_analysis.py:89-108,169-199` checks selected papers, retrieves up to six 1,200-character excerpts per paper and revalidates before profiling. `:111-146` permits related discovery only for public/both scope, with at most 20 public candidates and three related papers. `:206-238` checks the combined selection and evidence before/after synthesis. Private-only analysis does not expand into public or another user's private sources. |
| Saved results | `backend/app/services/comparison.py:178-202` requires run ownership, current source selection and matching document hashes. `backend/app/services/citations.py:86-106` hides saved chat envelopes whose sources are no longer permitted. This prevents application replay but is not physical deletion of stored snapshots (P2-07). |

The underlying ownership predicate is explicit:
`backend/app/services/authorization.py:56-83,86-106`. Admin status does not grant
blanket private-library retrieval. Internal helper methods are not substitutes for
route/service checks; they must not become new public endpoints without those checks.

### Threat coverage and limits

| Requested area | Source-grounded assessment |
| --- | --- |
| Direct/indirect injection, malicious PDFs | Prompts label evidence/history as untrusted and demand abstention; no prompt can make arbitrary text trustworthy. Chat interpolates evidence into its system-message template (P2-01). A malicious public paper must first pass admin publication; a private upload does not become globally retrievable. |
| Sensitive information / system prompts | Only permitted passages/history are intentionally sent. No API key is interpolated into the inspected prompts. The model may still repeat its instructions or permitted sensitive text. System prompts are not a security boundary or a secret vault. Provider access/retention is a separate trust boundary from user-to-user authorization. |
| Retrieval poisoning | Chroma text/metadata cannot manufacture a new authorized SQL chunk. A vector-store writer can still delete vectors or manipulate ranking among valid chunks, and an approved paper can contain scientifically false/adversarial text. SQL permissions do not establish research quality. |
| Output / streaming | `backend/app/services/citations.py:19-43,50-83` bounds structured output, checks known citations and rejects model-authored URLs/HTML/citation markers in chat claims. Full objects/blocks are validated before emission; there is no replay after partial output (`backend/app/services/chat_service.py:278-303`). JSON-encoded stream frames and `backend/app/core/http_privacy.py:6-25` avoid raw control-frame injection and add no-store headers without buffering. Disconnect cancellation and already-started requests still need runtime verification. |
| Insights rendering | Structured text/citation objects are returned rather than executable instructions. Existing frontend controls described in Part 1 remain applicable: `frontend/src/components/chat/answer.tsx:219-232` uses Markdown with raw HTML disabled; automatic external images are suppressed by `frontend/src/lib/answer-images.ts:1-4`. No XSS test was run here. |
| Excessive agency | No reachable model tool registry, shell executor, SQL-writing agent or `bind_tools`/AgentExecutor path was found in `backend/app`. LangChain is used for retrieval, prompts, parsing and model calls. Model-generated text cannot approve publications or grant permissions through these paths. No claim is made about every third-party library internal. |
| Model URLs / SSRF | Personal settings accept only OpenRouter/OpenAI and fixed HTTPS destinations (`backend/app/services/ai_settings.py:21-44,48-55`), not an arbitrary provider URL. Other destinations are trusted operator configuration (`backend/app/services/llm/llm_factory.py:25-65`). A model ID is not treated as a fetch URL. Parser external-resource behavior is unverified, not a confirmed SSRF. |
| Provider credentials | Owner-bound AES-GCM, random nonce, user/provider authenticated data, masked responses and context reset are present (`backend/app/services/ai_settings.py:61-125,128-169`). Personal failures do not fall back to the shared key. This protects normal-user isolation, not backend/root compromise with the encryption key. Part 1's plaintext legacy application keys are a separate credential type. |
| Embeddings | `backend/app/services/embedding/embedding_factory.py:13-21,30-52` supports cached local Hugging Face embeddings and a download fallback; alternate configured providers transmit text externally. Personal generation keys do not replace the application embedding configuration. A cold-start lock prevents duplicate local model loads, but is not a concurrency/resource limit for embedding work. |

### P2-01 — Prompt injection can produce apparently cited but unsupported claims

**Severity:** Medium. **Confidence:** Likely; no adversarial model call in this audit.

- **Evidence:** `backend/app/services/chat_service.py:162-191,201-207` places
  `Untrusted evidence: {context}` inside a system-message template. Although it
  explicitly rejects document instructions, the content still shares that prompt
  message. `backend/app/services/citations.py:31-43` validates structure/reference
  membership and prohibited syntax, not entailment. Summary/comparison validators
  similarly check supplied IDs (`backend/app/services/document_summary.py:382-392`;
  `backend/app/services/comparison.py:205-235`). Candidate-gap substring checks are
  stronger anchors but still not a truth test (`backend/app/services/candidate_gaps.py:50-77`).
- **Attack scenario:** an uploaded passage contains instructions to restate a false
  research conclusion while citing a real evidence ID. If the model complies in
  valid JSON, reference validation alone can accept it. Broad public poisoning
  requires publication/reviewer approval or storage compromise, not merely upload.
- **Impact:** research-integrity damage and deceptive apparent grounding; no
  demonstrated cross-user access, code execution or credential extraction.
- **Remediation:** keep trusted instructions separate from document data; preserve
  server-side permission and output validation; add adversarial semantic evaluations
  and explicit uncertainty/quotation requirements where appropriate. Do not replace
  these controls with a keyword blocklist or claim that changing roles solves injection.
- **Verification:** later use synthetic instruction-bearing PDFs across chat,
  summary, comparison and analysis; inspect claim support, abstention, citations and
  forbidden marker output with human review. Repeat across actually served models.

### P2-02 — Non-chat generation retries do not revalidate before resending evidence

**Severity:** Medium. **Confidence:** Likely; concurrent revocation not reproduced.

- **Evidence:** summary assembles authorized evidence then calls `_generate_draft`
  (`backend/app/services/document_summary.py:327-382`). Its two-attempt loop has
  no actor/source callback before `model.invoke` (`:216-260`). Comparison's shared
  helper also retries a captured payload without DB reauthorization
  (`backend/app/services/comparison.py:85-167`); it is used by analysis as well
  (`backend/app/services/research_analysis.py:197-199,223-232`). Final result checks
  occur afterward. Chat answer attempts do recheck; its optional history rewrite
  uses an earlier authorized history snapshot (`backend/app/services/chat_service.py:210-245`).
- **Attack scenario:** a paper is archived/deleted or an account disabled after
  evidence collection/first call but before a delayed retry. The already captured
  text can be resent to the provider even though the final result is rejected.
- **Impact:** a revocation-to-egress timing gap. This is not an initial bypass of
  another user's private selection; an in-flight disclosure cannot be recalled.
- **Remediation:** define revocation semantics; revalidate actor, exact selection and
  evidence immediately before every provider attempt/stage, including retries and
  history rewriting. Use bounded cancellation without holding DB locks over the network.
- **Verification:** later mock a throttled provider, revoke a synthetic source in a
  second transaction before retry, and assert no second outbound payload is sent.
  Separately verify already-started call behavior and final response suppression.

### P2-03 — Shared AI/ingestion resources have no per-user allowance or admission budget

**Severity:** High. **Confidence:** Confirmed in application code.

- **Evidence:** no-personal-key resolution returns `None`, selecting operator
  credentials (`backend/app/services/ai_settings.py:113-125`;
  `backend/app/services/llm/llm_factory.py:20-39`). Generation routes call services
  without quota reservation (`backend/app/api/api_v1/chat.py:90-129`;
  `backend/app/api/api_v1/insights.py:78-105`;
  `backend/app/api/api_v1/retrieval.py:42-45`). Upload/process routes admit owned
  work with per-request limits but no per-account storage/job budget
  (`backend/app/api/api_v1/knowledge_base.py:270-345,401-479`). Analysis UUID replay
  protection (`backend/app/services/research_analysis.py:175-190`) does not limit
  fresh UUIDs. Existing models hold result/history data, not usage accounting
  (`backend/app/models/analysis.py:7-52`, `backend/app/models/ai_settings.py:6-13`).
- **Attack scenario:** one verified account opens simultaneous chats, repeatedly
  submits new analyses, and uploads distinct names across collections. Requests
  individually pass authorization while consuming the shared provider and local
  parser/embedding/SQL/storage capacity.
- **Impact:** unavailable AI for other students, possible operator cost if a paid
  model is configured, CPU/RAM/disk exhaustion and long-lived background work.
  No-cost generation does not make compute/storage unbounded or free to operate.
- **Remediation:** atomic per-user plus global admission, storage ceilings and a
  bounded queue; provider-call/token accounting for retries and all stages; separate
  shared-key and personal-key budgets. Preserve hard limits even with BYOK.
- **Verification:** later test concurrent admission against a disposable database
  with provider spies; reject before outbound work, count retries, protect against
  duplicate reservations, and reconcile failures/disconnects. No load test was run.

This expands P1-02 with credential routing and accounting evidence, rather than
claiming a newly discovered unlimited per-request output length. Existing finite
limits are documented below.

## MySQL findings and controls

Reviewed queries use SQLAlchemy predicates/bind values. Examples include exact
ownership (`backend/app/services/authorization.py:56-83`), escaped search
(`backend/app/services/insights_catalog.py:29-49`), and bound public-discovery terms
(`backend/app/services/research_analysis.py:115-132`). No request-derived raw-SQL
injection sink was found. Imported `text` or fixed SQL expressions do not, by
themselves, establish SQL injection. No SQL payload was executed.

Saved runs have an owner/request UUID uniqueness constraint and source snapshots
(`backend/app/models/analysis.py:7-52`). This protects idempotency, not quotas or
cross-store atomicity. The withdrawal transaction issue remains **P1-07**; it is
not duplicated here. Source-based ownership is enforced by the app, not database
row-level policies or separate per-student SQL credentials.

Actual MySQL grants, TLS, backup encryption, binary-log retention and filesystem
permissions cannot be verified from source. Production config separates the root
and application password variables (`docker-compose.production.yml:38-51`) but
environment changes do not alter accounts in a restored volume; the deployment
instructions warn about this (`deploy/README.md:31-36`). Runtime code also invokes
Alembic at startup (`backend/app/main.py:28-39`), so migration/runtime privilege
separation must be assessed. Part 1 P1-11 covers the broad backend environment.
Do not assert that the runtime account is already least-privileged or that it can
log in remotely as root.

### P2-07 — Deleting/withdrawing source documents does not erase evidence snapshots

**Severity:** Medium. **Confidence:** Requires Verification of retention/privacy policy.

- **Evidence:** `backend/app/models/analysis.py:28-51` deliberately retains source
  identity and plaintext excerpts with `ON DELETE SET NULL` and no chunk FK.
  `backend/app/services/comparison.py:303-312` persists result JSON and excerpts.
  Chat stores base64-encoded evidence plus answer text, not encrypted content
  (`backend/app/services/citations.py:46-47`;
  `backend/app/models/chat.py:36-42`). Current-source checks hide unavailable results
  from normal API reads, but do not erase them. Recovery documentation identifies
  sensitive local SQL backups (`docs/windows-migration-manifest.md:17-29`).
- **Attack scenario:** a student assumes source deletion removes all private text;
  an operator, compromised DB reader or leaked old backup later exposes retained
  excerpts/conversation data. The workflow intentionally retains some audit history.
- **Impact:** a possible privacy/retention mismatch, not an established normal-user
  IDOR or proof of breached backups. Base64 and hashing are not content encryption.
- **Remediation:** explicitly distinguish archive, source deletion and data erasure;
  define retention for snapshots, chats, logs and backups; implement authorized
  erasure/expiry with documented audit exceptions. Encrypt/access-control backups
  and protect the personal-key encryption secret separately.
- **Verification:** agree the policy, then trace a synthetic marker through source
  deletion, history redaction, retention expiry and disposable restore. Verify backup
  access, off-host copies, coordinated MySQL/MinIO/Chroma restore and key recovery.

### P2-08 — Long provider calls can hold scarce SQL connections and read transactions

**Severity:** Medium. **Confidence:** Likely; pool contention not measured.

- **Evidence:** `backend/app/db/session.py:5-13` creates the engine without explicit
  pool sizing/recycle/pre-ping/statement-timeout configuration and closes request
  sessions in `finally`. Queries after `fresh_selection` open transactions; generation
  proceeds before the next rollback (`backend/app/services/comparison.py:171-175,266-293`).
  Summary follows the same pattern (`backend/app/services/document_summary.py:327-382`).
  Chat repeatedly rechecks SQL during a stream (`backend/app/services/citations.py:109-115`)
  and closes the session when its generator finishes (`backend/app/services/chat_service.py:332-333`).
- **Attack scenario:** several slow/throttled generation requests or streams occupy
  pooled connections while waiting on the provider. Ordinary library/auth queries
  then contend for capacity. Long read snapshots can also increase DB maintenance work.
- **Impact:** availability degradation at low concurrency; no assertion that the
  SQLAlchemy defaults are unlimited or that pool exhaustion was observed.
- **Remediation:** use short SQL transactions and immutable authorized snapshots,
  release connections before external calls, reauthorize on reacquisition, and size
  explicit connection/request budgets together. Add stale-connection recovery and
  bounded network/DB timeouts appropriate to the deployed driver.
- **Verification:** later simulate slow providers without external calls, inspect
  checked-out connections/transaction lifetimes and verify ordinary reads remain
  responsive. Exercise DB restart/reconnect and disconnect cancellation in staging.

## Chroma findings and controls

Collections are selected server-side as `kb_{kb_id}` from SQL-permitted KBs,
not accepted as arbitrary collection names from clients
(`backend/app/services/retrieval_scope.py:74-88`). Filters include both KB and
document IDs (`backend/app/services/vector_store/chroma.py:53-58`). Results are
rehydrated from SQL and reauthorized before returning. Chroma scores affect ranking,
not scientific confidence or access permissions.

New vector IDs use durable SQL chunk IDs; deletion also covers legacy metadata IDs
(`backend/app/services/vector_store/chroma.py:25-39`). Source deletion is guarded by
private ownership or corpus admin status and processing state
(`backend/app/services/private_library.py:81-134`;
`backend/app/services/public_corpus.py:392-434`). Failed private cleanup marks tasks
failed, excluding them from ready retrieval; public deletion hides first. This is
safer than deleting SQL references before external cleanup, but cannot make three
independent stores one atomic transaction.

### P2-04 — Chroma's raw text/vector API relies on network isolation, not user authorization

**Severity:** High. **Confidence:** Confirmed in supplied client/deployment configuration;
actual external reachability requires verification.

- **Evidence:** `backend/app/services/vector_store/chroma.py:15-24` constructs an
  HTTP client without credentials/TLS or per-user tenant configuration. `:25-32`
  stores document content as well as vectors. `docker-compose.production.yml:54-58`
  supplies an internal network but no authentication configuration. Local Compose
  publishes Chroma on loopback (`docker-compose.yml:55-62`); development Compose
  includes an unrestricted mapping (`docker-compose.dev.yml:99-106`).
- **Attack scenario:** a misplaced port-forward, accidental development deployment,
  or attacker reaching the data network accesses Chroma directly, bypassing FastAPI's
  SQL checks. Raw stored passages could be read; vectors/collections could be altered
  or deleted. Model text poisoning alone does not grant this network access.
- **Impact:** broad raw research disclosure or retrieval corruption/outage despite
  correct application permissions. No publicly reachable Chroma instance was proven.
- **Remediation:** expose only the web proxy, enforce data-network isolation and host
  firewall rules, prevent arbitrary forwarding of storage ports, and use supported
  service authentication/TLS or an authenticated internal proxy where needed.
  Preserve SQL rehydration even if Chroma authentication is added.
- **Verification:** later test denied access from an external host and untrusted
  container, confirm runtime network/auth configuration, and use synthetic collections
  to test forged metadata, deletion failure and cross-user retrieval rejection.

## MinIO findings and controls

Current downloads are server-proxied after document authorization; no presigned-URL
generation was found in `backend/app`. Thus no presigned expiry can be certified
or criticized. Private object paths must remain under their KB prefix and cannot
contain traversal/backslashes (`backend/app/services/private_library.py:60-64`);
public paths use the equivalent check (`backend/app/services/public_corpus.py:248-251`).
Upload names are validated; staging keys are random. Filename collisions are checked
under a collection lock (`backend/app/api/api_v1/knowledge_base.py:270-308`;
`backend/app/services/public_corpus.py:267-279`). A document ID or guessed key is not
enough to bypass the download route's SQL authorization.

`backend/app/core/minio.py:12-29` uses configured service credentials and internal
HTTP, and creates/checks the bucket without enforcing a bucket policy/encryption
policy. That does **not** prove the bucket is public. Actual policies, grants,
server-side encryption, versions/lifecycle and restored-object ACL state are unknown.
The production template uses the same configured credentials for MinIO root
(`docker-compose.production.yml:60-68`): **P1-11 remains open**. Local HTTP transport
is a single-host trust assumption; off-host storage requires authenticated TLS.

### P2-05 — Some failed staging/expiry paths lose references to remaining MinIO objects

**Severity:** Medium. **Confidence:** Confirmed control-flow defect; no storage failure induced.

- **Evidence:** private upload writes a random object before inserting/committing
  its upload row, without compensation for a subsequent SQL failure
  (`backend/app/api/api_v1/knowledge_base.py:307-335`). Expired-upload cleanup catches
  MinIO removal errors, then deletes the SQL upload row anyway (`:493-512`). Public
  staging attempts compensation but silently abandons a failed remove
  (`backend/app/services/public_corpus.py:279-301`). Ordinary document deletion has
  stronger reference-preservation controls; this finding concerns these specific paths.
- **Attack scenario:** repeated uploads during DB failure or cleanup during storage
  outage leave data without its normal SQL cleanup reference. A user can exacerbate
  accumulation with fresh uploads; no cross-user access is needed.
- **Impact:** orphaned private files, retained sensitive data and storage growth;
  inability to reliably reconcile deletion using only application records.
- **Remediation:** durable pending-cleanup/outbox records, retain references on
  failure, and scoped retry/reconciliation with an age/grace period. Never blindly
  delete objects merely because a transient SQL query finds no row.
- **Verification:** later inject synthetic put/commit/remove failures and assert
  references survive or compensation completes; rerun cleanup and prove only the
  fixture's orphan objects are removed. Test crash recovery, not just exceptions.

## File-upload and ingestion assessment

| Area | Controls / remaining uncertainty |
| --- | --- |
| Filename and MIME | `backend/app/services/upload_validation.py:10-49` allows PDF/DOCX/TXT/MD, rejects path/control characters and oversized names, checks extension/MIME compatibility, PDF magic, DOCX archive structure, and UTF-8/no-NUL text. Generic MIME is permitted only alongside those content checks. A PDF magic header is not malware validation. |
| Input size | Private uploads read at most a 100 MiB request budget plus one byte (`backend/app/api/api_v1/knowledge_base.py:279-283`). Public files are limited to 20 MiB (`backend/app/services/public_corpus.py:259-272`). These are not per-user storage or decoded-content limits. Multipart parsing/spooling itself needs upstream and framework limits. |
| DOCX / ZIP | `backend/app/services/document_processor.py:31-37` requires `word/document.xml`, at most 5,000 ZIP entries and at most 100 MiB declared uncompressed size. It does not extract entries using user-supplied filesystem paths in application code. Actual decoder CPU/memory, unusual archives and dependency behavior were not exercised. Do not label an XXE/ZIP traversal exploit confirmed merely because ZIP/XML is used. |
| Parser execution | PyPDFLoader, Docx2txtLoader, UnstructuredMarkdownLoader and TextLoader load whole documents before splitting (`backend/app/services/document_processor.py:203-235,286-313`). No worker sandbox, per-file wall-clock limit, PDF page ceiling or extracted-text/chunk ceiling appears here. P1-03/P1-05 remain deployment concerns. No specific parser CVE, external fetch or XML-entity exploit is established by this offline review. |
| Processing state | Private tasks reject duplicate upload IDs/already-submitted uploads (`backend/app/api/api_v1/knowledge_base.py:414-422`), but distinct uploads can create more work. A sequential loop in FastAPI background tasks is not a durable queue (`:462-479`). Public retry is admin-gated and uses retained sources (`backend/app/services/public_corpus.py:437-454`). |
| Cross-store consistency | Ingestion copies/removes objects, commits SQL document/chunks, writes vectors and only then marks completed (`backend/app/services/document_processor.py:325-420`). Partial states are expected on crash; ready retrieval excludes incomplete tasks. No scheduled crash reconciliation/worker lease is established by this path. Collection deletion can remain blocked on a stale processing state. |
| Unused helpers | Older `process_document` / `upload_document` helpers exist in `backend/app/services/document_processor.py:54-185`, but no routed caller was found in `backend/app`. Their weaker legacy behavior is not reported as a reachable HTTP exploit. Nothing was removed. |

### P2-06 — Download failures can leave local temporary files outside cleanup blocks

**Severity:** Medium. **Confidence:** Confirmed control flow; residue not inspected at runtime.

- **Evidence:** preview creates `NamedTemporaryFile(delete=False)` and downloads
  before entering the `try/finally` that unlinks it
  (`backend/app/services/document_processor.py:195-203,236-237`). Background processing
  calls `fget_object` before entering the parser's local-file cleanup block
  (`:271-286,423-451`). Its outer failure cleanup removes a MinIO source, not the
  local destination. A missing task also returns before the outer session-close
  `finally` (`:254-265,452-455`); a separate failure-path cleanup review is warranted.
- **Attack scenario:** interrupted/failed object downloads during repeated previews
  or processing leave allocated local files or partial-download artifacts. A user
  does not need a traversal filename; storage/network failure triggers the gap.
- **Impact:** temporary-disk accumulation and possible residual private bytes. The
  exact MinIO client's partial-file naming/cleanup behavior requires verification.
- **Remediation:** establish encompassing cleanup before allocation/download; use
  bounded temporary directories and best-effort scoped removal on every exit, plus
  crash-safe age-based janitorial cleanup. Avoid predictable shared temp paths.
- **Verification:** later simulate download failure before/after partial writes using
  harmless fixtures; assert no allocated file remains and internally created DB
  sessions close. Check both preview and background-worker paths.

## Resource-exhaustion assessment

| Abuse route | Current bound | Residual risk |
| --- | --- | --- |
| Chat generation | User question ≤4,000 characters, last 20 history messages supplied, answer cap 4,096 tokens; two service answer attempts, rewrite timeout 20s (`backend/app/api/api_v1/chat.py:101-111`; `backend/app/services/chat_service.py:140-145,237-243,278-303`). | No aggregate input-token budgeting against the selected model/context size, per-user daily allowance or application stream admission. Character/message bounds are not a measured context percentage. SDK retries differ for shared non-OpenRouter providers. |
| Summary | 12 × 1,800-character excerpts, 4,000 output tokens, two service attempts (`backend/app/services/document_summary.py:51-52,192-193,223-260`). | Repeated requests with new IDs consume shared capacity. A single UI action can make two provider calls. |
| Comparison | 2–5 documents, ≤11 criteria; 8 × 1,400 characters per paper; output formula ≤10,000, retry can raise it to 12,000 (`backend/app/schemas/comparison.py:15-26`; `backend/app/services/comparison.py:58-62,100-108,266-285`). | No per-user/global budget; retained large prompts and optional retry amplify cost/latency. |
| Analysis | 1–5 selected papers, ≤3 related papers, excerpts capped; profile plus synthesis/interpretation/gap stages each have a two-attempt helper (`backend/app/schemas/research_analysis.py:17-31`; `backend/app/services/research_analysis.py:26,193-238`). | An action can require four service-level generation attempts, plus any applicable SDK retries. Limiting UI actions alone does not accurately bound provider requests/tokens. |
| Retrieval/embedding | Candidate pool ≤100 and filter batches ≤500 IDs (`backend/app/services/retrieval_scope.py:79-92`). | Total authorized KB/document batches are not capped globally; each can incur embedding/query work. Cached HF model does not cap CPU concurrent use. |
| Upload / preview | Per-request byte limit, filename validation and DOCX expanded-size checks. | No lifetime/user quota; preview list/chunk parameters are unbounded (`backend/app/schemas/knowledge.py:89-92`) and synchronous parsing executes within async preview. P1-03 applies. |
| Jobs / streams | Framework pools and configured provider timeouts exist; no explicit application-wide budget. | Unique jobs/streams can contend for CPU, memory, threadpool, connections and provider quota. Nginx read timeout is not an end-to-end cancellation guarantee. |

### P2-09 — Chat reads load full histories before applying the 20-message model window

**Severity:** Medium. **Confidence:** Confirmed in source; resource impact not benchmarked.

- **Evidence:** `backend/app/api/api_v1/chat.py:26-31` validates/sorts every message
  in a conversation. Listing chats uses plain integer `skip`/`limit` without schema
  bounds and returns those full histories (`:65-79`). Creating one message first
  calls `readable_chat`, then slices the result to 20 (`:108-111`). The relationship
  is unpaginated and message content is LONGTEXT (`backend/app/models/chat.py:24,36-42`).
- **Attack scenario:** a user builds many long own conversations, then repeatedly
  loads the chat list or sends messages. Even greeting turns persist message pairs
  without needing provider success (`backend/app/services/chat_service.py:96-120`).
- **Impact:** growing SQL reads, Python allocations, response sizes and storage,
  affecting other users; no unauthorized content access is required.
- **Remediation:** bounded chat-list pagination returning summaries only, a separate
  owner-checked paged message endpoint, and a SQL-limited recent-history query before
  building model input. Add storage/turn/admission budgets without dropping ownership
  or stale-evidence filtering.
- **Verification:** later seed synthetic long histories and verify bounded SQL row
  counts, response size and latency; test invalid limits and compare authorization
  and source redaction with the existing behavior.

## Recommended pilot limits — proposals, not implemented guarantees

Use a controlled 20–30-person enrollment initially. The following are conservative
starting proposals, not measured host capacity or current OpenRouter entitlements.
Tune after benign load measurements and verified provider allowance. Multiple
accounts must not multiply the global budget indefinitely.

| Resource | Proposed starting policy |
| --- | --- |
| Active generation | 1 active AI workflow per user; 2 outbound generation calls globally; bounded queue of 10 with a clear retry response. Apply shared infrastructure limits to personal-key requests too. |
| Shared-provider calls | Global daily ceiling no higher than the provider's verified remaining allowance; provisional cap 50 outbound calls/day **only if the actual account permits it**. Until verified, display allowance as unknown. Reserve calls atomically for retry/stage work, not just UI clicks. |
| Per-feature ceilings | Pilot maximums: chat 10 actions/user/day, summaries 2, comparison 1, analysis 1 (including interpretation/gaps). These are ceilings, not promised capacity; the shared global pool can be exhausted earlier. Make that visible and consider fair reservations per student after measuring demand. |
| Burst control | At most 2 workflow starts/minute/user and 6/minute globally, further reduced to provider limits. Bound provider connection checks separately, e.g. 3/hour/user. Reopening an existing result consumes no generation allowance. |
| Input/output | Initial total input target ≤12,000 tokens/call, output reserve ≤4,096, or lower if the actual model window requires it. Truncate/select evidence and history server-side with explicit coverage notices; validate analysis quality before reducing its current output bounds. Never equate chars to exact tokens. |
| Workflow deadline | Chat/summary total deadline target 90s; multi-stage workflows 180s including retries. Cancel queued/unstarted work and reconcile ambiguous provider consumption after disconnect; do not promise an active provider call can be recalled. |
| Uploads/storage | 20 MiB/file, ≤3 files/request, 50 documents or 250 MiB per user including staged/failed originals; initial 10 GiB global document budget only if the host has sufficient reserve. Account separately for SQL excerpts, vectors, temp files and backups. |
| Parser/embedding | 1 active ingest per user, initially 1–2 workers globally; max 10 queued jobs/user and 30 global. Start with ≤200 PDF pages, 2 million extracted characters and 3,000 chunks/file, adjusting for real university papers. Reject/stop before full expansion where possible. |
| Isolation | Dedicated non-root parser worker, no unnecessary egress, explicit CPU/RAM/temp-disk limits; provisional 1 vCPU/1 GiB parser allocation needs measurement. Keep the HF model's resident memory in sizing. Prevent total limits from starving MySQL/Chroma. |
| Storage/cleanup | Alert at 70% disk, stop new ingestion before 85%, retain ≥20% operational reserve. Retry cleanup from durable references, handle stale jobs via leases, and retain failed fixtures only for a documented review period. No volume pruning. |
| Reads/streams | Chat-list pages 20–50 metadata items, message pages 50, SQL recent-history cap before serialization; one active stream/user within global AI capacity. Enforce small JSON request caps independently from multipart upload size. |
| Reset/accounting | Proposed app allowance reset: 00:00 UTC, displayed in the user's timezone (05:00 Asia/Karachi). Use server timestamps and atomic accounting. Provider windows may differ; never label an application reset as the provider's reset. |

Count provider attempts/tokens even if validation later rejects the result. Treat
provider-reported usage as authoritative where available, estimated reservations
as estimates, and interrupted/unknown consumption as unreconciled rather than zero.
Personal paid-key usage must never silently move onto the shared key or a paid model.

## P0 deployment blockers

P0 is launch priority, not a claim that each item has Critical severity.

1. **Shared resource protection:** resolve P2-03, plus P1-02/P1-03; bound preview,
   jobs, storage, provider calls and streaming before public self-registration.
2. **Internal-store and secret boundaries:** verify Chroma cannot be reached outside
   the intended backend network (P2-04); address P1-11 service-account privileges and
   P1-01 plaintext legacy application keys. Never forward storage ports as a tunnel fix.
3. **Untrusted parser containment:** address P1-05 and the ingestion limits above;
   perform an authorized supported-version/dependency review before internet launch.
4. **Recovery/privacy acceptance:** verify failure cleanup (P2-05/P2-06), durable
   recovery of interrupted jobs and coordinated encrypted backups. Agree source,
   snapshot and provider-data retention policies (P2-07) before real student papers.
5. **AI acceptance:** resolve the outstanding Phase 21 reliability gate and expand
   injection/grounding evaluation (P2-01). Make revocation/egress semantics explicit
   and close P2-02's retry gap for sensitive deployments.

These are verification/remediation recommendations, not a new integration roadmap.
The existing phased plan and checkpoints remain authoritative. Neither this report
nor the local tunnel repair closes Phase 21/22 or certifies public readiness.

## Runtime verification requirements

Do not execute these against real student data without a separate authorization:

- Two synthetic researchers plus admin: exact selections, public/private/both scope,
  forged vector metadata/text, disabled users and source revocation before each LLM
  stage/retry. Assert provider spies receive no unauthorized passages.
- Synthetic hostile PDFs/DOCX/Markdown: valid/malformed citation structures,
  role-spoofing passages, misleading evidence and semantic support; confirm no tools
  execute and no automatic remote-image fetch. Include benign non-English/long papers.
- Provider behavior: actual served model, structured-output support, input/output/
  reasoning token accounting, retry amplification, timeouts and cancellation. Obtain
  current account quotas/reset rules separately; no values were queried in this audit.
- MySQL: runtime grants, separate migration account, TLS if crossing hosts, prepared
  queries, pool metrics and stale connections. Controlled concurrent withdrawal
  testing remains P1-07. Verify actual engine/version support from current advisories
  in a later authorized online review rather than assuming a clean CVE state.
- Chroma: authentication/network denial, actual tenant/collection settings, SQL/vector
  ID agreement, partial add/delete and restart recovery. Never directly expose it.
- MinIO: bucket policy, root/service-account separation, encryption/version/lifecycle
  settings, unauthorized object access/overwrite denial and retained source cleanup.
- Ingestion: benign boundary-size PDFs/ZIPs, compressed/decoded size enforcement,
  XML/external-resource behavior, parser timeouts, temp cleanup and worker restart.
- Capacity: bounded concurrency at 20–30 users, application/DB/vector/temp/backups
  disk accounting, job lease recovery and backpressure. No exploit/load test was run here.
- Backups: access controls, key separation, retention and a coordinated disposable
  restore that proves SQL documents/chunks, MinIO files and Chroma agree. Old SQL dumps
  remain local; this report authorizes no deletion or restoration.

## Requested AI-usage dashboard — design only

The user selected **audit and dashboard design first**. No dashboard code, usage
table, API, allowance or billing behavior was implemented during this audit.

### What a new user gets today

- **Shared AI is available without entering a personal key**, provided the account
  can authenticate and has permitted ready/public sources. No-personal-key resolution
  uses the backend configuration (`backend/app/services/ai_settings.py:113-125`;
  `backend/app/services/llm/llm_factory.py:20-39`). The local `.env` currently selects
  `openrouter/free`, OpenAI-compatible generation, Hugging Face local embeddings and
  Chroma. A shared key is configured; its value was not printed. This is a file-state
  observation, not a live provider balance check.
- There is **no per-student free-trial duration or daily feature/token allowance**
  implemented. One user's consumption can exhaust the operator's shared provider
  allowance for everyone. A new login/account does not create fresh upstream quota.
- All four generation features use the same per-user provider selection when saved;
  otherwise they use the shared setting. A failing personal key does not silently
  fall back to the shared key. Removing the personal setting restores default routing
  (`backend/app/api/api_v1/ai_settings.py:45-52`). Indexing remains app-provided
  (`frontend/src/components/researcher/ai-provider-settings.tsx:50-76`).
- The app sends the configured model identifier; it does **not** implement its own
  model-rotation or quota-reset scheduler. With `openrouter/free`, selection of the
  serving model is delegated to the provider. The provider may choose different free
  models; this audit cannot promise rotation, availability, a particular context
  size, or that switching models bypasses an account-wide limit.
- A provider's rate window may recover with time, while exhausted credit or another
  account restriction may require action. The code handles a bounded Retry-After
  delay, not a quota refill (`backend/app/services/chat_service.py:36-57,296-303`).
  Exact remaining calls/tokens, reset times and current free-tier terms are unknown
  here because no external account/network query was permitted.

### Context window is not remaining credit

A context window is the maximum model input/output capacity of **one request**.
It is not a daily balance that refills at midnight. A conversation can accumulate
history, but this app selects recent messages for each new call; each call has its
own context budget. Daily requests, rate limits and paid credits are different
measurements. A context percentage needs the actual served model's capacity and
tokenized input plus output reserve; a free router may not reveal that model before
dispatch. The UI must say **Unavailable** rather than inventing a percentage.

### Visual proposal

Place one compact **AI usage** panel below the existing three dashboard cards and
above publication activity (`frontend/src/app/dashboard/page.tsx:85-103`). Reuse
emerald/lime/ivory theme variables and card spacing from
`frontend/src/app/globals.css:19-43,47-63,296-308`. Do not crowd the existing stats.

| Element | Display and data rule |
| --- | --- |
| Panel header | `AI usage` with a small `Shared provider` / `Your provider` badge and Profile settings link. No key value or global account balance exposed to other users. |
| Four horizontal bars | Research Assistant, Summary, Comparison, Analysis. Once real accounting exists: `used / your daily allowance`, reserved work and remaining actions. Until then: `Usage not tracked` / `Allowance not configured`, not a fake full bar. |
| Context ring | One compact `Last request context` ring next to the bars on desktop. Label feature, actual model, input tokens and reserved output. Show a neutral ring with `Model capacity unavailable` when capacity/tokenization is unknown; never label this as daily remaining tokens. |
| Footer | App allowance reset timestamp/countdown only when a server-enforced window exists. Separately show provider throttle/retry time only if known; otherwise `Provider-managed limits`. |
| Mobile | Bars stacked at full width; ring moves below, no horizontal overflow. Use tabular numerals, readable labels, and dark-theme contrast. |
| Motion/accessibility | Brief 200–300 ms progress transitions on real data changes, no continuous decorative activity. Respect reduced motion; include text equivalents/accessible meter labels, keyboard access and polite status updates. Avoid announcing every countdown second. |

### Data required before implementation

Introduce a reviewed, owner-scoped usage ledger through the normal migration/test
gates, not browser-only counters. Each workflow needs a stable idempotency ID and
per-attempt records for feature, provider mode, actual model if returned, status,
input/output tokens, whether measured/estimated, reservations, timestamps and
reconciliation state. Exclude API keys, prompts and paper excerpts from that ledger.
Provider retries and analysis sub-stages must count; reopening history must not.

Expose only the signed-in user's usage and application-enforced allowance/reset.
Never accept a browser-supplied user ID as authority, and never imply that this
ledger equals the provider's full account usage (the key may be used elsewhere).
Record shared-pool state without leaking other students' activity. Apply quotas
atomically on the backend before making calls, including BYOK compute protection.

Acceptance should cover simultaneous reservations, retries, refunds versus unknown
provider consumption, idempotent replay, daily boundaries/timezones, denied cross-user
reads, no key disclosure, all four workflows, accurate unknown states, dark mode,
mobile layout and reduced motion. This is a design proposal only; the recommended
limits above have not been enabled.

**End of Part 2. No Part 3 work, automatic audit fixes, dashboard implementation,
commit, push or deployment was performed during the audit.**
