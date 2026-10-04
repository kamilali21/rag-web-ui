# Phase 8: Private Library

Started 4 October 2026 after frontend correction checkpoint `ed5a0ee`.
Authority: Master Integration Plan sections 8, 10 and phase table (pages 8,
9-10, 18). Phase 7 completion: `b6cdeab`, tag
`researchiq-phase7-verified-20261003`.

## Initial functionality mapping (superseded by final increment below)

| Requirement | Existing implementation | Remaining limit |
| --- | --- | --- |
| User-owned collections | `/api/knowledge-base`, `private_kb_filter`, `require_private_knowledge_base`; Library and collection pages | Preserve private scope/owner checks, including for admins. |
| Upload and processing | `DocumentUploadSteps`; existing upload/preview/process/tasks endpoints | Failed tasks without a document are visible only while their uploader is open; task IDs are required by the status endpoint. |
| Search/filter own documents | Private Library loads owner-scoped collections; filename, category and collection filtering | No bounded server-side document catalog; category buttons are explicitly filename shortcuts. |
| Processing state | Latest document task, polling while pending/processing | First increment adds processing-state filtering and uses the plan's Ready label for backend `completed`. No state is fabricated. |
| Query own collection | Existing Chat flow and retrieval test route with ownership checks | Later phases own Public/Private/Both and exact document retrieval. |
| Safe deletion | Existing whole-collection deletion | No per-document private deletion endpoint. Whole-KB cleanup currently commits despite external cleanup warnings; it is not proof of safe per-document deletion. |

Summarize, Compare and Analyze in section 8 describe final user capabilities;
their implementations remain in phases 11-15. Do not copy the mock Insights
workflow into Private Library or claim these later gates complete.

## First increment

Map existing document processing data into a Private Library state filter:
Pending, Processing, Ready (`completed`), Failed and Unknown. Combine with
current filename/category/collection filters; Clear resets search/category/state.
Reuse `documentStatus` to select the latest attempt. No schema, backend route,
storage, retrieval or authentication changes.

## First-increment acceptance and then-unfinished work

First increment: 23 Library/Public Library tests passed, TypeScript passed and
the production build passed. Deployed frontend image
`researchiq-frontend:phase8-status-20261004`; previous UI-only checkpoint image
`researchiq-frontend:rows-20261004` is retained. Six live HTTP checks passed
for two existing users (identity, owner-only catalog, foreign-KB denial).
Only temporary maintenance sessions were created and removed; research data
was not changed. Live bundle checks confirm both new filter controls are served.
Browser visual acceptance is pending until a supported browser is connected.
This increment does not close Phase 8 or authorize Phase 9.

The next unfinished Private Library lifecycle task is persistent visibility of
pending/failed uploads after the uploader closes, including tasks without a
document. Extend the existing owner-scoped task API and show its states; preserve
the ingestion pipeline. Then address exact-document deletion with cross-owner
denial and coordinated SQL/MinIO/Chroma failure/retry acceptance before closing
Phase 8. Server-side personal catalog filtering/pagination also remains open.

## Final increment - 4 October 2026

- Added bounded `/api/knowledge-base/catalog` SQL search, filename shortcuts,
  collection/state filters and pagination. Collection selection loads lightweight
  summaries; the original KB routes remain compatible.
- Catalog includes staged uploads and failed/pending tasks that have no document,
  survives closing/reopening the uploader, and polls active owner-scoped jobs.
- Added owner-only file viewing/download and exact document/upload deletion.
  Admin roles do not bypass private ownership. Active jobs block deletion.
- Deletion removes vectors and MinIO objects before SQL references. Failure keeps
  cleanup references, marks processing Failed, and permits retry; missing objects
  are safe to remove again. Whole-collection deletion no longer reports success
  after external cleanup failures. Chroma cleanup also matches legacy chunk IDs
  stored in vector metadata. Existing ingestion now persists partial-document
  links and chunk cleanup IDs before external vector writes.
- Duplicate processing submissions and conflicting filenames are rejected. No
  new ingestion service, storage layout, authentication behavior, or migration.
- Failed pre-document uploads can be removed and uploaded again. Automatic
  stopped-worker recovery and a durable job queue remain deployment work, as in
  the existing strategy. Summarize/Compare/Analyze remain their planned phases.

Validation receipts are stored outside Git under
`ResearchIQ-recovery/20261003-cleanup/phase8-*`. The pre-deploy SQL backup has
SHA256 `148742ece6c3b43d20eb1f27422a20984261feeff8d722f17ecd803f6a453a0e`.
The baseline code archive is `phase8-before-code.zip`; the preceding frontend
image `researchiq-frontend:phase8-status-20261004` is retained. Rollback uses
those code/image checkpoints; schema stays `riq_004` and volumes are retained.
Never restore an old SQL dump over later user work without reviewing changes.

## Completion gate

Phase 8 is COMPLETE on 4 October 2026. All initial remaining items above are
resolved by the final increment. Evidence: 194 backend regression passes,
12 final MySQL Phase 8 passes, 70 frontend passes, TypeScript and production
build. Live PDF upload/index/retrieve/cited-stream/saved-chat checks passed,
including exact cleanup and unchanged fingerprints for both original documents,
all original SQL records, MinIO objects and Chroma vectors. Schema: riq_004.

Image: researchiq-frontend:phase8-final-20261004 (manifest list
b00dc8186d84d1161b8f03b237256dc3289311376844dab8c39b811199260f86).
Visual browser inspection remains unavailable: the browser inventory is empty.
No claim of rendered-browser acceptance is made. Next gate is Phase 9.
