# Security Workstream 1 — focused remediation record

Date: 3 November 2026. Baseline: `9981318`, `master-integration`.
Follow-up to the final audit and the four-prompt checklist; not a new integration phase.

## Invocation 1 — F01 only

The owner explicitly chose: disable legacy application-key APIs and preserve personal
OpenRouter/OpenAI keys. No legacy-key migration, record deletion, credential rotation,
schema change or new infrastructure is part of this invocation.

### Implementation

- `backend/app/api/api_v1/api_keys.py`: a router-level retirement dependency denies
  list/create/update/delete before their authentication/database dependencies run.
- `backend/app/api/openapi/knowledge.py`: the same guard denies legacy integration
  retrieval before SQL, embedding or vector access.
- `backend/app/core/security.py`: common HTTP 410 response with no-store and a clear
  distinction from personal AI settings. The retired authentication dependency itself
  also rejects without reading a key or querying SQL. There is no configuration switch
  that silently re-enables plaintext credentials.
- Both retired routers are excluded from the API schema. Routes still return an
  explicit retirement response rather than disclosing stored credentials.
- Personal `/api/ai-settings`, encrypted provider credentials, browser sessions,
  public/private library authorization, citations and model routing are unchanged.

Stored legacy rows and historical backups remain unchanged and sensitive. They are
not converted to hashes or erased by disabling the API. Do not claim raw credentials
are absent from old databases/backups. The current application will no longer accept
them after activation; rolling back to an older image/source could re-enable them.
Future removal/retention or secure reintroduction needs a separate reviewed change.

### Verification boundary

New tests in `backend/tests/test_legacy_api_retirement.py` check every retired method
with/without credentials, rejection before auth/SQL, no key echo or cacheability,
preservation of existing key rows, direct retired-dependency rejection and API docs.
Existing authorization/authentication/privacy tests now expect retirement rather
than legacy key acceptance. The personal-AI-settings suite checks owner isolation,
encryption/masking and provider behavior alongside the browser/RAG regressions.

Tests use the existing `researchiq-backend-tests:phase8` image with `--pull never`,
`--network none`, a read-only backend source mount and disposable in-memory SQLite.
No `.env` file is passed, the optional MySQL fixture is disabled, and no application
startup/migrations, production database, external provider or real document is used.
No image build, live restart, deployment, secret rotation, commit or tag is included.

**Observed result:** 117 passed, 5 skipped, 11 warnings in 85.53 seconds. The warnings
are existing Pydantic/SQLAlchemy deprecations and a personal-key test's empty regex
warning. No MySQL or live deployment acceptance is claimed. All 13 new F01 cases pass.
The exact pytest selection was:

```text
python -m pytest -q -p no:cacheprovider tests/test_legacy_api_retirement.py tests/test_phase2_authorization.py tests/test_phase3_authentication.py tests/test_personal_ai_settings.py tests/test_phase21_redteam.py
```

F01 is **VERIFIED COMPLETE for the owner-selected server-side retirement in source
and isolated HTTP tests**. **NEEDS OWNER/RUNTIME VERIFICATION for activation**: a
separately authorized backend rollout must load this source and verify HTTP 410 on
both retired surfaces, successful browser login and masked personal AI settings.
Do not treat this source-only checkpoint as an already deployed fix.

### Next work and scope limits

- F01: **VERIFIED COMPLETE** in source/isolated tests as qualified above; activation pending.
- F04: **STILL OPEN** — legacy auth/default configuration is unchanged by this fix.
- F15: **NEEDS OWNER/RUNTIME VERIFICATION** — production source keeps stores private,
  but actual host reachability/auth/TLS is not proven. No new network test was run.
- F05/F11: **STILL OPEN** against the audit baseline; not implemented in this invocation.
- Exact next IDs: **F04 and F15**, within Workstream 1. Stop before Workstream 2.

The previous uncommitted local/tunnel authentication work is preserved. This run only
changes two legacy-status expectations in the already modified authentication test
file; it does not bundle that older work into a commit. Historical audit reports remain
unchanged so that findings and subsequent remediation evidence stay distinguishable.

## Continuation - 5 November 2026

The owner requested completion/checkpointing of the remaining workstream. This
continuation prepares the remaining source/configuration controls together; it does
not treat an offline check as proof of deployed grants, service isolation or ingestion.
No production deployment, rebuild, database migration, credential rotation, grant
change, volume ownership change, external network test or provider request was run.

### Changes

- **F04:** production settings fail closed during configuration import, before
  clients initialize. Verified email sessions, exact HTTPS origin, no local-origin
  exceptions, independent non-placeholder secrets, a single private proxy peer,
  non-root SQL identity and working SMTP security modes are required. There is no
  silent legacy-auth fallback in the production profile. Development remains explicit.
- **F15:** preflight rejects store ports, extra/untrusted network membership,
  frontend/proxy membership in the data network, missing stores, Docker socket mounts
  and privileged/host networking. Production retains the isolated internal network;
  it does not claim Chroma service authentication has been added.
- **F05:** the default backend build ends in a production stage using UID/GID 10001.
  Production Compose drops all capabilities, prohibits privilege escalation, makes
  the root filesystem read-only and limits writes to upload/cache volumes plus a
  256 MiB noexec temporary mount. Local Compose selects the original local stage;
  the dev Dockerfile names its stage compatibly for Compose merging. No live cache
  ownership was changed. Image build and synthetic end-to-end ingestion remain pending.
- **F11:** production passes an explicit backend environment allowlist, excluding
  root/bootstrap credentials. MinIO root and bucket-scoped application identities
  are separate settings. MySQL image auto-grants are removed. Runtime startup checks
  the schema revision instead of applying DDL and requires a pre-provisioned bucket.
  `deploy/runtime-privileges.md` defines the operator-reviewed SQL grants, separate
  migration workflow and bucket policy, acceptance and rollback. These policies have
  **not** been applied to existing accounts or proven effective on a target host.
- Existing local/tunnel origin and cookie changes are included in this coherent
  checkpoint, with their regression tests and `docs/tunnel-access.md`. Production
  rejects those local exceptions and never includes the development Nginx rewrite.
  Previously untracked audit Parts 1/2 remain untouched and outside this commit.

### Observed checks

1. Existing offline test image, no pull/network, read-only source mounts and no real
   env/volumes: **148 passed, 5 skipped, 11 existing warnings (79.86 s)** across
   production guards/preflight, legacy-key retirement, Phase 2 authorization,
   Phase 3 authentication, personal AI keys and Phase 21 HTTP privacy regressions.
   Five existing optional tests remain skipped; this is not disposable-MySQL acceptance.
2. After final hostname/SMTP validation corrections, production/preflight tests ran
   as UID 10001 with read-only rootfs, ALL capabilities dropped, no-new-privileges
   and bounded noexec `/tmp`: **34 passed, 1 existing warning (1.29 s)**. This used
   the existing test image, not a rebuilt production image or the real model cache.
3. Actual production Compose resolution with synthetic settings passed preflight.
   This caught and corrected YAML quoting for the temporary mount before checkpoint.
   No real env file was read or secrets printed. `git diff --check` passed.

The first combined test invocation had a deployment-module import-path collection
error; rerunning with `/audit` on PYTHONPATH produced the results above. No failing
application test was hidden. No frontend change/build is involved in this workstream.

### Checkpoint and release status

Planned annotated tag: `researchiq-security-workstream-1-source-20261105`.
This is a **source-remediation checkpoint**, not a production-ready/completed-phase tag.

| Finding | Source/test status | Remaining gate |
| --- | --- | --- |
| F01 | VERIFIED COMPLETE: retirement and BYOK preservation | Backend activation and live 410/browser/BYOK checks |
| F04 | VERIFIED COMPLETE: production configuration guard | Secure host startup, HTTPS/session/CSRF acceptance |
| F15 | VERIFIED COMPLETE: source/preflight isolation constraints | NEEDS OWNER/RUNTIME VERIFICATION: actual IPv4/IPv6 reachability and trusted peers |
| F05 | Production controls implemented; isolated guard tests pass | NEEDS OWNER/RUNTIME VERIFICATION: built image, target volume permissions, synthetic ingestion/retrieval |
| F11 | Credential separation/bootstrap gates implemented | NEEDS OWNER/RUNTIME VERIFICATION: provision and prove limited SQL/MinIO grants |

**Workstream 1 is not fully closed until those runtime gates pass.** Public launch
remains blocked by the audit's other P0s as well. Workstream 2 implementation has
not started; next source findings are **F02/F03**, after owner agreement on pilot
budgets/limits. Do not silently enforce proposed quotas or move to later prompts.

Read `rAGRIsearch_Codex_Prompts_05_06.pdf` in the parent Projects folder (both pages).
Reserved for future sessions only: measured performance for one user journey and
accessibility/privacy UX for one journey, at most two targeted changes per prompt.
No Prompt 5/6 work was executed. This durable note records the reading without
promising cross-session memory or replacing the source document.
