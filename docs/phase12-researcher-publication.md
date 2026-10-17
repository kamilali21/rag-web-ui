# Phase 12 — Researcher Portfolio and Publication Requests

Status: formally complete (17 October 2026). Implementation and synthetic live
acceptance completed on 16 October; the controlling Master Plan amendment was
appended and visually reviewed on 17 October. Phase 13 is now the current gate.

This is the Phase 12 insertion approved by the project owner. It preserves the
existing architecture and phase gates. The earlier planned Phases 12–21 become
Phases 13–22; completed phase numbers, commits, and historic tags are unchanged.
The dated original Master Integration Plan PDF remains unchanged at the Projects
root. The amended working copy is committed at
[`output/pdf/ResearchIQ_Master_Integration_Plan.pdf`](../output/pdf/ResearchIQ_Master_Integration_Plan.pdf)
and synchronized to the working PDF at the Projects root.

## Scope

- A one-to-one profile separate from authentication stores full name, active
  department, degree, and research area. Ag number, class, section, and a
  bounded PNG/JPEG/WebP photo are optional and private to the researcher and
  authorized corpus administrators.
- Profile editing shows publication submissions, processing state, decisions,
  reasons, and the researcher’s published papers. Photos are stored in MinIO,
  served only through authenticated, no-store routes, and rejected unless their
  bounded bytes have an allowed image signature.
- A researcher may submit one fully indexed private document at a time. Required
  catalog fields are title, authors, active department, and document type. Other
  existing academic metadata fields are optional. The submitter’s consent is
  stored per request; without it no researcher card is returned.
- Public Library admins receive a pending-count badge and a review queue. Review
  provides the requester’s full private profile and a request-scoped stream for
  only the exact attached private file. Generic admin access to private-library
  APIs remains denied. Admins may correct request metadata and approve or deny;
  denial requires a reason shown to the researcher.
- Approval reads the owner-checked private source, stages a separate copy in the
  system-managed public corpus, and reuses its existing ingestion/indexing
  lifecycle. The public copy becomes published only after processing and
  indexing succeed. The private original remains in its private KB.
- A researcher may ask to withdraw a published copy. Admin approval uses the
  existing archive lifecycle, hiding it from public catalog and retrieval while
  retaining its file, vectors, and request audit. Denial leaves it published and
  returns a reason. The user may cancel a pending submission; deleting its
  private source cancels the pending request while retaining its history.
- The limited public researcher card appears only on a consented published
  paper. It contains name, department, degree, research area, and photo only
  when that paper’s request consented. It never returns Ag number, class,
  section, username, email, or authentication fields. There is no researcher
  directory.

## Schema and API checkpoint

Alembic revision `riq_006` adds `researcher_profiles`, `publication_requests`,
and `withdrawal_requests`; `riq_005` remains the parent revision. Downgrade
refuses to drop any non-empty Phase 12 table. Request status and metadata are
stored as a separate snapshot so the original private academic data is not
changed. Deleting a private source nulls the source reference but retains its
request audit.

The API uses the established authenticated session, CSRF, current role and
allowlist checks. Review and approval also resolve the existing corpus-admin
authorization. Public copy ingestion and archiving reuse `public_corpus`; normal
private file read, retrieval, and deletion remain owner-scoped.

## Acceptance gates

Before Phase 12 closes, verify:

1. Profile owner checks, active-department validation, photo type/size/removal,
   limited public field projection, per-request consent, and exclusion of Ag
   number/class/section from every public response.
2. Private request ownership, ready-file eligibility, duplicate-active request
   prevention, metadata validation/editing, exact-document admin review, denial
   reasons, retryable failed indexing, and pending-count behavior.
3. A separate public document and vector set after approval, without changing or
   deleting the private original. Public catalog/retrieval visibility starts
   only after successful indexing.
4. Withdrawal approval archives the public copy and removes it from catalog and
   retrieval while retaining its file/vector state; denial leaves it published.
5. Backend regression tests, focused Phase 12 tests, disposable-MySQL migration
   and preservation tests, frontend tests, TypeScript checking, and production
   frontend build.
6. Synthetic live acceptance: reviewer sees only the requested paper; opted-in
   public fields and photo match the consent; PDF open/download, retrieval and
   cited chat continue to work; withdrawal removes public discovery; saved chats,
   existing users, private documents, and original RAG records remain unchanged.

All implementation, regression, migration, frontend, typecheck, build and
synthetic live acceptance gates passed. Live migration `riq_006` was applied
only after the disposable-MySQL gate passed and a verified backup was created.
The synthetic acceptance fixture was removed through the application lifecycle;
counts returned to the recorded baseline. Recovery snapshot:
`researchiq-phase12-recovery-20261016`. The amended plan formally closes Phase
12 and defines the Phase 13 summary gate.

## Verification receipt

- Backend: 331 passed, 41 skipped; Phase 12 cases are included.
- Disposable MySQL migration: 25 passed, including populated-baseline upgrade,
  downgrade guard and rollback verification.
- Frontend: 80 passed; `tsc --noEmit` passed; optimized production build passed.
- Live acceptance: profile/photo privacy, ownership checks, exact-document admin
  review, metadata correction, separate public indexing, retained private source,
  limited consented card, PDF open/download, retrieval, cited streaming,
  saved-chat reopen and withdrawal removal from catalog/content/card/retrieval.
- Live pre/post totals: 9 users, 6 knowledge bases, 11 documents, 193 chunks,
  7 chats, 56 messages. Phase 12 table counts returned to zero.
- Model selection: `openrouter/free` passed after the previously selected free
  model returned 404.
- Local deployment: backend Profile API is registered (unauthenticated request
  returns 401); frontend `/dashboard/profile` returns HTTP 200 and the container
  is healthy. No browser visual review was available.
- Follow-up UI polish: API Keys removed from dashboard navigation, Profile moved
  last, and Insights marked as a coming-soon sample preview. Two focused Jest
  suites pass (6 tests); the production build passes with existing ESLint-option
  and Tailwind line-clamp warnings.
- Backup: `.local/backups/researchiq-before-phase12-20261016.sql`; SHA-256
  `7CEE428002578BDFF308BB61BC4AFC6385EAD964BEB4B68A6AE61AEDD3ACD6D2`.
