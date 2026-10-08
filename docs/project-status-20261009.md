# ResearchIQ / rAGRI search — project status, 9 October 2026

This report follows `ResearchIQ_Master_Integration_Plan.pdf` (version 1.0,
15 September 2026), the repository and recorded acceptance evidence. It does
not replace the plan. The last completed feature phase is **Phase 11**. The next
formal task remains **Phase 12: structured single-document summary with citations**.

## This session

The interrupted corpus-chat correction was first committed as `ac5a04f`, tagged
`researchiq-chat-corpus-20261008`. This preserves the now-working model selection,
bounded query rewriting/provider requests and persistent embedding cache before
making the requested presentation changes.

New answers now request a JSON object containing short, separately cited blocks.
Each distinct factual sentence or closely related pair carries its own evidence
IDs. The server validates every block, then places its citation markers directly
after that block's text. This keeps the provider's working JSON mode while
avoiding one long paragraph followed by a pile of references. Unknown references,
extra fields, empty/oversized responses, mixed answer/abstention envelopes and
model-authored source links remain rejected. The whole envelope is validated
before its first claim is emitted, and permissions are rechecked before output.

The saved message and streaming formats are unchanged. Earlier single-block
responses remain compatible. Existing saved answers retain their original
citation placement; moving their references to particular sentences without
re-evaluating the evidence would invent a claim-to-source association.

The assistant avatar now uses an emerald open book and lime leaf, matching the
dashboard/authentication palette. It has an accessible name, explicit dimensions
and does not shrink in the message layout. The old RAG Web UI image is no longer
used by chat. No authentication behavior or frontend API logic changed.

Files changed for this increment:

- `backend/app/services/chat_service.py`: request separately supported claims.
- `backend/app/services/citations.py`: validate the bounded response envelope,
  reuse existing reference validation and retain the original response format.
- `backend/tests/test_phase10_assistant.py`: fragmented transport, citation
  placement, invalid envelope rejection and streamed/saved ordering regressions.
- `frontend/src/app/dashboard/chat/[id]/page.tsx`: branded, stable-size avatar.
- `frontend/public/ragri-assistant.svg`: native SVG book/leaf mark.
- Progress/report documentation. No dependency or schema migration was added.

## What has been implemented

These are historical phase acceptance results; they are not all new tests run
on 9 October. Refer to the phase documents and commits for exact gate details.

| Phase | Delivered behavior | Evidence |
| --- | --- | --- |
| 0 | Protected the original working upload → process → retrieve → cited answer → reopen baseline | `36a2330`, baseline repair `ad2429e`; live PDF acceptance |
| 1 | Schema foundation, reversible migrations and data preservation | `7cc9697`, `e6b0d58`; 46 backend tests and live post-migration RAG |
| 2 | Roles, server authorization and private ownership enforcement | `9f4aac7`; 49 SQLite/MySQL authorization checks |
| 3 | Password registration/login with one-time email verification, OTP recovery and revocable sessions, reflecting the approved authentication correction | `0860607`; 96 MySQL/40 frontend checks and user acceptance |
| 4 | Non-login system-owned public corpus and guarded lifecycle | `eee6c37`; 125 MySQL checks and live lifecycle acceptance |
| 5 | Academic metadata, validation and normalized departments | `6ee4063`; 168 MySQL/41 frontend checks |
| 6 | Public catalog, filters, pagination, bookmarks and source/PDF inspection | `c912772`; 192 MySQL/55 frontend checks, historical Linux responsive-browser acceptance |
| 7 | Admin ingestion, metadata, processing/retry, publication, archive and deletion | Recovery `6dd19cf`, completion `b6cdeab`; `researchiq-phase7-verified-20261003`; Windows API and user UI acceptance |
| 8 | Private library parity, status display and owner-only document lifecycle | `ad8960e`; `researchiq-phase8-verified-20261004`; 194 backend/12 focused MySQL/70 frontend checks and live PDF/chat lifecycle |
| 9 | Public/Private/Both retrieval constrained before vector search, with fresh SQL evidence checks | `1457dbd`; `researchiq-phase9-verified-20261005`; 220 backend/80 MySQL checks |
| 10 | Scoped Research Assistant, validated citations, streamed answers, saved conversations and source withdrawal handling | `903619e`; `researchiq-phase10-verified-20261006`; 113 MySQL/74 frontend checks and live scope/citation/reopen acceptance |
| 11 | Exact selected-document retrieval service and authenticated API | `1615a00`; `researchiq-phase11-verified-20261007`; 295 backend/99 MySQL checks and live exact-ID access tests |

Phase 0–6 checkpoint names mentioned in older documentation are not all present
as local tags after recovery. Their commits remain reachable. Phase 7–11 tags
listed above are present.

The Phase 11 checkpoint also includes the public login/register hero, research
paper composition, supplied UAF photograph and responsive/reduced-motion styling.
Its recorded validation is 74 frontend tests, TypeScript and production build,
plus live HTTP checks; form handlers, verification and session behavior were
preserved. There was no connected-browser visual sign-off in that checkpoint.

## Windows recovery and current architecture

ResearchIQ still extends the original FastAPI/MySQL/MinIO/Chroma/Next.js system;
the existing `/api` routes remain compatible. MySQL holds users, roles, sessions,
libraries, documents, metadata, chunks and conversations. MinIO holds files.
Chroma indexes permitted chunks, and retrieval reconstructs trusted evidence
from SQL rather than trusting vector-store metadata supplied in isolation.

The old MySQL data was restored after the Linux hardware failure. At the user's
later instruction, 14 proven-stale test documents and their dependents were
retired instead of recovering old Linux MinIO/Chroma volumes. The newly uploaded
working OneDrive document and protected account/schema state were preserved.
The user has since uploaded more documents; those historical cleanup counts are
not a statement of today's catalog size.

Chat failures had several distinct causes: greetings entering a citation-only
research prompt; missing embedding weights after container recreation; failed or
slow history rewriting; intermittent provider connectivity; and inconsistent
model output. The maintenance checkpoints addressed each observed failure:

- Complete greetings are authorized, saved and answered locally. A greeting
  followed by a research question still needs evidence.
- MiniLM is reused per worker and loaded locally first from a persistent cache.
  Its model, dimensions and original weight checksum did not change. Existing
  document objects and vectors were not recreated.
- Optional rewriting falls back to the original question after failure or its
  deadline. Provider timeouts/retries are bounded; errors remain visible.
- With approval, the runtime uses zero-cost
  `apodex/apodex-1.1-mini:free` through OpenRouter instead of a random free router.
  The provider supports JSON object mode; its advertised JSON Schema mode was
  tested and rejected, so it is not used. No paid credits were purchased.
- New structured blocks preserve that stable generation path while placing
  references beside their supported text.

The recovery maintenance gate passed 314 backend tests (40 environment-specific
skips), 118 disposable MySQL tests and real Public/Private/Both cited-answer and
saved-reopening checks. Details and retained failed probes are in
`docs/chat-reliability.md`. The local application remains at
`http://127.0.0.1.nip.io`, with schema revision `riq_005`.

## Requested analysis features and what is still unfinished

Ordinary chat already accepts natural-language questions, explanations and
summaries of retrieved evidence. That is not equivalent to a verified summary of
an entire selected paper, an exhaustive corpus review, or a structured analysis
workflow. Current retrieval supplies relevant excerpts; it does not establish
that every part of every document was examined.

The request to add full summary/abstract, Compare, Analyze and potential-gap
workflows was assessed but **not started in this increment**, following the
user's instruction not to leave a partially built task. Those capabilities span
multiple sequential phases and require more than changing a prompt:

| Next phase | Required outcome |
| --- | --- |
| 12 | Structured single-document summary with citations, using exact selected-document retrieval |
| 13 | Insights selection from real catalog data |
| 14 | Separate retrieval for each selected document, structured comparison JSON and a rendered table |
| 15 | Bounded multi-stage analysis with document profiles and related-document discovery |
| 16 | Supporting, contradicting and qualifying evidence relationships |
| 17 | Evidence-qualified candidate gaps within the indexed corpus |
| 18 | Analysis history experience |
| 19–21 | Cross-feature security testing, RAG quality evaluation and deployment/recovery hardening |

The present Insights screen is explicitly a sample workspace, not a completed
analysis service. It must not be presented as working summary/Compare/Analyze.

The exact first Phase 12 task is to connect the existing exact-document retrieval
service to a structured cited summary workflow. Current document access, scope
and readiness must be checked; selection must never silently broaden to the
library. The recorded plan correction also requires durable analysis-run/evidence
storage when the first real analysis workflow is built, before the later history
UI. Its tests, live acceptance and recovery checkpoint must pass before Phase 13.

## Security and reliability boundaries

This increment includes focused citation/access regression review, not a complete
vulnerability audit. SQL authorization, ownership, publication/readiness checks,
server-side session/CSRF protections and source rechecks remain in place.
Untrusted model metadata and unknown citations are rejected. The inspected answer
renderer does not enable raw HTML parsing.

Valid source identifiers do not automatically prove that a cited passage entails
every generated claim. Formal RAG quality evaluation remains Phase 20. A source
missing from the retrieved excerpts also cannot establish a novel gap in the
global literature; gap outputs must be qualified against the indexed corpus.
Free-provider rate limits, availability and occasional output failures remain
external constraints. Local HTTP is not production HTTPS, and the broader
security/deployment gates remain unfinished. No claim of “no hidden
vulnerabilities” is made.

## Final validation and checkpoint

- Full isolated backend: **322 passed, 40 environment-specific skips**.
- Disposable MySQL chat/Phase 9–11 gate: **126 passed**. Production database,
  schema and authentication settings were not changed by the test gate.
- Live Both-scope acceptance cloned current chat 31, answered the folder-backup
  and file-sharing question with five separately cited claims, and verified
  identical saved reopening. The temporary chat/session were removed; hashes
  confirmed all original research rows and conversations unchanged.
- That first live check took 100.59 seconds after backend restart while the full
  test suites and frontend build were also running. It is a cold-start/concurrent
  workload observation, not a claimed performance improvement or guarantee.
- A focused review found no material regression in the new citation parser's
  compatibility, bounds, reference checks or source-access rechecks.
- Frontend: **74 tests across 10 suites passed**, explicit TypeScript checking
  passed, and production build passed. Existing Next.js experimental-option and
  Docker ENV-format warnings remain; Jest reported the builder's duplicate
  standalone package name without test failures.
- The final warm live check took **16.09 seconds**, produced two separately cited
  claims and reopened identically. Temporary chat 44/session 154 were removed;
  original research/conversation fingerprints matched. These measurements do
  not guarantee future free-provider latency or availability.
- Deployed frontend image: `researchiq-frontend:chat-polish-20261009`, image ID
  `sha256:ed80e079db5f6572764919de871094f95d538d01fbe316692c7fc466a47ceb9f`.
  Live HTTP checks confirmed the chat bundle references the branded SVG, its
  served bytes match the source checksum, and the public auth hero remains.
  Backend health is 200; `riq_005`, OTP and the chosen model are unchanged.
- Browser integration was still unavailable; these are real HTTP, stream and
  asset checks, not a claim of rendered-browser visual acceptance.
- Checkpoint tag: **`researchiq-chat-polish-20261009`**, on `master-integration`.
  The separate pre-existing MinIO image change and SQL backup files were left
  outside this commit. No unrelated cleanup or next-phase code was introduced.
- Evidence/runners are retained outside Git under
  `ResearchIQ-recovery/20261003-cleanup/chat-inline-20261009/`,
  `chat-inline-warm-20261009/` and `chat-polish-deployment-20261009.json`.

To reverse this increment, preserve any later edits and revert only its source
commit, keeping the earlier `ac5a04f` reliability/cache fix. For frontend rollback,
the prior `researchiq-frontend:phase11-20261007` image remains available; retag it
as `researchiq-frontend`, recreate only frontend without rebuilding dependencies,
and reload nginx. Restart backend after a source rollback. No database rollback,
research-volume deletion, cache deletion or model change is required.
