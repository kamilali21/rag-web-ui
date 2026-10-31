# Cleanup and hosting review — 31 October 2026

Baseline: `408d408` on `master-integration`. This is maintenance within the
existing plan, not a replacement architecture or permission to delete research.
Phase 21's intermittent overview failure was still open at the start of review.

## What actually occupies space

Docker's detailed inventory reported the following. Image sizes share layers:
do **not** add displayed image sizes together to predict reclaimed disk space.

| Item | Observed size | Meaning / action |
| --- | ---: | --- |
| Active backend image | 18.3 GB, only 44.67 MB unique versus other images | Keep. Most bytes are shared with older backend images. Deleting an old 18 GB tag will not recover 18 GB. |
| NVIDIA / PyTorch / Triton installed directories | 3.2 / 1.2 / 0.897 GiB | Large ML dependencies. Do not manually uninstall from the running image; verify a CPU-only replacement image first. |
| Backend `/root/.cache` | 3.3 GiB | Embedded in image layers, not 3.3 GiB of new writable-container data. Removing it inside the container does not shrink existing image layers. Inspect and exclude disposable package caches when building its replacement; preserve model files. |
| Active frontend image | 354 MB, 116.6 MB unique | Keep. |
| Old frontend test/build images | Several images around 1.65 GB each | Removed six unused superseded images after current frontend verification; measured aggregate image storage reduction: 3.16 GB. Retained the currently used test image. |
| Two stopped frontend test containers | 782 MB + 326 MB writable layers | Not used by the running app. They also contain old `/work` source/config copies, not just caches. Export/compare those non-cache files before deleting the containers. |
| Build cache | **0 B** at this audit | Already cleaned since the previous session. No additional cache savings were available at the start. |
| Current named data volumes | MySQL 273.7 MB; Chroma 13.66 MB; MinIO 10.88 MB; embedding cache 91.58 MB | Keep all four. These are working data, not junk. |

Some stopped MySQL test containers still reference approximately 202 MB volumes.
Do not infer that an unnamed/unmounted volume is disposable. No volume prune,
system prune, Git clean, database cleanup or virtual-disk compaction is part of
this maintenance.

## Removed / simplified in source

- Removed seven assets with no tracked references: `file.svg`, `globe.svg`,
  `next.svg`, `vercel.svg`, `window.svg`, and the obsolete `logo.png` / `logo.svg`.
  The current `ragri-assistant.svg` and supplied `uafbanner.jpg` remain. Total
  removed: **138,173 bytes** (about 135 KiB); this is not a gigabyte-scale saving.
- Removed one unused test import and one unused test setup variable, identified
  by TypeScript's unused-local/parameter checks. The compiler reported no unused
  production locals/parameters. This does not prove every exported symbol is used.
- Merged duplicate `unstructured` requirements into `unstructured[md]>=0.10.30`.
  This preserves the previous combined version constraint and Markdown support;
  it does not remove the installed parser or change providers.
- Kept all dynamically selectable embedding/vector/LLM providers, routed pages,
  migrations and security tests. A hidden navigation entry is not evidence that
  its API or page is unused. No feature was removed to make the source look smaller.
- Ignored the four existing `*-safety-snapshot.txt` inventories by their exact
  root filenames. The files were left untouched. Resolved Compose configuration
  can contain secrets, so these snapshots must not enter a public Git commit.

## Logic inconsistency addressed

Structured generation already retried malformed JSON/schema output at most
once, but Research profiles validated selected document IDs, complete field
sets and per-paper citations only after leaving that retry loop. Consequently,
JSON with the correct shape but wrong evidence references failed immediately.

The shared generation helper now accepts an optional output validator. Research
profiles use their existing validator inside the **same maximum two model
attempts**, then still validate before use. JSON failures, throttling and evidence
failures share the budget; no nested retry or third profile attempt is introduced.
Permission/source-change errors are never converted into a model retry. No
invalid evidence is saved, and existing fresh source/ownership checks remain.

This can recover a transient invalid profile; it cannot guarantee that a free
provider always returns correct output. A second invalid response still fails
closed. No paid fallback, new model, schema migration or authentication change.

## Docker cleanup and rollback-image retention

There is no honest claim that deleting a rollback image has *zero* effect: it
does not change the running application, but it removes that immediate rollback
option. Git tags preserve source, not the exact resolved dependencies in an image.

Preserved, including this recommended minimum retention:

- Active `researchiq-backend:latest` and `researchiq-frontend:latest`.
- Most recent verified frontend images: `phase20-verified-20261029` and
  `phase19-verified-20261027`.
- Backend `pre-phase20-20261029`: it has almost no unique size (13.04 kB in
  the inventory), so deleting it sacrifices rollback for negligible savings.
- `researchiq-dashboard-check:20261019`, used by current frontend verification.
- Active MySQL, Chroma, MinIO and nginx images; all data volumes and backups.

Removed the following six superseded test/build images after the current frontend
tests, strict type check and production build passed. The cleanup verified exact
image identities, checked every running/stopped container reference, and refused
protected/in-use images. No `--force` or blanket prune was used. These old test
environments are no longer available; production rollback images remain.

| Exact image tag | Current unique size estimate | Runtime effect |
| --- | ---: | --- |
| `researchiq-frontend-phase13-check:latest` | 356 MB | None; loses old Phase 13 test image |
| `researchiq-frontend-check:phase12` | 356.8 MB | None; loses old Phase 12 test image |
| `researchiq-phase12-builder-final-20261016:latest` | 361.1 MB | None; loses old builder |
| `researchiq-phase12-builder:20261016` | 356.9 MB | None; loses old builder |
| `researchiq-frontend-builder:security-20261010` | 350.1 MB | None; loses old builder |
| `researchiq-frontend-builder:security-20261009` | 1.383 GB | None; loses old builder |

Docker reported aggregate image storage **29.75 GB before, 26.59 GB after**:
approximately **3.16 GB reclaimed inside Docker**, with image count falling
from 45 to 39. This is not six times the images' displayed total sizes. Local
receipt: `.local/tmp/obsolete-build-images-result-20261031.json`. Windows host
free-space growth was not independently measured; no virtual-disk compaction
was attempted.

Frontend production rollback images older than Phase 19 are a further optional
candidate, typically only 33–117 MB unique each. They remain untouched: removing
them sacrifices older instant rollback. The old security-cache images also
remain until their cached content and replacement dependencies are confirmed.

The two stopped frontend containers are a separate potential **1.108 GB** saving
after preserving their non-cache `/work` files. Never start their old commands
just to clean them, and never use `docker rm -v` for this task.

The biggest future reduction is a **fresh, tested CPU-only backend image** without
embedded package caches and unnecessary build tools. Current dependency resolution
is broad and current images are AMD64, so this is a build/migration task with
embedding-equivalence and RAG acceptance checks, not a safe live-file deletion.

## Can the whole app run on free hosting?

The closest fit is one Linux VM running the existing six-service Compose stack,
not six unrelated free services. Oracle currently documents an Always Free A1
allowance equivalent to **2 ARM OCPUs / 12 GB RAM**, with **200 GB total block
storage** across boot/data volumes. Capacity can be unavailable and idle instances
may be reclaimed. This is a candidate for a small pilot, not guaranteed free
production hosting. Verify the account's actual free limits before provisioning.
[Oracle Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

For that option, first verify/build ARM-compatible images and Python dependencies;
do not simply move the existing AMD64 images. Then use the existing production
Compose, private data network, one HTTPS origin, tested data restoration and
off-host backups. Close Phase 21 and Phase 22's security/restore gates before
opening access. No Oracle account, server, domain or paid resource was created.

Render Free lacks persistent disks, sleeps when idle, and blocks standard SMTP
ports. That conflicts with this app's current storage and email-OTP setup.
[Render Free limitations](https://render.com/docs/free)

Railway Free currently provides only 0.5 GB RAM per service, three services after
the trial, 0.5 GB volume storage and $1 monthly resource credit. That does not fit
this six-service stack and its local embedding process as-is.
[Railway pricing](https://railway.com/pricing)

Vercel can host frontend/container workloads, but is not a single free drop-in
host for the current persistent Compose deployment; external durable stores and
processing/session-routing checks would still be necessary.
[Vercel container guidance](https://vercel.com/kb/guide/docker-on-vercel-vs-render)

Hosting also does not make model inference, email delivery, domain registration
or backup storage automatically free. User-supplied AI keys shift inference
charges to their owners; free models retain quota and reliability limits.

## Verification

- Focused profile retry tests: **13 passed**. Full backend regression:
  **610 passed, 44 opt-in skipped**; no schema change. Receipts:
  `backend/.local/tmp/cleanup-focused-20261031.xml` and
  `backend/.local/tmp/cleanup-regression-20261031.xml`.
- Frontend: **133 passed**; TypeScript including unused-local/parameter checks
  and production build passed. The pre-existing ESLint invalid-options error
  and redundant Tailwind plugin warning remain; a clean lint pass is not claimed.
  The disposable test image's package manifest and lockfile match
  this checkout byte-for-byte.
- Docker initially disconnected during verification and returned engine errors.
  A normal Docker Desktop restart recovered it; existing Compose services were
  started without rebuilding, resetting or deleting their data. The successful
  regression run above supersedes the interrupted attempts, which did not
  produce completed test results. All six app services were running afterward.
- The backend fix is loaded through the existing source mount. Unreferenced
  frontend asset removal is a source change; the running production frontend
  was not rebuilt solely to remove those unused assets.
- Live synthetic evaluation: **12/13 cases passed**, plus comparison (26.82s),
  saved reopening/replay/revocation and exact original SQL/MinIO/vector cleanup.
  Overview now passed (12.76s); contradiction interpretation returned an HTTP
  error after generation (24.98s). The harness correctly exited nonzero. No
  validation was weakened and no failed run was called a completed phase.
  Chat, both summaries and candidate gaps passed; manual review of their claims
  and the overview matched the synthetic facts and limitations. Phase 21 remains
  open pending interpretation diagnosis and a complete quality gate.
- Previous evaluation receipts were preserved as `*-pre-cleanup-20261031.json`
  before the new run. Current receipts are `backend/.local/tmp/phase21-*.json`.
  No public deployment, migration, provider change or Git push was performed.
- Maintenance checkpoint: `researchiq-maintenance-checkpoint-20261031`.
  This is not a Phase 21 completion tag.
