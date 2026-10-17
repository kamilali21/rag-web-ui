# ResearchIQ / rAGRI search — project status, 17 October 2026

This status follows the working `ResearchIQ_Master_Integration_Plan.pdf`,
including its 17 October Phase 12 amendment. The dated 15 September original is
preserved. Completed phase numbers and their historical checkpoint tags remain
unchanged.

Phase 12 (researcher profile/publication requests) and Phase 13 (structured
single-document summaries) are complete. The active branch is `master-integration`.

Phase 13 adds an exact-document summary API for ready, owner-owned private
documents and ready, published public documents. It returns five academic
sections with server-verified citations, marks unsupported sections, and keeps
results temporary. Private and public library details expose the action; no
chat, schema, or history behavior changed. The implementation and test evidence
are recorded in [phase13-document-summary.md](phase13-document-summary.md).

Verification passed: backend full regression (352 passed, 42 skipped); focused
Phase 13 backend tests (15 passed, 1 opt-in live test skipped by default); the
opt-in synthetic-only provider acceptance (1 passed); frontend Jest (90 passed
in 16 suites); TypeScript; and the optimized production frontend build. There
were no database migrations or persistent synthetic test records.

The exact next plan task is **Phase 14 — Insights on real catalog data**. Do not
skip ahead to Phase 15; retain the incremental tests, live acceptance, and
recovery-checkpoint gates.
