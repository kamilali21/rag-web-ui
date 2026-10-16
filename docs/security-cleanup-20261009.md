# Security cleanup and deployment preparation — 9 October 2026

## Scope and preservation

Maintenance after Phase 11, not completion of Phase 19 or 21. Phase 12 remains
the next integration-plan feature. Authentication, roles, OTP/session flows,
schema (`riq_005`), retrieval permissions and the existing evidence/citation
protocol are preserved. No old Linux volume recovery or data cleanup is included.
Public hosting is not activated: the owner requested configuration now and a
domain/server later.

Plan sequence note (16 October 2026): at this report's date, the structured
summary was the next Phase 12 feature. The approved researcher portfolio
insertion occupies Phase 12 and moves the summary to Phase 13.

Migration checkpoint: `48761da`, tag `researchiq-windows-migration-20261009`.
Backend safety checkpoint: `f4eae3b`, tag `researchiq-backend-safety-20261009`.
The two SQL dumps remain ignored, local and untouched. Safe SQL inspection
helpers and a [recovery manifest](windows-migration-manifest.md) are committed.
The historical `reset-db.sql` is documented as destructive and was not run.

## Changes

- Bound private upload reads to the existing 100 MiB request limit, including
  cumulative multi-file size; reject oversized requests with 413.
- Reuse the public DOCX archive guard for private preview and processing:
  required document XML, at most 5,000 entries and 100 MiB expanded content.
- Redact private processing errors in new jobs and responses containing old
  records. Parser/provider strings are no longer exposed as task errors.
- Fix API-key deletion UI handling of a successful empty 204 response.
- Remove verified unreferenced DocumentList, its badge, unused theme wrapper,
  duplicate inactive stylesheet, unused imports and obsolete Next config flags.
- Remove unused frontend packages and the redundant npm lock. Docker uses the
  pinned pnpm version and its frozen lockfile as the single install path.
- Replace the `ai/react` re-export with its exact existing implementation,
  `@ai-sdk/react@1.2.9`. This removes the unused server/RSC SDK and jsondiffpatch
  dependency without upgrading the chat hook or changing the streaming protocol.
- Update the vulnerable Next.js 14 line to 15.5.27 with React 19.3.0 and matching
  types/testing support. Dynamic client pages use `useParams`, preserving routes.
- Move Docker build/runtime to Node 22 LTS; Node 20 is end-of-life according to
  the [official release table](https://nodejs.org/en/about/previous-releases).
  Pin compatible patched transitive releases for Markdown, CSS and build tools
  in pnpm overrides; the frozen lock preserves the audited versions.
- Exclude backend secrets, local receipts, dumps and caches from Docker context.
- Prepare localhost-only data ports in the Windows Compose file and a separate
  [production configuration](../deploy/README.md): HTTPS nginx, exact proxy trust,
  isolated internal data network, explicit external volumes, pinned data-service
  image digests, verified-auth settings and a secret-safe preflight command.

## Dependency findings and limits

The initial frontend production dependency audit reported 2 critical, 40 high,
26 moderate and 8 low entries. These counts include transitive/duplicate paths;
they are not a count of independently reachable application exploits. Removing
the unused shadcn CLI removes its install-time dependency tree. Next.js was
upgraded because its old release includes published remote-code-execution and
denial-of-service advisories, not simply to adopt a newer framework.

The final locked production dependency audit reports **0 critical, 1 high,
1 moderate and 1 low** entries. The residual high finding is `braces@3.0.3`
(no patched release in the retrieved advisory); the moderate finding is the
legacy PostCSS selector parser in the CSS/build toolchain. Their inputs are
repository-controlled build patterns/styles, not document uploads or chat
messages. The low finding concerns unbounded body reads in the retained AI
provider utility's JSON/error response handlers. These remain recorded rather
than suppressed from audit output.

Backend OSV package checks found residual advisories. This maintenance does not
claim zero vulnerabilities or replace a penetration test:

- Chroma advisories include collection authorization and model-loading issues
  (`GHSA-2wm9-hf6c-p5cr`, `GHSA-36p7-vc44-83pf`,
  `GHSA-f4j7-r4q5-qw2c`, `GHSA-xph7-9rjv-w5fr`). The retrieved advisories did not
  provide a fixed version. Do not expose Chroma directly. SQL permission checks
  and server-controlled embeddings remain the application's access boundary;
  production data services are isolated from the frontend and proxy.
- LangChain advisories cover legacy prompt loading, file-search middleware,
  HTML URL splitting and image token counting. Those affected APIs have no
  callers in `backend/app`. Moving to LangChain 1.x requires a separately tested
  provider/retrieval migration; it is not folded into an unused-code cleanup.
- `python-jose` DER-key algorithm confusion and `ecdsa` timing advisories remain
  in the dependency graph. The app fixes JWT verification to HS256 and production
  uses the existing opaque verified sessions, not attacker-supplied EC/DER keys.
- The unused AI server SDK and jsondiffpatch are removed. Remaining React-hook
  provider utilities are retained for protocol compatibility. Review the
  advisory's JSON/error response-handler reachability when extending the client
  or switching its stream protocol; this cleanup does not claim it is patched.
- Build-tool advisories and container OS packages need a refreshed scan when
  release images are built on the selected host. Backend dependency constraints
  remain broad; a fresh backend image must pass the regression/live gate before
  production use. The current runtime image is not proof of a future rebuild.

A tracked-file scan found no matches for the private-key/cloud-key formats
checked. This is a bounded scan, not proof that all historic secrets are absent.
Raw audit receipts and private live-check evidence stay outside tracked files.

References: [Next.js advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4),
[Next.js 15 compatibility](https://nextjs.org/docs/app/guides/upgrading/version-15),
[LangChain advisory](https://github.com/langchain-ai/langchain/security/advisories/GHSA-qh6h-p6c9-ff54),
[OSV advisory database](https://osv.dev/).

## Verification and release conditions

Completed backend/local checks:

- Full backend regression: **325 passed, 40 skipped**. A separate guarded
  MySQL gate supplements this run for database-specific behavior.
- Guarded MySQL authorization/library/chat gate: **172 passed**, using only
  `researchiq_phase2_test`; the application database was not migrated or reset.
- Production preflight unit checks: **2 passed**, including nine invalid
  configuration variants. Resolved synthetic Compose settings pass the guard;
  nginx TLS syntax passes with a temporary self-signed test certificate.
- Applied localhost-only data ports. Data-service image IDs and named mounts
  match the pre-change values; no volumes were deleted or replaced.
- Live greetings and saved reopening pass. A synthetic PDF uploads and indexes,
  but its initial cold-start wait exceeded the smoke script's 180-second limit;
  the resumed synthetic answer was uncited and failed that script's citation
  assertion. This is retained as a limitation, not counted as a passing RAG check.
- A separate known OneDrive question passes with two inline cited claims in
  10.84 seconds, valid source IDs and saved reopening. Temporary sessions/chats
  and the synthetic collection were removed through the normal lifecycle.
  Fingerprints confirm original SQL records, objects and vectors are preserved.
- No rendered-browser inspection is claimed by these API/asset checks.

Public launch still
requires domain/server selection, valid renewable TLS, credential provisioning,
SMTP delivery, tested release images, an isolated restore drill and the browser
acceptance checklist in `deploy/README.md`. No public launch is claimed.

## Frontend verification — 10 October 2026

- Built the production frontend as `researchiq-frontend:security-20261010`
  (image `3236e365d804`). The Next.js 15.5.27 build compiled all routes and
  completed successfully.
- Frontend Jest: **76 passed across 11 suites**. TypeScript check passed.
  OTP tests passed **13/13** after fixing an immediate cooldown display race;
  API endpoints, verification flow, validation, sessions and form submission
  behavior are unchanged.
- The build's embedded ESLint integration reports unsupported legacy options
  (`useEslintrc`, `extensions`) with this flat ESLint configuration. A direct
  lint audit also found existing source findings (23 errors and 15 warnings).
  These were not mass-edited because doing so would expand the cleanup into
  unrelated code changes. The build and explicit typecheck pass; lint is not
  claimed clean.
- The running Windows frontend remains on `researchiq-frontend:latest`
  (`chat-polish-20261009`). The verified security image was built but not
  promoted or activated; the live containers and data volumes were left alone.
  No integrated-browser visual inspection is claimed.
