# Phase 14 - Insights on real catalog data

Date: 19 October 2026. Checkpoint: `researchiq-phase14-insights-20261019`.

## Delivered scope

Insights now loads real ready documents, defaulting to the published public
corpus. Private shows only the signed-in user's ready documents; Both is their
union with the published corpus. The former sample dataset is removed and the
navigation preview lock is removed. Discovery uses the shared SQL authorization
and latest-processing-state boundary used by retrieval, including for admins.

The screen reuses Library's table, compact desktop/mobile rows, search bar,
collapsible filters, theme controls, action buttons and bottom pagination.
Search covers title, filename, author and abstract; filters cover author,
department, document type and publication-year range. Results use bounded stable
ID cursors. Empty, loading, failed and retry states do not display sample papers.

Users can select up to five papers across pages within a scope. Changing scope
clears selection. Compare requires at least two; Analyse requires one (the
contradictions configuration requires two). Both actions open a configuration
dialog and then revalidate the exact selected IDs on the server before showing a
temporary metadata workspace. Revoked/unready/foreign selections fail as a whole.
Stale asynchronous responses are ignored and dialogs restore keyboard focus.

This is the Phase 14 discovery/selection gate. Workspaces explicitly state that
no AI findings have been generated. Evidence-backed comparison and persistence
belong to Phase 15; generated analysis belongs to Phase 16. No schema, history,
provider configuration, authentication or publication approval changes were made.
Public details reuse the existing details dialog; private details recheck access
and reuse owner-checked content and summary endpoints.

## Verification

- Full backend regression: **383 passed, 42 skipped**. Skips are opt-in or
  environment-specific gates; they are not counted as successful executions.
- Focused Insights/retrieval/summary gate: **72 passed, 1 skipped**.
- Full frontend regression: **99 tests in 16 suites passed**. Following the
  correction of an unsupported test-query option, all **9 Insights tests**
  passed again and standalone TypeScript checking passed.
- Production frontend build passed. Deployed `researchiq-frontend:phase14-20261019`
  (image manifest `sha256:d6a10932197704894586d80d6b9d3eedb3c614a8ee7686bf780670e75be9f454`).
  Recreated frontend only, restarted the source-mounted backend without rebuilding
  its image, and reloaded nginx. Health and `/dashboard/insights` returned 200;
  served JavaScript contains the new catalog/selection UI and CSS contains the
  shared Library styles. Anonymous catalog access still returns 401.
- Existing build warnings: Next/ESLint option incompatibility and Tailwind's
  built-in line-clamp plugin notice. The build's separate type checking passes;
  these warnings do not constitute a clean standalone lint run.

Live HTTP acceptance through nginx used temporary synthetic users, private PDF
objects and catalog readiness records. This is a catalog/access test, not an
ingestion or model-generation test. It verified:

1. Nine existing ready public papers returned by the real catalog.
2. Private/Both ownership, foreign detail/selection/PDF rejection, anonymous 401.
3. Owner-only private PDF download and an existing public PDF opening.
4. Combined filters, stable pagination, exact IDs and order in Compare/Analyse.
5. A new failed processing attempt immediately excluding the selected fixture.
6. Removal of only synthetic SQL records, sessions and MinIO objects. Hashes of
   original users, roles, collections, documents, tasks, chunks, uploads, academic
   metadata, chats/messages, profiles and publication/withdrawal requests matched
   before/after. Alembic remained `riq_006`. Chroma was not modified.

Browser inventory returned no connected surfaces. Rendered desktop/mobile visual
inspection is therefore not claimed; UI interactions are covered by frontend
tests, shared layout classes and deployed-asset checks.

Reproduce the live gate only on the local Windows deployment:

```powershell
docker compose exec -T -e PHASE14_LIVE_ACCEPTANCE=1 backend python -m tests.phase14_live_acceptance
```

It creates synthetic fixtures and cleans their exact IDs/paths in `finally`.
Do not kill it mid-run. No external model call, mail delivery or index write is
required. Existing user sessions are not used or rotated.

## Planning and preserved follow-up

The working Master Plan now has a dated page 27 recording future department and
supervisor-scoped review queues and supervisor-assisted similarity/plagiarism
review. Detailed boundaries and future gates are in
[the future extensions note](future-supervision-and-similarity-review.md).
These features are planned only; current roles are unchanged. Existing phase
numbers and historical tags are preserved. The new PDF page was rendered and
visually checked; the tracked and Projects-root working PDFs match. The dated
original PDF is untouched.

This checkpoint also preserves the already requested, verified dashboard
publication cards/activity and Phase 13 summary reliability follow-up. Their
separate scope and live evidence are recorded in
[the follow-up receipt](dashboard-summary-followup-20261019.md).

## Recovery and next gate

The prior frontend image is preserved as
`researchiq-frontend:pre-phase14-20261019`. Rollback requires preserving later
work, reverting this source increment, restarting the source-mounted backend,
and restoring that frontend image (recreate frontend only; reload nginx).
No database rollback or volume operation is required. The source tag is not a
backup of MySQL, MinIO or Chroma.

Next: **Phase 15 - Compare with evidence persistence**. Start by implementing
the server-side exact-selection comparison contract, evidence-backed structured
output and analysis/evidence persistence with the plan's access rules and tests.
Do not treat Phase 14's temporary metadata workspace as a generated comparison.
Phase 15 has not been started.
