# Phase 20 — Cross-feature Security — 29 October 2026

## Scope and objectives

This is the security gate in the amended Master Integration Plan, following
Phase 19 (`3db258d`, `researchiq-phase19-history-20261027`). Exercise OTP abuse,
role bypass, private ID guessing, prompt injection, upload abuse and output
sanitization across the implemented features. Fix confirmed defects without
changing the authentication architecture, publication workflow or database.
Phase 21 remains RAG quality evaluation; Phase 22 remains deployment hardening.

## Confirmed findings and changes

1. Private ingestion previously accepted empty/unsupported files and trusted the
   submitted content type before staging them. Public and private ingestion now
   share an extension/filename allowlist, non-empty content checks, PDF signature
   checking, existing DOCX expansion limits, UTF-8/non-binary text validation and
   MIME consistency checks. Missing/generic binary MIME remains supported; stored
   MIME is canonical. Public uploads keep their 20 MiB bound; private requests
   keep their aggregate 100 MiB bound. Private temporary keys use UUIDs while
   display filenames and final document lifecycle remain unchanged. DOCX expansion
   bombs now fail before storage, parsing or embedding.
2. Profile photos previously needed only a recognizable magic prefix. New photos
   must fully decode as still PNG/JPEG/WebP, with the existing 3 MiB limit and a
   16-megapixel limit. Truncated, forged, animated and oversized images are
   rejected before changing the existing photo. Pillow 13.0.0 is pinned in
   `backend/requirements.txt`. Existing stored photos are not rewritten.
3. Chat Markdown could load model-supplied images from external URLs, potentially
   leaking evidence through automatic requests. Images now render as escaped
   text placeholders. Raw HTML stays disabled and ReactMarkdown's default safe
   URL handling remains enabled. Normal user-clicked links, citation popovers,
   code and comparison tables retain their existing behavior.

No migration: `riq_008`. No model/provider changes. No production-data cleanup.

## Security coverage

| Boundary | Evidence |
| --- | --- |
| OTP/login abuse | `test_phase3_authentication.py`: keyed hashes, expiry, attempt/single-use limits, resend/IP/email throttles, SMTP TLS failures, origin, CSRF, session revocation and password recovery |
| Role bypass/private IDs | Phase 2/4/9/11/12 suites: current ownership, inactive/system users, admin private-library isolation, exact-request review and ready/published source checks |
| New-feature session protections | `test_phase20_security.py`: cookie CSRF cannot be bypassed by legacy bearer headers on Profile, publication review, personal AI settings, Summary, Compare or Analyse |
| Saved content and keys | Phase 19 and personal AI suites: owner-only history, source revocation, snapshot redaction, encrypted owner-only keys and provider isolation |
| Untrusted model/source data | Phase 9/10/13/15–18 suites plus the Phase 20 hostile-source test: SQL-rehydrated evidence, exact document scope, unknown citations/malformed output rejected, no broadened retrieval |
| Upload abuse | Phase 4/8/12/20 suites: filenames, MIME, empty/binary/spoofed uploads, expanded DOCX limits, full photo decoding, replacement preservation and byte/pixel bounds |
| Output sanitization | Real ReactMarkdown/remark-gfm/rehype-highlight test rejects automatic images, raw HTML, script and data URLs; preserves citations, ordinary links and tables. Jest confirms Answer uses the safe image renderer |

## Validation and deployment receipt

**Complete.** This receipt and the Phase 20 changes share the annotated recovery
checkpoint `researchiq-phase20-security-20261029` on `master-integration`.
No push. Phase 21 has not started.

- Focused backend run: 83 passed, 5 opt-in checks skipped. Local receipt:
  `backend/.local/tmp/phase20-focused.xml`.
- Frontend: 132 tests passed in 20 suites; TypeScript checking passed.
- Real Markdown pipeline: `node tests/phase20-markdown-security.mjs` passed.
- Full backend regression: **586 passed, 44 skipped**, no failures. Skips are
  explicitly opt-in migration/concurrency/provider tests, not silently passed
  security checks. Receipt: `backend/.local/tmp/phase20-regression.xml`.
- Separate MySQL gate: **41 passed**, no skips. An isolated MySQL 8 container with
  no published ports or external network was initialized through `riq_008` and
  ran OTP request/verification/signup race tests plus all 38 Phase 20 tests.
  The disposable container and its anonymous test volume were removed afterward.
  Receipt: `backend/.local/tmp/phase20-mysql.xml`.
- Synthetic live acceptance passed: private/public PDF upload, processing and
  indexing; owner-only private access; non-admin review/corpus rejection;
  cross-feature CSRF and foreign-origin rejection; invalid uploads; sandboxed
  PDF download; valid/forged photo handling and isolation. The real configured
  provider produced a cited comparison in **41.82s**; saved reopening and
  idempotency, source revocation, history redaction and logout all passed.
  Cleanup proved original SQL fingerprints, MinIO objects and Chroma vector IDs
  unchanged. Receipt: `backend/.local/tmp/phase20-live-receipt.json`.
  SQL fingerprints exclude transient session/OTP/rate-limit tables and the
  separately checked Alembic marker; fixture auth rows are removed by exact
  synthetic user IDs.
- Production frontend build passed (Next.js compilation, type validation, all
  16 static pages and image export). Backend and frontend are deployed locally.
  Served chat assets contain the safe image renderer and existing citation UI;
  health, anonymous rejection, Pillow 13.0.0 and unchanged `riq_008` were checked.
  Receipt: `backend/.local/tmp/phase20-deployment-receipt.json`.
- Browser inventory returned no connected browser; visual browser acceptance is
  not claimed. API and renderer checks are independently recorded.

The interrupted parallel image builds did not produce deployable images. The
backend dependency was subsequently built offline from the preserved base image
and the cached official wheel, avoiding a reinstall of the RAG/ML stack. The
tracked requirements and normal Dockerfile remain the clean-build source of
truth. Local rollback base: `researchiq-backend:pre-phase20-20261029`; frontend
rollback: `researchiq-frontend:phase19-verified-20261027`.
The verified images are tagged `researchiq-backend:phase20-verified-20261029` and
`researchiq-frontend:phase20-verified-20261029`. Backend code remains bind-mounted
from the matching Git checkout; an image tag alone is not a source-code rollback.

For rollback, preserve current work, use a separate checkout of the preceding
Phase 19 tag, and run it with the preserved backend/frontend images. No schema
rollback is needed. Do not reset the active checkout or restore database volumes.

## Reproduction

- Backend: `python -m pytest tests -q`; focused gate:
  `python -m pytest tests/test_phase20_security.py -q`.
- MySQL: `python -m tests.phase20_mysql_gate` with `PHASE2_TEST_DATABASE_URI`
  targeting only `127.0.0.1/researchiq_phase2_test` inside a disposable MySQL
  container's network namespace. The helper refuses other hosts/schema names.
  Never point this resettable test fixture at application data.
- Frontend: `npm run test:ci -- --runInBand`, `npx tsc --noEmit`,
  `node tests/phase20-markdown-security.mjs`, production `docker compose build frontend`.
- Synthetic live: inside the local backend only,
  `PHASE20_LIVE_ACCEPTANCE=1 python -m tests.phase20_live_acceptance`.
  The shared harness creates temporary users and PDFs, tests existing processing,
  retrieval/comparison/citations and saved access, then removes its own fixtures.
  It compares original SQL row fingerprints, MinIO object names/ETags/sizes and
  Chroma vector IDs after cleanup. No existing user key is used for generation.

## Limits and remaining plan gates

This is a bounded application security audit and regression gate, not a claim of
zero vulnerabilities or an external penetration test. Citation membership and
authorization checks do not prove every generated claim is true or semantically
faithful; quality evaluation remains Phase 21. Upload validation is not antivirus
or content disarm/reconstruction. PDF parsing still occurs in the existing
processor, whose failures remain safely reported. Existing photos are not
re-encoded and their embedded metadata is not removed.

Public TLS, production secrets/quotas, dependency/container scanning, parser
isolation and deployment configuration must be assessed in the existing Phase 22
gate. The current loopback HTTP development origin is not a production setup.
No new roadmap or phase renumbering is introduced.

The frontend build's existing ESLint-option incompatibility means its lint step
is not a successful lint gate. Standalone TypeScript and Jest results are reported
separately. Existing SQLAlchemy/Pydantic deprecation warnings remain unchanged.

Reference: the upload controls follow the layered-validation approach in the
[OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
