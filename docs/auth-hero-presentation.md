# Public authentication hero — 7 October 2026

Presentation-only update to login, registration and their existing verification,
recovery and loading states. Included with the Phase 11 source checkpoint.

- Added a shared `AuthShell`: rAGRI search wordmark, research headline and capability
  chips, layered illustrative research papers, evidence/citation connector and the
  user-supplied UAF photograph at `frontend/public/uafbanner.jpg`.
- Reused the emerald/lime/ivory palette, typography, focus treatment and form
  controls. Styles are scoped in the existing `globals.css`.
- Desktop uses an approximately 55/45 hero/form split. Below 1024px the hero and
  form stack, the decorative paper scene is hidden, and a direct form anchor keeps
  account access reachable. No new dependency or authentication route was added.
- Subtle entrance, 6px floating cards, connector/glow and hover motion respect
  `prefers-reduced-motion`. Existing form labels, autocomplete, validation and ARIA
  behavior remain; headings use one page H1 with form H2s.
- The original form markup and component state/effect/handler blocks were compared
  against `da75deb` and matched. Authentication API calls, OTP/email verification,
  registration, password recovery, sessions and submission logic are unchanged.

## Verification and deployment

- 74 frontend tests across 10 suites passed, including 13 authentication checks.
- Production frontend build and explicit `pnpm exec tsc --noEmit` passed.
- Live `/login` and `/register` HTTP checks verified the hero, form panel,
  responsive/reduced-motion CSS and supplied photo. Its SHA-256 is
  `9B300A2A902A395A380773632C4D2BE95D222F0E8996CBBFC078C7E764A76F24`.
- Browser/native helper was unavailable: no rendered browser sign-off is claimed.
- Frontend image `researchiq-frontend:auth-hero-final-20261007`, also tagged
  `researchiq-frontend:phase11-20261007`, is deployed. Its image ID is
  `sha256:24595697120f2a0d5ff5b4b8104c23633d3a1df5b39354b61dc57425c753e491`.
- Previous frontend retained as `researchiq-frontend:before-auth-hero-20261007`.
  To reverse presentation deployment, retag that image as `researchiq-frontend`,
  recreate only frontend with `docker compose up -d --no-deps --no-build frontend`,
  then reload nginx. Preserve uncommitted changes before reversing source changes.
- Evidence: `ResearchIQ-recovery/20261003-cleanup/auth-hero-verification-20261007.json`
  outside Git. No backend or database changes were made for this visual update;
  Phase 11's separately documented backend API deployment follows it.
