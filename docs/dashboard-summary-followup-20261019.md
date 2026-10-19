# Dashboard and summary follow-up — 19 October 2026

## Scope

This is a focused follow-up to Phase 13, not a new phase or roadmap change.
Authentication, schema, publication approval rules, and persistent RAG data are unchanged.

## Dashboard

- Three compact cards: My papers, Publication requests, and Published. Small icons
  sit opposite tabular numeric counts; Published uses the existing emerald palette.
- Publication submission and admin review entry points move from Library to Dashboard.
  Researchers open the existing submission dialog; admins open the existing review
  panel. Admins can still submit their own papers using the secondary shortcut.
- Counts use owner-scoped APIs; only admins fetch the review queue count. A failed
  count displays an unavailable value rather than zero. Published excludes archived
  papers and approved withdrawals. My papers uses the catalog total instead of
  downloading all collections/documents. The chat shortcut and theme switch remain.
- The five most recent personal publication/withdrawal requests appear below the
  cards, linking to existing Profile management. No fabricated activity is shown.
- Cards use three columns on larger screens and compact stacked rows below 600px.
  Shared theme variables and visible keyboard focus remain in use.
- Library upload and Manage corpus remain; the existing publication deep link is
  retained for compatibility.

## Summary incident

The previous uncommitted summary hardening changes were preserved. A live repeat
on published document 70 reproduced HTTP 502: the provider returned a completed
JSON response with more than two key findings (`too_long:key_findings.claims`).
The correction attempt repeated the same presentation-limit failure.

The draft now accepts at most eight claims per section. All claims and citation
references are validated, including claims outside the display limit, before
returning the first two claims per section. The prompt still requests two concise
claims. This removes an unnecessary regeneration for otherwise valid output;
it does not accept fabricated citations or change exact-document permissions.

Post-fix checks on the same published paper both completed with five sections.
The warm request took 9.6 seconds; provider calls took about 8–10 seconds. The cold
check during concurrent build/test work took 123 seconds. These are observations,
not a latency guarantee. Model loading and free-provider variability remain.
No summaries, conversations, or database records were saved by these checks.

## Verification

- Summary regression: 23 passed; 1 opt-in synthetic provider test skipped. Live
  verification separately used the existing published paper without writing data.
- Frontend regression: 89 other tests passed; all 6 dashboard tests passed on
  rerun after correcting an asynchronous test assertion (95 tests total).
- Browser inventory returned no connected surfaces; rendered desktop/mobile
  visual acceptance remains unverified in this session.
- Previous frontend image preserved as `researchiq-frontend:pre-dashboard-20261019`.

- Standalone TypeScript check passed. Final production frontend image build
  passed; existing Next/ESLint option and Tailwind plugin warnings remain.
- Deployed the final frontend image and restarted the source-mounted backend;
  no backend image rebuild. Reloaded nginx. `/api/health` reports healthy;
  `/dashboard` and its updated JavaScript bundle return HTTP 200 through nginx.
  Verified the served bundle contains the new dashboard text.
- This follow-up was initially left uncommitted. It is now included in the
  user-requested Phase 14 commit/checkpoint `researchiq-phase14-insights-20261019`.
  The prior Phase 13 checkpoint remains unchanged; no push was requested.
