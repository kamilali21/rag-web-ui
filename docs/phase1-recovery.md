# Phase 1 Checkpoints And Recovery

<!-- Added by ChatGPT: coordinated source/database recovery for the existing Docker deployment. -->

## Checkpoints

| Checkpoint | Source | Database |
| --- | --- | --- |
| `researchiq-frontend-checkpoint-20260915` | `09a9485`, preserved frontend redesign | Baseline; not a stability certification |
| `researchiq-phase0-verified-20260915` | `36a2330`, passing live RAG baseline | `3580c0dcd005` |
| `researchiq-citations-verified-20260916` | `fd4b997`, deployed and browser-verified citations | `3580c0dcd005` |
| Phase 1 schema implementation | `7cc9697`, tested additive migrations | Target `riq_003` |

The final `researchiq-phase1-verified-20260916` tag is created only after live acceptance passes.
All checkpoints are local. Neither the original `researchiq-development` branch nor its remote-tracking reference was moved. No changes were pushed.

## Backups

The final pre-migration MySQL backup is `.local/backups/pre-phase1-apply-20260916.sql` in the repository. The backup directory is mode 700 and the file is mode 600; both backups and local artifacts are ignored by Git. Both the earlier test backup and this final maintenance-window backup were restored successfully into isolated MySQL. All ten original tables in the final backup matched every original live column value after the post-migration smoke test. Use the final backup for recovery; the earlier clone predates chat activity during this session.

This is a database backup, not a complete service backup. Source tags do not include `.env`, credentials, MinIO objects or Chroma volumes. Phase 1 did not alter original objects/vectors. Before future ingestion/deletion changes, back up all persistent stores consistently. Do not publish SQL dumps: they contain private application data and password hashes.

## Return To The Citation Checkpoint

Run from the repository root during a maintenance window. First confirm the worktree is clean, preserve any subsequent work, take a fresh database backup, and make sure no document-processing jobs are active. These are recovery instructions, not commands to run during normal use.

1. Stop the API so it cannot write during schema reversal:

   ```sh
   docker compose stop backend
   ```

2. While the Phase 1 migration files are still present, reverse the additive schema using a one-off container:

   ```sh
   docker compose run --rm --no-deps backend alembic downgrade 3580c0dcd005
   ```

   Downgrades intentionally refuse to discard academic metadata, bookmarks, public KB state, auth records, OTP-only/system users, custom roles, departments or explicit admin-role assignments. If refused, do not bypass the guard or delete real data to force success. Export/transition that data or restore a reviewed backup into a separate database. Each revision has its own guard; a multi-revision downgrade may stop at an intermediate revision. Inspect `alembic current` before proceeding.

3. Only after downgrade succeeds, create a recovery branch without rewriting existing branches:

   ```sh
   git switch -c codex/recovery-phase1 researchiq-citations-verified-20260916
   docker compose up -d --no-deps backend
   docker compose exec -T nginx nginx -s reload
   ```

   The frontend is identical at the citation and Phase 1 checkpoints, so this particular rollback does not require a frontend rebuild. Returning to a different frontend tag does require `docker compose build frontend` and recreation of that service.

4. Wait for backend startup to finish, then verify `/api/openapi.json` through the normal URL and run `docker compose exec -T backend python -m tests.baseline_smoke`. Backend startup takes longer than the container's initial `Started` status. A smoke test started too early can receive a transient 502.

## Important Limits

- MySQL DDL auto-commits. An interrupted migration is not one automatically reversible transaction. Keep the API stopped until the actual schema and Alembic revision are reconciled.
- Do not import an old dump blindly over a newer schema. New tables can remain, and any work after the backup can be lost. Restore into isolated MySQL first, validate original ownership/data, then plan a controlled cutover.
- The disposable tests verify every original column value, defaults, FK/unique/check constraints, real FULLTEXT search, refusal guards and upgrade/downgrade/re-upgrade. They are opt-in and refuse a non-test host/database.
- Phase 1 does not activate OTP, RBAC, public catalog, system-owned corpus or Compare/Analyze APIs. Those require their own feature gates.
