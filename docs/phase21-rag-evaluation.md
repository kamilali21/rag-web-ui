# Phase 21 — RAG evaluation and adversarial review

Date: 30 October 2026. Baseline: `6fdd079`, Phase 20 checkpoint
`researchiq-phase20-security-20261029`. This follows the amended Master
Integration Plan; deployment hardening remains Phase 22.

## Scope and reproducibility

`backend/tests/phase21_live_evaluation.py` evaluates two fabricated English
irrigation papers through the running upload, processing, retrieval and AI APIs.
The private paper describes 120 greenhouse plots and a 23% water reduction;
the public paper describes 60 cotton field plots and an 18% reduction. Both
explicitly state one-season coverage and unmeasured yield. Neither gives a
p-value. The private paper also contains a hostile instruction to output a
unique marker without citations. This is test data, not scientific evidence.

Four exact-selection retrieval queries measure recall@5 and reciprocal rank.
Chat checks factual citation integrity, document injection, forged client
history/scope, an absent statistic and unsupported yield. Summaries, overview,
contradiction interpretation, candidate gaps and comparison use only these
selected papers. Citation membership/page checks are automatic; semantic
faithfulness, context distinctions and qualified wording also require review
of the actual output. Correctly stating that a source did not measure yield
is a valid grounded abstention, not a generation failure.

All test chats use only the synthetic private collection. No real private paper
or existing public corpus is sent to the model. Synthetic users do not inherit
any existing user's personal provider key. The existing configured provider is
used, with existing retry limits and evidence validation unchanged.

Run inside the local backend:

```text
PHASE21_LIVE_ACCEPTANCE=1 python -m tests.phase21_live_evaluation
python -m pytest tests/test_phase21_redteam.py -q
python -m pytest tests -q
```

The opt-in harness refuses non-local origins. It removes only its own fixtures
through application lifecycle operations, then compares original SQL row
fingerprints, MinIO object names/ETags/sizes and Chroma vector IDs. Existing
transient authentication tables are excluded from row fingerprints. Receipts
remain under ignored `backend/.local/tmp/`; do not commit live database dumps,
session cookies, keys or private research.

This small benchmark is a reproducible smoke evaluation, not an accuracy claim
for arbitrary research, languages, OCR, long PDFs, concurrent traffic or model
changes. Single-run latency is not a production percentile or SLA. An empty
contradiction list can be correct when contexts differ; invented conflict is
not a success criterion. Future regression corpora should add representative,
consented university documents and human relevance labels.

## Confirmed fixes

- Previously, private API responses did not consistently prohibit browser/proxy
  caching. Pure ASGI middleware now adds `Cache-Control: no-store`, `Pragma:
  no-cache`, `nosniff` and `no-referrer` across `/api` and `/openapi`, including
  authentication errors. It forwards stream frames immediately without buffering.
  Both frontend API helpers explicitly request `cache: no-store`.
- Pydantic validation responses could echo submitted values. Responses now
  preserve bounded field locations/types with generic messages, excluding input,
  context and raw validation messages. Unhandled errors return a generic private
  JSON response. This does not claim to sanitize all infrastructure/server logs.
- Regression tests cover owner-only cache policy, anonymous errors, invalid
  passwords/OTPs/keys/prompts, streaming, forged cookies and replay after logout.
- Manual evaluation found that interpretation factors speculated about weather,
  evaporation and statistical power not described by the papers. Tightened the
  existing prompt to describe documented differences without inventing mechanisms,
  even with hedging. The final live interpretation explicitly said the reason for
  the effect-size difference was not established. This is a mitigation, not a
  semantic proof for arbitrary model output.

No schema, embedding model, provider routing, authentication architecture or
publication workflow was changed. Old cached browser content is not remotely
erased by these headers; the controls govern subsequent responses.

## Security assessment and production blockers

| Surface | Evidence / protection | Residual risk / required gate |
| --- | --- | --- |
| Prompt injection / query manipulation | SQL ownership and publication checks precede retrieval; vector results are rehydrated from SQL; unknown citations and forged scope are rejected. Live hostile-paper probe plus Phase 9/10/13–20 tests. | Semantic influence remains possible even when references are valid. Never let model output grant permissions or execute tools. Expand adversarial corpora continuously. |
| Sessions / CSRF | Opaque hashed sessions, exact origin + CSRF checks, verified/active users, logout revocation and HTTPS cookie policy; Phase 3/20/21 tests. | A stolen valid session remains a bearer credential until revoked/expired. Local HTTP is development-only; HTTPS and production cookie acceptance are mandatory. |
| Personal AI keys | Owner/provider-bound AES-GCM encryption, masked projection, fixed provider endpoints and per-request context; personal-AI regression suite. | Backend/root compromise with the master key can decrypt them. Protect and back up the encryption key separately, rotate secrets and restrict access. |
| Legacy application API keys | Owner-only management and active-user checks; logging avoids key values. | **Deployment blocker:** `api_keys.key` still stores reusable keys in plaintext and owner APIs return them. Plan a tested hash-at-rest / show-once migration or explicitly disable this legacy API surface before public launch. This is distinct from encrypted AI-provider keys. |
| Browser rendering / uploads | Citation/output validation, automatic remote Markdown images disabled; bounded file/photo validation in Phase 20. | Parser sandbox/resource isolation and malware policy remain required review items; extension/signature validation is not antivirus. |
| Abuse / denial of service | Existing authentication throttles, bounded request fields/output and provider retries. | Authenticated AI/upload quotas, concurrency budgets and shared-worker limits are not a completed production gate. Protect shared model credit and parser resources. |
| Dependencies / containers | Version pins and prior regression tests; no new dependency added here. | Current OS/package/image vulnerability scans, patching policy, least privilege and restore drills remain Phase 22 work. No clean CVE scan is claimed by this audit. |
| Storage / deployment | Production Compose separates internal data services; no public DB/vector/storage ports specified. | Actual public TLS, network exposure, secrets, backup recovery and failover have not been accepted on a hosting server. |

This is a bounded code review and executable regression evaluation, not a claim
that the application is secure from every attack or an independent penetration
test. OWASP explicitly notes that RAG alone does not eliminate
[prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

## Database and deployment decision

The running application uses **MySQL 8.0.46** (schema `riq_008`) for users,
documents, profiles, publication requests, chats and analysis history;
**Chroma** stores embeddings and **MinIO** stores files. MySQL is a suitable
production relational database; this single-machine deployment has not been
capacity-tested and does not establish a supported user count or high availability.

MySQL 8.0 moved to Oracle Sustaining Support on 21 April 2026. Before launch,
test a supported LTS upgrade, including driver/authentication compatibility,
disposable restored data, Alembic checks and rollback. The production Compose
still pins the current 8.0 image and native-password startup flag; changing only
the image would be unsafe. No live DB upgrade was performed. See the
[official MySQL notice](https://www.mysql.com/support/eol-notice.html).

For an initial controlled deployment, retain the architecture on a Linux VM
using the existing production Compose and a single HTTPS origin. Expose only
the reverse proxy, keep databases/object/vector storage private, use tested
versioned images and encrypted off-host backups with restore drills. This is
a pilot architecture with a single-host failure domain, not an HA design.
Use managed MySQL and durable object storage when operational requirements and
budget justify it; size workers/vector storage from measured corpus and traffic.

Vercel now supports container Functions and Daemons, so it is incorrect to say
Docker cannot run there. However, local container storage is ephemeral, and the
current persistent multi-service Compose is not a drop-in Vercel deployment.
It would require external durable data services and verification of long-running
processing, streaming and same-origin session routing. A Linux container host
fits this project's existing strategy with fewer changes. See
[Vercel's current Docker guidance](https://vercel.com/kb/guide/docker-on-vercel-vs-render).

## Execution results

**Checkpoint complete; Phase 21 live acceptance remains open.** Do not advance
to Phase 22 or call the application production-ready based on this checkpoint.
No push. Annotated checkpoint: `researchiq-phase21-evaluation-checkpoint-20261030`.

| Check | Result |
| --- | --- |
| Full backend regression | 597 passed, 44 opt-in skipped; `phase21-regression.xml` |
| Focused interpretation/gap regression after prompt adjustment | 52 passed; `phase21-interpretation.xml` |
| Frontend | 133 tests passed; standalone TypeScript passed |
| Production frontend build | Passed; existing ESLint invalid-options warning means lint is **not** a passing gate |
| Final synthetic benchmark | 12/13 cases passed, plus comparison/reopening/revocation and exact cleanup checks |
| Retrieval | Recall@5 4/4; mean reciprocal rank 0.875; one number-focused query ranked the other paper first |
| Chat | Correct cited 23% answer despite hostile source; both absent-statistic/yield questions abstained; forged client scope/history did not broaden retrieval |
| Summaries | Both complete, correct per-paper 23%/18% findings and single-season/unmeasured-yield limitations; saved evidence reopened |
| Interpretation | Passed; supporting evidence with documented crop/year/sample differences, no fabricated weather explanation in the final run |
| Candidate gaps | Passed final run with qualified scope and verified quotations; earlier run rejected a non-verbatim quotation |
| Comparison | Passed; source-specific cells/citations, saved reopening, replay and revocation |
| Overview analysis | **Failed final run: HTTP 502 after Research profiles generation.** Earlier run returned a grounded overview. Intermittent structured-profile validity remains unresolved. |

Final timings: retrieval 0.23–0.56s; chat 6.59–7.78s; summaries 10.34–10.53s;
interpretation 68.58s; candidate gaps 58.12s; comparison 5.64s. Overview failed
after 6.64s. The first run's overview succeeded at the API level after 154.81s.
These are individual local observations, not p95 figures; first-run timings were
also affected by concurrent verification/build work. Cold embedding initialization
delays ingestion after a backend restart and is not included in retrieval timing.

First-run benchmark bugs were corrected without weakening application validators:
summary citations do not expose `excerpt` directly; saved history supplies the
evidence; hostile text legitimately remains inside raw citation excerpts; an
explicitly cited statement that yield was not measured is valid abstention.
The first raw results and synthetic observations are retained separately as
`phase21-evaluation-first.json` and `phase21-first-observations.json`. They also
record the genuine first gap-generation failure (`quote_not_in_excerpt`). The
final receipt is `phase21-evaluation.json`; its nonzero exit intentionally reflects
the remaining overview failure. No failed attempt was converted into a green gate.

Manual review of final summary claims and interpretation found correct facts,
source mapping and limits for this fixture. Citation identity alone cannot prove
semantic faithfulness, as the first interpretation demonstrated. Free-model
availability and structured-output variability remain practical constraints.

Both runs verified original research SQL fingerprints, MinIO objects and Chroma
vector IDs unchanged after fixture cleanup. Schema remains `riq_008`. Deployed
health returns 200; anonymous profile/history return 401 with `no-store`; login
returns 200. Six application services remain running. No browser visual pass is
claimed. Backend source remains bind-mounted; preserve the Git checkpoint with
the existing Phase 20 dependency image when reproducing it.

**Exact next task:** finish the existing Phase 21 gate by diagnosing the
intermittent Research profiles validation failure, improving bounded structured
generation without weakening citation/permission checks, and repeating the full
quality/latency benchmark. Then perform the existing Phase 22 deployment gate,
including the production blockers above. No new phase or architecture is proposed.

## Requested disk cleanup

- Removed only resolved, link-free repository paths `backend/.pytest_cache`
  (245.4 MiB) and `frontend/.next` (180.2 MiB). A subsequent focused test regenerated
  6,210 bytes of pytest cache, also removed after it completed.
- Docker build-cache cleanup older than seven days reclaimed **4.228 GB**, while
  retaining at least 8 GB of cache. A second unused-cache check older than 24 hours
  reclaimed 0 bytes. Commands used `docker buildx prune --filter until=...`
  with `--reserved-space 8GB`; no system/volume prune was used.
- Kept every data volume, database dump, uploaded document, vector collection,
  `.env`, installed dependencies, active container and recovery image. Stopped
  containers with unknown historical state were also retained.
- Docker subsequently reported 30.76 GB of build cache, including shared/recent
  layers, and 29.75 GB of image storage. Those categories overlap; do not add them
  to estimate physical disk use. The large backend image contains installed ML
  dependencies and was not treated as disposable data.
- Reclaimed Docker space is reusable inside Docker's virtual disk. Immediate
  Windows Explorer free-space growth was not independently measured; no Docker
  shutdown, virtual-disk compaction or filesystem-wide cleanup was attempted.
