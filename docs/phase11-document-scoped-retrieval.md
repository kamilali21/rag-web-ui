# Phase 11 — Exact document retrieval

**Complete and deployed — 7 October 2026.** Checkpoint tag:
`researchiq-phase11-verified-20261007`.

Started 6 October 2026 after Phase 10 completion commit `903619e`, tag
`researchiq-phase10-verified-20261006`. First service checkpoint: `da75deb`.

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

## Authenticated API increment — 7 October 2026

`POST /api/retrieval/documents/query` calls the same `search_documents` service.
It requires the existing authenticated user/session and CSRF/origin checks.

```json
{"document_ids": [28, 31], "scope": "both", "query": "What methods were used?", "top_k": 5}
```

IDs above are illustrative; callers must submit actual accessible document IDs.

- `document_ids` is required: 1–20 positive integer IDs. Strings, booleans,
  fractional values, null, empty selections and unknown fields are rejected.
- Scope defaults to `both`; `public` and `private` further restrict selection.
  Query length and top-k limits reuse the existing request model (1–4000 query
  characters, nonblank query, top-k 1–20).
- Returns the existing `results` envelope: SQL-backed chunk content, score,
  immutable document/chunk/KB IDs and citation metadata. Missing vectors return
  no evidence; provider failures return a sanitized 503. Neither broadens search.
- A missing, inaccessible or non-Ready ID rejects the entire selection with the
  same generic 404. Duplicates are resolved once. No admin private-data bypass.
- Existing `/api/retrieval/query`, chat, upload and API-key routes are unchanged.
  There is no schema migration, new vector pipeline, LLM call or selection UI.

## API regression evidence

- Focused Phase 9/10/11 isolated suite: **98 passed, 1 MySQL-only skip**.
- The same suite on an isolated RAM-backed MySQL instance: **99 passed**, including
  the existing separate-connection revocation and migration gate at `riq_005`.
- Full isolated backend suite: **295 passed, 40 environment-specific skips**.
- New HTTP checks cover Public/Private/Both exact selection, trusted SQL metadata,
  malformed/missing/oversized IDs, duplicate IDs, whole-selection rejection,
  administrator boundaries, unauthenticated requests and provider failure/empty
  results. Service tests continue to cover same-collection exclusion and source
  withdrawal during vector retrieval.

```sh
python -m pytest tests/test_phase11_document_scope.py tests/test_phase9_retrieval_scope.py tests/test_phase10_assistant.py -q
```

The optional MySQL fixture only accepts the disposable
`127.0.0.1/researchiq_phase2_test` schema and deletes its test rows; never point
tests at production. Live acceptance is separate and preserves research data.

## Live acceptance and recovery

- Deployed by restarting the existing bind-mounted backend; no dependency/image
  rebuild, schema migration or data-volume recreation was required. Live health
  and OpenAPI checks confirm the new route is loaded.
- Real HTTP requests through nginx retrieved four SQL-matched chunks exclusively
  from private document 28 and four exclusively from public document 31. A mixed
  selection returned only those IDs, with no duplicate chunks. Another researcher
  could retrieve the public selection but not the mixed/foreign private selection.
- Invalid/missing/oversized selections, scope mismatch, missing sources,
  unauthenticated requests and invalid CSRF/origin were rejected. The original
  broad-scope endpoint still returned 200. No LLM calls were made by this gate.
- All original research-table rows, MinIO object fingerprints and Chroma vector
  IDs/content/metadata/embeddings are unchanged; revision remains `riq_005`.
  Temporary sessions 134–137 were removed. An existing session (133) was revoked
  concurrently: restoring only its revocation and automatic update timestamps
  **in memory** reproduced the original full-row hash. The raw aggregate mismatch
  and successful independent reconciliation are both retained.
- The first attempt timed out because the running container lacked model weights.
  Restored the original Phase 10 MiniLM cache, verifying weight SHA-256
  `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
  No embedding model, dimensions, vector data or environment configuration changed.
  Cache persistence across container recreation remains Phase 21 hardening work;
  a plain restart preserves the cache. Keep the verified archive for recovery.
- Local evidence: ignored `backend/.pytest_cache/phase11-final-20261007/` and its
  external copy under `ResearchIQ-recovery/20261003-cleanup/`, containing
  `before.json`, `after.json`, `receipt.json`, and `preservation-reconciliation.json`.
  The external `phase11_api_acceptance.py` and `phase11_reconcile.py` runners retain
  the exact checks; the failed initial receipt is `phase11-first-cache-timeout.json`.
- Pre-change source archive: `phase11-before-da75deb.zip` outside Git. To reverse
  this API increment, restore only the prior retrieval API module from that
  checkpoint after preserving later edits, then restart backend. No database
  rollback is needed. Frontend recovery is documented separately below.

## Hero frontend included in this checkpoint

See [auth-hero-presentation.md](auth-hero-presentation.md). Previously deployed
presentation changes are now documented and checkpointed alongside Phase 11.
Their 74-test frontend suite, TypeScript check and production build passed;
authentication handlers and forms are unchanged.

## Next existing-plan task

Phase 12 is a structured single-document
summary with citations, using this exact-selection service. Insights selection
and Compare/Analyze remain later phases; none is implemented by this API gate.
