# rAGRI search / ResearchIQ — Security Audit, Part 3

**Review started:** 1 November 2026; **completed:** 2 November 2026 (Asia/Karachi)
**Role:** Principal DevSecOps Engineer / Production Security Architect
**Repository:** `C:\Users\tayya\Projects\ResearchIQ`
**Branch / HEAD:** `master-integration` / `995d5afef6b38fa3a336e252719c0e7ab0e0597a`
**Scope:** deployment, secrets, dependencies, persistence, recovery and Oracle ARM64 readiness.

## Executive summary

The standalone production Compose is a useful starting point: only Nginx publishes
ports, the three data services share an internal network, HTTPS/session mode is
forced, infrastructure images use digests, and explicitly prepared external volumes
prevent silently creating empty production stores. These are source controls, not
evidence of a secured deployed host.

Public launch is **NOT READY**. Parts 1 and 2 identified missing admission budgets,
unsafe legacy application-key storage and insufficient parser containment. This
review adds deployment/recovery gaps: non-reproducible backend builds, stale CI,
non-durable background work, incomplete readiness checks and unverified coordinated
backup recovery. ARM64 compatibility and current dependency exposure are unverified.

Part 3 records **10 findings: 2 High, 8 Medium; 6 Confirmed, 4 Requires Verification**.
P3-01 expands the earlier unsafe-deployment finding rather than adding a separate
vulnerability to the consolidated count. Severity describes potential impact;
confidence describes evidence. A confirmed unsafe development configuration does
not mean that configuration is deployed publicly. No Critical exploit was confirmed.

## Method and limits

Read Parts 1 and 2, all three Compose files, Dockerfiles, proxy configurations,
production examples/preflight/runbook, dependency manifests/lockfile, Git tracking
metadata, workflows and relevant startup, provider, ingestion and persistence code.
All references below are repository-relative and line-numbered against the current
working tree. Existing uncommitted authentication/tunnel changes were inspected,
not edited; Part 1's original authentication line numbers predate those changes.

Only this report and `RAGRISEARCH_SECURITY_AUDIT_FINAL.md` were created. No application
or configuration edits, installs, migrations, builds, deployment, Docker runtime
queries, database access, external requests, exploit/load tests or cleanup occurred.
No credentials, `.env` values, private papers, SQL dump contents or credential-bearing
Docker safety snapshots were disclosed. Recommendations and verification procedures
below are future work, not completed checks.

A bounded offline scan of **320 tracked text files** (files at most 2 MB, excluding
binary content) found no matches for the checked private-key block, AWS access-ID,
provider-token and GitHub-token formats. It does not detect arbitrary passwords,
every secret format, large/binary files, deleted secrets or every historic blob.
A filename-only Git history query for the selected real env/dump/key/snapshot paths
returned no entries. This is not a complete historical secret scan. Default/example
credentials do exist in development configuration; their values are intentionally
omitted here. Actual secret strength/rotation and file ACLs were not tested.

No current offline advisory database or installed release SBOM was established.
The historical dependency audit is treated as dated evidence, not a current scan.
Oracle pricing, free allowances, available capacity, image manifests and Ubuntu
support status were not queried because external access was prohibited.

## A. Docker and reverse-proxy inventory

| Component | Source evidence | Assessment |
| --- | --- | --- |
| Production backend | `docker-compose.production.yml:5-30`; `backend/Dockerfile:1-35` | Explicit image supplied by operator, no source bind mount, two networks, restart unless-stopped, no-new-privileges. Dockerfile has no non-root USER; no Compose override, resource ceilings, cap-drop or read-only-root policy. P1-05/P1-02 remain open. |
| Production frontend | `frontend/Dockerfile:1-56`; `docker-compose.production.yml:32-36` | Multistage standalone runner, non-root nextjs user, image healthcheck, no-new-privileges, no published port. Build stages run as root; that does not mean the runner does. |
| MySQL | `docker-compose.production.yml:38-52` | Digest, persistent volume, internal network, separate root/application variables, restart policy, mysqladmin ping. Ping does not verify application grants or schema readiness. Native-password compatibility is explicitly selected; version support/current advisories require review. |
| Chroma | `docker-compose.production.yml:54-58`; `backend/app/services/vector_store/chroma.py:15-32` | Digest and internal persistent service. No service auth/TLS supplied by this client/config. Raw passages are stored; isolate it from all untrusted callers. P2-04. |
| MinIO | `docker-compose.production.yml:60-68`; `backend/app/core/minio.py:12-29` | Digest, internal network, persistent volume; app credentials are also root credentials. API uses internal HTTP. Actual bucket policy/encryption is unknown, not proven public. P1-11. |
| Nginx | `docker-compose.production.yml:70-84`; `deploy/nginx.conf.template:4-36` | Only host ports 80/443, fixed-domain HTTP redirect, wrong HTTPS Host rejection, TLS 1.2/1.3, HSTS/nosniff/frame/referrer headers, read-only certificate/config mounts. Forwarded client headers are overwritten; backend trusts only configured proxy peer. |
| Networks | `docker-compose.production.yml:28,34,51,57,67,80-82,103-110` | Frontend/proxy on app network; stores on internal data network; backend bridges both. Frontend cannot directly join the data network through this config. Host/Docker administrators and compromised backend remain privileged boundaries. |
| Data/cache | `docker-compose.production.yml:86-102` | External named MySQL/Chroma/MinIO/HF-cache/upload volumes. External means explicit lifecycle ownership, not backup, encryption or proof of correct contents. |
| Local profile | `docker-compose.yml:8-11,25-27,38-59,79-98` | Source mounts, floating images, loopback storage mappings, HTTP edge. Not a production configuration. Root/app DB password variables are shared in this file. |
| Dev profile | `docker-compose.dev.yml:26-42,60-75,84-119`; `nginx.dev.conf:25-33,104-110` | Reload/debug tooling, public-interface data/API/frontend ports, default credentials and a MinIO proxy route. Must never be used/merged for internet deployment. |

No `privileged: true`, host networking, Docker socket mount or explicit capability
addition was found in the reviewed Compose files. Production does not drop default
capabilities; image runtime users for DB/Chroma/MinIO/Nginx cannot be inferred safely
from a digest string alone. Their USER/entrypoint privilege transitions need image
inspection. Container root is not, by itself, proof of host escape.

Production has restart policies for all six services. Local Compose lacks policies
for several services; development policies differ. Do not extrapolate laptop reboot
behavior to production. A restart policy restarts exited processes, not necessarily
unhealthy processes or abandoned application jobs. Docker daemon startup is a host
configuration outside this repository.

The production proxy has no application-page CSP (P1-06) or per-route admission
limits (P1-02), and permits up to 100 MB bodies globally. A proxy read timeout is
not a whole-workflow deadline. There is no production wildcard CORS header; the
wildcard occurs in the development proxy and does not itself permit credentialed
cross-origin reads. The narrow local tunnel Origin rewrite in `nginx.conf:9-17`
is absent from the production template and must stay development-only.

## B. Detailed findings

### P3-01 — Development/legacy deployment profiles remain unsafe for public use

**Severity:** High. **Confidence:** Confirmed, conditional on selecting the wrong profile.
**Consolidation:** F04 with P1-04; Chroma-specific impact is F15/P2-04.

- **Evidence:** `docker-compose.dev.yml:30-31,69-75,84-119` publishes API, frontend,
  DB, vector and object services and includes default storage/DB credentials.
  `nginx.dev.conf:104-110` proxies MinIO. `docker-compose.yml:38-44,93-98` uses shared
  DB password variables and HTTP. `backend/app/core/config.py:32-41` defaults to
  legacy auth with a built-in signing fallback. Production forces safer settings
  (`docker-compose.production.yml:13-17`); its runbook forbids merging (`deploy/README.md:3-6`).
- **Scenario / impact:** a deployment following the generic dev command or merging
  profiles exposes stores/default credentials or enables weaker authentication.
  This is a conditional disclosure/tampering risk, not evidence of current public exposure.
- **Remediation:** enforce a production configuration gate and explicit standalone
  deployment command; fail closed on insecure auth/default secrets; prohibit data
  port forwarding and dev overrides. Keep local development separate.
- **Verification:** later inspect resolved production settings without printing
  secrets; verify external denial of every non-web service and test insecure-profile
  rejection on disposable infrastructure. Do not deploy dev merely to demonstrate it.

### P3-02 — Backend rebuilds and embedding artifacts are not reproducibly pinned

**Severity:** Medium. **Confidence:** Confirmed. **Consolidation:** F21.

- **Evidence:** `backend/requirements.txt:1-30` mostly uses minimum or unconstrained
  versions; no backend lock/constraints file is tracked. `backend/Dockerfile:1-18`
  uses a mutable Python base and unpinned apt/pip resolution in a single runtime
  stage. `frontend/Dockerfile:1-22` uses a mutable Node base, although pnpm itself
  is pinned and installs a frozen lockfile. `backend/app/services/embedding/embedding_factory.py:13-21`
  identifies the model by name, not an immutable revision, and downloads if cache is
  missing. Infrastructure digests are a positive control, not a lock for future app builds.
- **Scenario / impact:** the same source checkpoint rebuilt later resolves different
  packages/model artifacts, breaks parser/provider or client/server compatibility,
  or prevents exact rollback. No malicious package/model was demonstrated.
- **Remediation:** record tested, hashed Python resolutions and base/OS/image
  identities per target architecture; retain SBOMs and immutable release images;
  record embedding revision/files and compatibility parameters. Preserve frozen
  pnpm installs. Do not remove providers or change embedding models as a cleanup.
- **Verification:** two clean offline-capable builds from the recorded dependency
  set; compare SBOMs, model hashes/dimensions and semantic retrieval fixtures. Verify
  application behavior rather than assuming equal vector dimensions mean equivalence.

### P3-03 — Repository CI does not enforce the current release gates

**Severity:** Medium. **Confidence:** Confirmed configuration mismatch. **Consolidation:** F22.

- **Evidence:** `.github/workflows/frontend-tests.yml:23-44` targets Node 18/20 and
  `npm ci` with `frontend/package-lock.json`; that file is absent. The tracked lock
  is `frontend/pnpm-lock.yaml`, and `frontend/package.json:5` specifies pnpm;
  `frontend/Dockerfile:1-11` uses Node 22/pnpm. Both workflows target main only
  (`.github/workflows/test.yml:3-7`; frontend workflow `:3-13`), whereas this branch
  is master-integration. Service smoke checks use curl without fail-on-HTTP-error
  (`.github/workflows/test.yml:29-38`) and do not execute backend regression tests.
- **Scenario / impact:** integration pushes lack these automatic gates; a main/PR
  run can fail installation or treat an HTTP error as command success. Historical
  local test passes are not a dependable CI release barrier.
- **Remediation:** align CI with the supported package manager/runtime and intended
  branches; add explicit regression/type/build/security gates and HTTP status checks.
  Pin workflow actions to reviewed commits and set least workflow permissions as
  hardening. Do not run the CI teardown against production volumes.
- **Verification:** later exercise the corrected pipeline on a disposable runner,
  including deliberate benign test/HTTP failures. Branch protection and action
  permissions must be checked in repository hosting settings; not inspected here.

### P3-04 — Persisted job status is not a durable execution/recovery mechanism

**Severity:** Medium. **Confidence:** Confirmed control-flow gap. **Consolidation:** F23.

- **Evidence:** `backend/app/api/api_v1/knowledge_base.py:430-479` commits pending
  tasks then dispatches in-process FastAPI background work. Public processing commits
  processing before work (`backend/app/services/public_corpus.py:304-321`). Ingestion
  commits SQL chunks before vectors and final status (`backend/app/services/document_processor.py:354-420`).
  Analysis commits a processing run before generation (`backend/app/services/comparison.py:244-260`;
  `backend/app/models/analysis.py:13-23`). Startup only initializes storage, migrates
  and provisions corpus (`backend/app/main.py:28-39`); no lease/requeue reconciliation
  is wired there. Private resubmission rejects already-associated uploads (`backend/app/api/api_v1/knowledge_base.py:421-422`).
- **Scenario / impact:** process termination after commit, before dispatch or between
  store writes leaves pending/processing jobs and partial data. Exception handlers
  do not run after abrupt termination. Restarting containers does not resume work;
  stale status can block normal lifecycle actions. Completed-only retrieval helps
  prevent incomplete papers becoming ready but does not repair the job.
- **Remediation:** define durable claim/lease, idempotent resume or explicit failed
  transition, and scoped reconciliation of SQL/object/vector state; preserve sources
  and cleanup IDs. A bounded recovery mechanism can be incremental; this report
  does not prescribe a replacement infrastructure stack.
- **Verification:** later interrupt a disposable worker at each commit boundary,
  restart and verify deterministic recovery without duplicate publication, missing
  sources or deletion of unrelated data. Include analysis replay and stale claims.

### P3-05 — Coordinated, encrypted off-host recovery is not demonstrated

**Severity:** High. **Confidence:** Requires Verification. **Consolidation:** F24.

- **Evidence:** `deploy/README.md:10-16,68-83` requires consistent backup/restore and
  rollback but supplies no accepted drill result. `docs/phase21-rag-evaluation.md:87-88`
  records recovery as unaccepted; `docs/windows-migration-manifest.md:17-29` describes
  sensitive local SQL dumps, not a current coordinated backup of all stores.
  `docker-compose.production.yml:86-102` defines persistence, not off-host backups.
  `deploy/production.env.example:27-29` correctly requires separately backed-up
  personal-key encryption material.
- **Scenario / impact:** disk/VM/account loss or mismatched snapshots leave SQL
  documents without objects/vectors, lose research/history, or render saved encrypted
  AI keys unreadable. Backups might exist outside the repo; absence is not asserted.
- **Remediation:** owner-assigned encrypted off-host backup schedule, retention,
  independent key recovery and documented RPO/RTO; consistent restore manifests
  spanning SQL/object/vector/schema/model/image versions and pending jobs. Keep at
  least one recovery copy outside the VM and its principal failure domain.
- **Verification:** inspect protected backup metadata/access policy, then restore
  synthetic data to isolated volumes and prove object hashes, SQL/chunk/vector IDs,
  permissions, citations, conversations and key recovery. Record elapsed recovery
  time and achieved data-loss window. Never restore over the working installation.

### P3-06 — Readiness and reboot supervision do not cover dependent services

**Severity:** Medium. **Confidence:** Confirmed in repository configuration. **Consolidation:** F25.

- **Evidence:** `docker-compose.production.yml:21-27` waits for MySQL health but only
  service start for MinIO/Chroma; backend, Chroma and MinIO have no Compose-defined
  readiness probes. Image-defined store probes are unknown. The frontend has a
  Dockerfile healthcheck (`frontend/Dockerfile:53`). Backend `/api/health` always
  returns healthy without dependency checks (`backend/app/main.py:47-52`). Nginx
  depends on service start, not readiness (`docker-compose.production.yml:79`).
  TLS renewal/reload is a manual operational requirement (`deploy/README.md:38-41`).
- **Scenario / impact:** reachable processes mask store outages, a reboot starts an
  unusable stack, or an unverified renewal/reload path eventually causes HTTPS failure.
  This does not prove certificates currently expire or store images lack all probes.
- **Remediation:** distinguish liveness/readiness, use bounded dependency checks,
  alert on failed readiness and stalled jobs, and prove reboot/certificate renewal
  handling. Coordinate deployments with startup Alembic rather than assuming
  process restart is read-only (`backend/app/startup/migarate.py:77-101`).
- **Verification:** later simulate dependency unavailability and normal host reboot
  in staging; check readiness, startup retries, service recovery and certificate
  renewal/reload. Test that supervision never repeatedly restarts healthy long jobs.

### P3-07 — Production log rotation and capacity monitoring are not established

**Severity:** Medium. **Confidence:** Requires Verification of host logging defaults. **Consolidation:** F26.

- **Evidence:** `docker-compose.production.yml:5-84` supplies no logging limits;
  development explicitly caps some logs (`docker-compose.dev.yml:20-24,54-58,78-82`).
  `backend/app/main.py:11-14` configures INFO logging, and per-file processing logs
  metadata (`backend/app/services/document_processor.py:325-350,370-421`). The old
  disk inventory shows substantial image storage (`docs/cleanup-and-hosting-review-20261031.md:12-24`).
- **Scenario / impact:** if daemon logging/retention is not already bounded, routine
  requests and repeated failures grow logs until DB/temp/data writes fail; retained
  logs also preserve private metadata (P1-10). No current log growth was measured.
- **Remediation:** bounded protected log rotation, redaction/retention policy, disk
  and inode alerts, separate accounting for images/data/temp/backups and ingestion
  backpressure. Do not prune volumes or active/required rollback images.
- **Verification:** inspect actual Docker daemon logging settings, disk/inode
  metrics and alert delivery; use harmless staging logs to verify rotation. Check
  that disk-pressure response preserves database and recovery capacity.

### P3-08 — Oracle ARM64 deployment has no accepted architecture/capacity evidence

**Severity:** Medium. **Confidence:** Requires Verification. **Consolidation:** F27.

- **Evidence:** `docs/cleanup-and-hosting-review-20261031.md:14-16,112-115` records
  an 18.3 GB AMD64 backend and large ML/native dependencies. Production image digests
  (`docker-compose.production.yml:39,55,61,71`) were selected for Windows-verified
  versions (`deploy/README.md:63-64`); the repo does not establish that each digest is
  a multiarch index containing linux/arm64. `backend/requirements.txt:10-12,27-30`
  includes native vector/ML/image dependencies. The frontend lock includes ARM64
  SWC variants (`frontend/pnpm-lock.yaml:1400-1416`), which is encouraging, not an
  end-to-end image certificate.
- **Scenario / impact:** unsupported image manifests/wheels, ABI changes or expensive
  emulation prevent startup, exceed VM storage/memory, or alter embedding behavior.
  Actual ARM incompatibility and current image size are not newly measured here.
- **Remediation:** validate all manifests/wheels and build native ARM64 release
  images with CPU-appropriate ML dependencies, while preserving embedding identity;
  stage a consistent copy of data and measure simultaneous services. Retain AMD64
  rollback artifacts. Do not move live raw stores blindly across versions/architectures.
- **Verification:** later inspect manifests/SBOMs, run native ARM64 tests/normal
  ingestion and benign 20–30-user workload, verify cache cold/warm behavior, vectors,
  source permissions and recovery. Obtain actual Oracle allocation/availability
  before sizing; no free-tier quota or availability guarantee is made here.

### P3-09 — Production preflight does not validate personal-key encryption readiness

**Severity:** Medium. **Confidence:** Confirmed. **Consolidation:** F28.

- **Evidence:** `deploy/preflight.py:26-45,74` checks selected secrets/providers but
  never validates `AI_KEY_ENCRYPTION_KEY`, despite its requirement in
  `deploy/production.env.example:27-29`. `backend/app/services/ai_settings.py:61-86`
  validates it only on use, requiring 32 decoded bytes and successful decryption.
  Changing the key without re-encryption makes existing values unreadable.
- **Scenario / impact:** preflight can pass with missing/wrong encryption material
  while saved personal-provider settings fail at runtime. This fails closed with
  503; it is not plaintext disclosure or silent use of someone else's key.
- **Remediation:** validate key presence/format without printing it, preserve the
  correct key for restored ciphertext, and document backup/rotation/re-encryption.
  Include a synthetic ciphertext round-trip in a controlled release gate.
- **Verification:** later check absent/invalid key rejection and restored synthetic
  setting readability; confirm responses/logs remain masked. Preflight is advisory
  unless explicitly made a deployment gate.

### P3-10 — Current dependency vulnerability/support status is unverified

**Severity:** Medium. **Confidence:** Requires Verification. **Consolidation:** F29.

- **Evidence:** `docs/security-cleanup-20261009.md:59-91` records historical residual
  frontend and Python/Chroma advisories, with reachability caveats. Current frontend
  versions are `frontend/package.json:42-55` and the lockfile, including braces
  `frontend/pnpm-lock.yaml:3206-3213`; Python constraints are
  `backend/requirements.txt:1-30`. Production digests pin identity, not a vulnerability
  status. No current machine-readable advisory database/release SBOM was established.
- **Scenario / impact:** a vulnerable resolved runtime/parser/service component
  could be exposed by accepted documents or requests; build-only issues may have
  different reachability. No specific currently exploitable CVE is confirmed here.
- **Remediation:** scan exact release images/OS/Python/npm dependencies with current
  advisories, classify production reachability, verify upstream support, and patch
  with regression gates. Treat an old minimum version or old audit severity as an
  investigation lead, not proof of the current installed vulnerability.
- **Verification:** later obtain dated SBOM/advisory receipts and a reviewed
  reachability matrix. Confirm native dependency versions for each architecture.
  No library is labeled abandoned/unmaintained without current primary evidence.

## C. Secrets and build boundary

Positive controls: `.gitignore:70-80` excludes real production env, TLS directory,
sensitive SQL dumps and resolved Docker inventories. `backend/.dockerignore:1-21`
excludes env/data/log/test artifacts; `frontend/.dockerignore:1-10` excludes env and
local build outputs. Build contexts are the service directories; the repo-root
runtime `.env` is not passed as a Docker build argument by these Dockerfiles.
No tracked frontend `NEXT_PUBLIC` secret reference was found; the dev Compose's
public API URL is not a credential. `frontend/next.config.js:9-13` uses operator
build variables for output/proxy configuration, not browser credentials.

The dev frontend receives the shared `.env` at runtime (`docker-compose.dev.yml:74-75`),
which is excessive for a production frontend process; the production frontend does
not. Runtime environment variables can be read by privileged host/container operators.
AES-GCM personal-key storage protects against SQL-only disclosure, not theft of both
ciphertext and the backend encryption secret. Legacy application keys are plaintext
(P1-01). Backend receives the entire production env, including DB-root settings;
MinIO uses root credentials for app operations (P1-11). Real `.env` strength, ACLs,
remote repository history and actual image layer contents remain unverified.

Do not publish resolved Compose output or unrestricted `docker inspect` output.
Do not interpret ignored plaintext backups as encrypted or access-controlled.
Secrets should be provisioned separately from immutable images, restricted to the
services that need them, and rotated using tested store-specific procedures.

## D. Persistence, recovery and consistency

| State | Persistence in source | Recovery obligation |
| --- | --- | --- |
| MySQL | External mysql_data at /var/lib/mysql (`docker-compose.production.yml:46,88-90`) | Logical consistent dump or supported physical backup, schema revision, grants, hashes, sessions, analysis and key ciphertext; protect/expire restored sessions appropriately. |
| Chroma | External chroma_data at /data (`:56,91-93`) | Compatible server/client/index version, collection/chunk-ID manifest, supported snapshot/export or controlled rebuild. Live raw-directory copying is not proven safe. Dev file uses a different path (`docker-compose.dev.yml:105`). |
| MinIO | External minio_data at /data (`:66,94-96`) | Object bytes/keys/hashes plus bucket/policy/version metadata; use supported backup/mirror/snapshot under a consistency plan, not arbitrary internal-file copying. |
| Embeddings | External HF cache (`:20,97-99`) | Model artifacts/revision and parameters compatible with indexed vectors; native caches/extensions are not automatically portable. |
| Upload staging | External uploads (`:19,100-102`) plus staged MinIO objects | Include pending work and separately account for ephemeral local temp paths; a named uploads mount does not prove every temp file is there. |
| Secrets/config/images | Outside those data volumes | Independent encrypted key backup, image digests/SBOM, runtime config, TLS renewal arrangement, schema/model/version manifest. |

There is no atomic transaction across SQL, Chroma and MinIO. Ingestion deliberately
persists cleanup IDs before vector writes, and readiness filters exclude unfinished
tasks; these are beneficial controls. They do not replace reconciliation or a backup
consistency boundary. P2-05/P2-06 cover exception cleanup; P3-04 covers process-crash
recovery. P2-07 covers retained snapshots after source removal.

Recommended drill, **not executed**: establish a quiesced/consistent backup point;
record versions and SQL-document/chunk/object/vector manifests; encrypt/offload and
verify checksums; restore only to isolated disposable volumes with outbound AI/mail
disabled or stubbed; validate counts and identity/hash mappings, authorized downloads,
retrieval, saved histories and key decryption using synthetic fixtures; measure RPO/RTO;
retain a signed-off receipt. Image rollback alone cannot reverse schema/data changes.
Startup invokes Alembic, so launching an older/newer image must follow an explicit
migration/compatibility decision. Never use historical `reset-db.sql` in recovery.

## E. Oracle ARM64 / Ubuntu pilot assessment

The existing single-VM Compose topology is a plausible **candidate**, not accepted
capacity. No current Oracle free entitlement, VM reservation, storage quota, reclaim
policy or public host state was verified. Numeric free-tier claims in older project
notes must be rechecked separately; they are not adopted as current facts here.

- Use a supported Ubuntu ARM64 release and native tested images for all six services;
  verify manifest architecture rather than assuming a digest is multiarch. Avoid
  relying on AMD64 emulation for production parsing/embedding performance.
- Backend's historical 18.3 GB image is disk size, **not resident RAM**. HF model,
  PyTorch/native libraries, parsing buffers, Chroma, MySQL and frontend consume memory
  concurrently. Each worker can load its own cached model. Start with measured low
  concurrency; building on the small serving VM can need substantially more memory
  than running the release. A tested CPU-only build may reduce disk, but is future work.
- Preserve MiniLM/model identity; do not switch embedding providers during a host
  migration. Prepare cache permissions for a non-root backend. Cache-miss Hub downloads
  are a reliability/egress dependency; warm immutable artifacts remove that uncertainty.
- Only expose 443 and optionally 80 for redirect/certificate challenge. Deny public
  DB/Chroma/MinIO/frontend/backend ports at both cloud and host/Docker boundaries,
  including IPv6. Verify actual packet paths; a host firewall alone must not be assumed
  to override Docker port publishing. Restrict SSH to operator IP/VPN, key auth,
  non-root administration and cloud-account MFA. These are recommendations, not
  findings of an existing open SSH server.
- Use the existing Nginx TLS template with automated renewal/reload and one exact
  origin. Caddy is an alternative edge, not an installed feature; replacing Nginx
  requires separate header/proxy/stream acceptance and is unnecessary for this audit.
- Keep stores on the private single-host network and durable block storage, off-host
  encrypted backups, bounded logs and disk alerts. Single VM/region/account remains
  a failure domain; Always Free hosting does not provide application HA or free SMTP,
  domain, backup capacity or model availability by itself.

## F. Launch gates and outstanding verification

The consolidated report is authoritative for deduplicated priorities. Before public
exposure: close resource/preview and legacy-key issues; enforce secure profile and
data isolation; contain parsing and minimize secrets; prove supported release images,
architecture and TLS; accept crash recovery and coordinated backups; close the existing
Phase 21 quality gate. The prior maintenance run remained 12/13
(`docs/cleanup-and-hosting-review-20261031.md:170-177`); no new test result supersedes it.

Runtime checks still needed: effective service users/capabilities/mounts/limits;
firewall and actual ports; image manifests/SBOM/advisories; DB grants/bucket policies;
secret ACLs and key recovery; TLS validity/renewal, session/CSRF/proxy behavior;
reboot/readiness/stalled jobs; capacity/disk logging; complete synthetic authorization,
RAG/citations and restore acceptance. They were not performed under this audit.

**Part 3 complete as an offline source audit. No fixes, deployments, network requests
or application tests were performed.** Following the separate request to commit/tag,
the two Part 3/final reports form documentation checkpoint
`researchiq-security-audit-final-20261102`. This is not a deployment approval or a
completed implementation-phase checkpoint. Existing code/configuration changes and
the earlier audit files are outside this documentation commit.
