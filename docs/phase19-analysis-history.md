# Phase 19 — Analysis Persistence and History — 27 October 2026

## Outcome and use

Open **Insights → Analysis history** to browse your summaries, comparisons,
research overviews, evidence interpretations and candidate research gaps. Filter
by workflow, status or source scope; page through results newest first. **Open**
shows the existing result view and stored evidence snapshots without another
retrieval or model call. The history URL can reopen a particular saved run.

New summaries from either Library are saved automatically. Their result includes
a **Reopen saved summary** link. Summaries generated before this phase were
temporary and cannot be reconstructed. Previous comparisons and analyses already
stored since Phase 15 appear in history without backfilling or regenerating them.

## Implementation

- Reuse `analysis_runs`, `analysis_documents` and `analysis_evidence`, introduced
  in Phase 15. No migration: database revision remains `riq_008`.
- Add authenticated `GET /api/insights/history` and `GET /api/insights/history/{id}`.
  Rows are owner-filtered, even for admins; filters are allowlisted and pages are
  limited to 20 by default, 50 maximum. Descending ID cursors avoid duplicate rows
  when a new run arrives between pages. Listing does not load result/evidence JSON.
- Share the existing source/readiness/publication/hash validation used by saved
  result reads. Unavailable entries retain only owner-private workflow/status/date
  information; titles, questions, documents and saved content are hidden. Direct
  reads are denied. All selected and related sources must remain accessible.
- History responses use `Cache-Control: no-store`; the UI also requests no-store.
  Results stay in component state, not browser persistent storage. Generated text
  and excerpts render as React text, never HTML.
- Extend summary generation with owner-private run lifecycle, source hash and exact
  SQL evidence snapshots, page/rank/score/hash, and final permission/evidence checks.
  Invalid output is never saved as a successful result. Provider failures produce
  a failed run without result/evidence. Optional UUID request IDs prevent duplicate
  generation on replay and reject reuse with changed options. Existing requests
  without an ID remain accepted; returned `run_id` is additive.
- Personal OpenRouter/OpenAI routing, citation validation and bounded generation
  retries remain unchanged. Reopening history does not require another provider
  call. Snapshots survive chunk/index rebuilds while source access remains valid.
- Reuse current result components, dialogs, buttons, theme colors and Library
  table spacing. Mobile rows stack compactly; dropdowns use explicit theme colors;
  keyboard focus returns to Open on dialog close. Processing reads poll at most
  60 times at five-second intervals and can be checked manually afterward.

This phase does not add history sharing, deletion, exports or a new RAG store.
It does not claim saved model interpretations are scientifically correct. Evidence
snapshots support inspection; retrieval scores are not scientific confidence.

## Verification

Completed on 27 October 2026:

- Generation regression: 149 tests passed; one explicitly opt-in live test skipped.
  Initial new-history fixtures omitted a required retrieval rank; corrected the
  fixture and reran the complete new suite (21 passed). Final combined history
  and personal-provider suite: 39 passed. No production behavior was weakened to
  satisfy tests.
- All 126 frontend tests passed; final expanded history suite: 11 passed,
  including all result views, keyboard focus, failure states and processing
  recovery. TypeScript checking passed after the final UI change.
- Production frontend build passed. Existing Tailwind plugin redundancy and
  ESLint option warnings remain; a clean lint result is not claimed.
- Live synthetic public/private PDF upload, processing/indexing, summaries,
  persisted quotations/pages, owner-only reads, pagination and request replay
  passed. Comparison regression passed in 30.01 seconds.
- Unpublishing the synthetic public source redacted its history metadata and
  denied both its saved summary and comparison. The private summary remained
  usable. Exact original SQL rows, MinIO objects and Chroma vector IDs matched
  after synthetic cleanup.
- Deployed backend source and frontend locally. Health, API/schema, anonymous
  rejection, served history JavaScript and responsive CSS checks passed. The
  browser tool returned no connected browsers; rendered desktop/mobile visual
  acceptance is not claimed.

Ignored receipts under `backend/.local/tmp/`: `phase19-focused.xml`,
`phase19-final.xml`, `phase19-personal.xml`, `phase19-live.log` and
`phase19-live-receipt.json`. No credentials, database dumps or test outputs are
included in the commit.

Recovery tag: `researchiq-phase19-history-20261027`.
Frontend image checkpoint: `researchiq-frontend:phase19-verified-20261027`.
Frontend image ID: `sha256:f178a10fc44a3e51aac2a0a0be9c7ffc83725ff2efc95f35dd9ebdda5ad20c20`.

Repeatable gates:

```sh
# In the isolated backend test image, without production services
python -m pytest tests/test_phase19_history.py tests/test_phase13_document_summary.py tests/test_phase15_comparison.py tests/test_phase16_research_analysis.py tests/test_phase17_evidence_interpretation.py tests/test_phase18_candidate_gaps.py -q
python -m pytest tests/test_personal_ai_settings.py tests/test_phase19_history.py -q

# Frontend test image / frontend directory
npm run test:ci -- --runInBand --silent
npx tsc --noEmit
docker compose build frontend

# Explicit synthetic-only local live gate, inside backend
PHASE19_LIVE_ACCEPTANCE=1 python -m tests.phase19_live_acceptance
```

## Recovery and next gate

Previous source tag: `researchiq-phase18-candidate-gaps-20261025`.
Previous frontend image: `researchiq-frontend:phase18-verified-20261025`.
Rollback source/frontend together if needed; retain additive summary records.
No database downgrade or object/vector restore is needed for this phase.
Historical tags remain unchanged. No push requested.

After this acceptance checkpoint, the next existing plan gate is **Phase 20 —
Cross-feature Security**: OTP abuse, RBAC bypass, private ID guessing, prompt
injection, upload abuse and sanitization. Phase 20 is not part of this session.
