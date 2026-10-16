# ResearchIQ project status — 16 October 2026

This update preserves the 9 October historical report and its evidence. Phases
0–11 remain complete at their recorded checkpoints. The approved new Phase 12
is Researcher Portfolio and Publication Requests; the prior planned Phases
12–21 shift to 13–22. Completed phase numbering and historic tags remain as-is.

Phase 12 implementation and synthetic acceptance are complete; Phase 13 has not
started. It adds a separate researcher profile, private photo storage,
owner-scoped submission APIs, an admin request queue, request-scoped access to
the submitted document, separately ingested public copies, consent-limited
researcher cards, and archive-based withdrawals. The private-library owner
boundary and existing public corpus lifecycle remain intact.

Migration `riq_006` is live. Before applying it, the SQL database was backed up
to the ignored local file `.local/backups/researchiq-before-phase12-20261016.sql`
(SHA-256 `7CEE428002578BDFF308BB61BC4AFC6385EAD964BEB4B68A6AE61AEDD3ACD6D2`)
and restored into a disposable schema with matching baseline counts. The live
pre/post totals match: 9 users, 6 knowledge bases, 11 documents, 193 chunks,
7 chats, and 56 messages. Phase 12 table counts are zero after synthetic
fixture cleanup.

Verification: backend regression **331 passed / 41 skipped**; disposable MySQL
migration suite **25 passed**; frontend **80 passed**, TypeScript passed, and
production build passed. Synthetic live acceptance passed profile/photo privacy,
request ownership and exact-document review, separate public indexing, retained
private original, consented card, PDF open/download, retrieval, cited streaming,
saved-chat reopening, and approved withdrawal removal from discovery/retrieval.
Synthetic users, sessions, files, vectors, and messages were removed.

The pinned OpenRouter model returned HTTP 404 during the first chat acceptance.
The already-approved free-model router selection (`openrouter/free`) passed the
same cited-answer test. `.env` selects that router, and the refreshed backend
reports `openrouter/free` as its active model.

The Phase 12 backend and frontend are deployed locally. The backend serves the
Profile API (unauthenticated access returns 401); the frontend is healthy and
`/dashboard/profile` returns HTTP 200. A browser visual review was not available.
The dashboard now hides the API Keys navigation item, places Profile last, and
labels Insights as a coming-soon sample preview; corpus analysis is not connected.

The dated original Master Integration Plan PDF remains byte-identical. A
recovery snapshot is tagged `researchiq-phase12-recovery-20261016`; it preserves
the current implementation and the pre-staged dashboard-theme changes without
moving the branch or changing the real Git index. The working-copy PDF amendment
is still outstanding because the PDF skill's required authoring-marker script
is unavailable in this workspace. Phase 12 is not formally closed; do not start
Phase 13 until that amendment is completed.

See [phase12-researcher-publication.md](phase12-researcher-publication.md) for
the approved scope, privacy boundaries, API/schema notes, and acceptance gates.
The first task after the Phase 12 checkpoint is Phase 13: structured
single-document summary with citations, using existing exact-document retrieval.
