# Phase 13 — Structured Document Summaries

**Status:** Complete, 17 October 2026
**Branch:** `master-integration`
**Recovery tag:** `researchiq-phase13-summary-20261017`

## Delivered

Added an authenticated temporary summary endpoint at
`POST /api/retrieval/documents/summarize`. The request contains one positive
document ID and either `private` or `public` scope. The service reuses the
existing exact-document retrieval path and does not widen retrieval to sibling
documents or collections.

Private requests require an active owner and a ready document. Public requests
require a ready document in the system-managed corpus whose publication status
is `published`. The service resolves access again after the provider call, so
an ownership, account, processing, or publication change during generation
discards the result.

The response has five academic sections: objective, methods/context, key
findings, limitations, and implications/conclusion. Document passages are
treated as untrusted input. Model output is validated as a bounded structured
object; every cited evidence ID must map to retrieved evidence, and returned
citation metadata is built from SQL-backed chunk and document records. Empty
sections say **“Not identified in retrieved evidence.”** Summaries are returned
only to the caller and are not stored in chat or summary history.

Ready private document details and published public document details expose a
**Summarize paper** action with loading, error, and retry states. Citations link
to the corresponding authorized PDF route and page. Unpublished drafts do not
show a summary action.

## Verification

- Focused backend module: 15 passed, 1 opt-in provider test skipped by default.
- Opt-in provider acceptance: 1 passed using fabricated paper passages in the
  isolated SQLite/API test fixture. Both private and public summaries produced
  grounded claims with citations to the selected document. Cross-user private
  access remains denied by the focused authorization tests. The test asserted
  no chat messages were written; fixture teardown removed its synthetic data.
- Full backend regression: 352 passed, 42 skipped.
- Frontend Jest: 90 passed in 16 suites.
- TypeScript: `tsc --noEmit` passed.
- Production frontend Docker builder: passed. Next.js reported the repository's
  existing ESLint option incompatibility and Tailwind line-clamp deprecation
  warnings; neither prevented compilation, static generation, or build output.
- No migration was required. No live ResearchIQ MySQL, MinIO, Chroma, or user
  records were changed. Existing chat, retrieval, and document behavior remained
  covered by the regression suite.

## 19 October reliability follow-up

A live repeat exposed a presentation-limit failure: valid provider JSON contained
more than two findings, causing both generation attempts to fail validation.
The bounded draft now validates up to eight claims per section and returns the
first two only after validating every citation. Focused tests pass (23 passed,
1 opt-in test skipped); two post-fix live summaries completed, with the warm
request taking 9.6 seconds. Cold model loading remains slower. See
[the follow-up record](dashboard-summary-followup-20261019.md) for evidence and
the accompanying dashboard changes. Historical phase/checkpoint records are unchanged.

## Next gate

Phase 14 is **Insights on real catalog data**. Follow the Phase 14 task in the
working Master Integration Plan and keep its own acceptance gate and recovery
checkpoint before proceeding to Phase 15.
