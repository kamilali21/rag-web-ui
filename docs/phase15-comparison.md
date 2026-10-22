# Phase 15 comparison recovery checkpoint - 22 October 2026

Status: **complete**. On 22 October the user clarified that declining the live
command was accidental and authorized it. Synthetic acceptance now passes.
The earlier pending checkpoint was staged but never committed or tagged.

## Implemented scope

In Insights, select 2-5 ready papers, choose Compare, select criteria and choose
Generate comparison. Public selections must be published; private selections
must belong to the requester. Both scope preserves those same boundaries.

- `POST /api/insights/comparisons` retrieves evidence separately for each exact
  selected document. It supports objective, methodology, context, population,
  dataset, variables, techniques, findings, limitations, conclusion and future work.
- Server validation requires the requested rows/documents and checks every claim's
  citation against evidence from that same paper. Unsupported cells are marked
  “Not identified in retrieved evidence.” Citation validation establishes source
  identity, not independent scientific verification of generated statements.
- Compatibility includes Highly related, Related, Weakly related, Different
  domains and Insufficient evidence. Cross-domain comparison is allowed with
  explanatory caution. Retrieval scores are not scientific confidence.
- Evidence is untrusted input. The model returns structured JSON, never rendered
  HTML. React renders text, per-paper/page links and inspectable evidence excerpts.
- Access, document hashes and SQL chunk excerpts are rechecked before saving.
  Runs, document identities and immutable excerpt/hash snapshots are persisted
  using additive Alembic revision `riq_007`.
- `GET /api/insights/comparisons/{run_id}` is owner-only and rechecks current
  source availability/access. Published source papers do not make the saved run
  public. Revoked, archived or deleted sources prevent reopening the result.
  Evidence snapshots survive chunk reindexing; they do not bypass access checks.
- A per-owner request UUID prevents duplicate generation on a successful request
  replay. Changed options with the same UUID are rejected. Loading, failure,
  retry, insufficient-evidence and saved-link states are provided.
- Retrieval is bounded to eight passages per paper, 1,400 characters per excerpt.
  Generation uses the existing configured model with at most two attempts total
  (a bounded 429 retry or malformed-output correction). No paid fallback or model
  configuration change was introduced.

Saved-run reopening is part of the persistence foundation required by the existing
plan correction. A history browser and generated Analyse workflow are not included.
A process interruption can leave a run marked processing; no background recovery
worker was added in this phase.

## Verification evidence

| Check | Result |
| --- | --- |
| Focused comparison backend tests | 30 passed |
| Full backend regression | 413 passed, 43 skipped |
| Disposable MySQL migration test | 1 passed |
| Focused Insights frontend tests | 13 passed |
| Full frontend tests | 103 passed across 17 suites |
| TypeScript | Passed |
| Production frontend Docker build | Passed |
| Local health / Insights HTTP page | Healthy / 200 |
| Served comparison bundle | Comparison endpoint and result assets found |
| Anonymous comparison API access | Rejected with 401 |
| Authenticated synthetic live comparison | Passed; generation 6.28 seconds |
| Rendered browser inspection | Unavailable: no connected browser |

Backend skips are opt-in/environment-specific checks, not successful acceptance.
The production build retained existing Next.js ESLint-option and Tailwind
line-clamp warnings; this receipt does not claim a clean standalone lint run.

The disposable migration test exercised upgrade from `riq_006`, unchanged legacy
values, source-deletion snapshot retention, run-deletion cascades, populated
downgrade refusal and empty downgrade/re-upgrade.

## Deployment and recovery

- Before the live migration, the backend was briefly stopped and MySQL was
  backed up to ignored local `.local/backups/pre-phase15-20261021.sql`.
- The tested migration was applied to the running database. Its receipt at
  ignored `backend/.local/tmp/phase15-migration-receipt.json` records revision
  `riq_007`, unchanged values in all 22 original tables and empty new analysis
  tables immediately after migration. This is a point-in-time check.
- Backend source was restarted without rebuilding its image. The frontend was
  rebuilt/recreated and nginx reloaded. The existing stores and model settings
  were retained.
- Frontend build manifest:
  `sha256:01e55710ed80a2f03001ef3602fa8302e31b32999cf22e5cd33aab7aba46890f`.
  Previous frontend image: `researchiq-frontend:pre-phase15-20261021`.
- Source checkpoint: annotated tag
  `researchiq-phase15-compare-20261022`.
  No push was requested.

Prefer a forward fix or a compatible feature rollback that retains the `riq_007`
migration chain and analysis data. Do not simply deploy old backend source without
that migration: its startup migration check would not recognize the newer revision.
Do not automatically downgrade or restore the database. Downgrade deliberately
refuses populated analysis tables; restoring the pre-migration backup would discard
subsequent writes and requires a separately reviewed recovery window. A source tag
is not a backup of SQL, MinIO or Chroma data.

## Live acceptance - 22 October 2026

The opt-in runner `backend/tests/phase15_live_acceptance.py` passed through the
running nginx/backend and configured provider with:

```powershell
docker compose exec -T -e PHASE15_LIVE_ACCEPTANCE=1 backend python -m tests.phase15_live_acceptance
```

Synthetic public/private PDFs uploaded and indexed successfully. Generation,
per-paper/page citations, saved reopening, idempotency, PDF opening, owner-only
access and source revocation passed. Cleanup verified original application SQL
rows, MinIO object identities and Chroma vector IDs unchanged. The local receipt
is `backend/.local/tmp/phase15-live-receipt.json` (ignored).

Browser inventory remains empty; no rendered-browser acceptance is claimed.
Frontend tests cover rendering, escaping, citations and saved/error states.
Phase 16 may now proceed; no Phase 17 work is included.
