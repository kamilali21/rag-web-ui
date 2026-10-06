# Phase 11 — Exact document retrieval

Started 6 October 2026 after Phase 10 completion commit `903619e`, tag
`researchiq-phase10-verified-20261006`. This is the first service increment,
not a Phase 11 completion claim.

- Extended the existing SQL resolver and vector retrieval; no new RAG pipeline,
  schema, provider, UI or source-scope semantics.
- `search_documents` requires 1–20 positive integer IDs. Empty/missing/invalid
  selections cannot fall back to broad retrieval. Duplicates resolve once.
- Every selected document must exist, be Ready, and be accessible in the requested
  Public/Private/Both scope. A missing, foreign, draft, archived or failed item
  rejects the whole request before vectors are queried.
- Exact IDs constrain native vector filters and SQL evidence reconstruction.
  A fresh SQL recheck rejects the selection if a source is withdrawn during search.
- Existing scope-only callers retain their prior behavior. Regression tests caught
  and corrected parameter shadowing during this change before checkpointing.

## Evidence

- Combined Phase 9/10/11 isolated suite: **72 passed, 1 MySQL-only skip**.
- The same suite against the disposable MySQL schema: **73 passed**, including
  source revocation on a separate connection and migration safety.
- Read-only live service acceptance retrieved four chunks exclusively from private
  document 28 and four exclusively from public document 31. A selection containing
  a missing ID was rejected. No LLM calls or data mutations occurred.
- Receipt: ignored `backend/.pytest_cache/phase11-live-read.json`; the matching
  runner is `phase11_live_read.py` in the same directory.

## Remaining Phase 11 work

Expose exact selection through the existing authenticated retrieval API with a
bounded request schema and API-level acceptance checks. Preserve the service's
all-or-nothing authorization and existing broad-scope routes. Complete that gate
before Phase 12's structured summary; do not start synthesis or Insights now.
