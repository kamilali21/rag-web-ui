# rAGRI search frontend

Use Node 22 LTS and `pnpm@8.15.9`. Install with `pnpm install --frozen-lockfile`.
The committed `pnpm-lock.yaml` is the canonical dependency lock, matching both
Dockerfiles; do not generate a competing npm/yarn lockfile.

The app contains Public/Private Library, administrator ingestion, verified
sign-in and scoped cited chat. The emerald/lime/ivory design is defined in
`src/app/globals.css`, using the local Arial/Helvetica font stack. Insights is
still a sample workspace; see `../docs/implementation-progress.md` for gates.

Checks: `pnpm test:ci --runInBand`, `pnpm exec tsc --noEmit`, `pnpm build`.
Docker creates a standalone production server; see `../deploy/README.md` for
public deployment preparation. The working Windows app uses Nginx at
`http://127.0.0.1.nip.io`.

For an isolated development preview, set `RAG_NEXT_DIST_DIR=.next-preview` and
optionally `RAG_API_PROXY_URL` to the backend proxy, then run `pnpm dev`. Verified
session origin/cookie settings must match the preview origin; do not disable
CSRF or change production auth settings to accommodate a preview.
