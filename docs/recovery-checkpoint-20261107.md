# Interrupted work and USB recovery checkpoint - 7 November 2026

## Status at the overheating shutdown

Branch: `master-integration`. Previous checkpoint: `5675ae8`, tagged
`researchiq-security-workstream-1-source-20261105`.
This new checkpoint preserves interrupted work, **not completed Workstream 2**.
No existing application files were edited in this recovery session. Docker was not
started; no build, installation, migration, provider call or data cleanup was run.

Preserved changes:
- Preview request validation now bounds distinct positive document IDs and chunk /
  overlap settings (`backend/app/schemas/knowledge.py`). This schema change takes
  effect when the source is loaded; it has not passed its regression gate yet.
- New `preview_limits.py`, `preview_worker.py` and `bounded_preview.py` are unfinished
  parser-isolation scaffolding. The existing preview endpoint/service does **not**
  call the new worker. Do not claim F03 is fixed or deploy this as a completed fix.
- Security Audit Parts 1 and 2 are now included in the recovery commit, unchanged.
  A scoped scan found no configured secret values/private-key patterns in these
  documents or the pending source files. This is not a full historical secret audit.

Owner decision for continued Workstream 2: adjustable **capacity protection**, not
daily usage allowances or a maximum total number of documents per student. Implement
bounded concurrency/queues, request/file safety bounds and timeouts. Shared provider
spending policy remains an explicit launch decision. F02 is not implemented; F03
needs wiring, cancellation/resource-boundary tests and two-user authorization checks.
F19/F20 remain open. Workstream 1 host/grant/TLS/ingestion gates remain pending.

Next session: inspect this checkpoint, finish F03 and test before starting broader
admission controls. Review worker cancellation during subprocess startup, cleanup,
resource limits, preview fidelity and aggregate response bounds. Do not infer that
the earlier successful parser-library import probe was feature acceptance.

Recovery tag: `researchiq-workstream-2-interrupted-20261107`.
Only `git diff --check` and scoped secret checks were possible in this session;
backend/runtime tests were not run with Docker stopped.

## Copy these items, not only the source directory

1. The complete `C:\Users\tayya\Projects\ResearchIQ` folder, including hidden `.git`
   and the ignored `.env`, plus `uploads`. `.env` contains private credentials and
   the independent `AI_KEY_ENCRYPTION_KEY`; preserve the existing value to recover
   saved personal AI keys. Keep these secrets off Git/public repositories and protect
   the USB backup with encryption/access control.
2. **Docker data disk, outside Projects:**
   `C:\Users\tayya\AppData\Local\Docker\wsl\disk\docker_data.vhdx`.
   Observed size: **56,444,846,080 bytes (56.4 GB / about 52.6 GiB)**.
   This is the Docker Desktop WSL2 disk containing Docker images/container state
   and named-volume storage. Preserve the whole file while Docker is fully stopped.
   It is the recovery target for MySQL, MinIO, Chroma and the Hugging Face cache.
   This session did not mount the disk or verify its contents/database integrity.
3. Parent-folder plans: `ResearchIQ_Master_Integration_Plan.pdf`, its dated original,
   `ragrisearch final 4 prompt checklist` (PDF without extension), and
   `rAGRIsearch_Codex_Prompts_05_06.pdf`. Include other project assets you want retained.
4. Existing historical SQL backups in `.local/backups` and the repository root as
   secondary recovery copies. Latest observed SQL dump: 25 October 2026; root dumps
   are from 2 October. **They are not a current database backup** and contain neither
   current MinIO documents nor Chroma vectors. Keep them private and out of Git.
5. Small portable Git archive prepared beside the repository:
   `C:\Users\tayya\Projects\ResearchIQ-recovery-20261107.bundle`, with a SHA256 file.
   It preserves committed history/branches/tags, including this WIP checkpoint;
   it does **not** contain ignored `.env`, uploads, SQL dumps or Docker volumes.

The local Compose file declares `mysql_data`, `minio_data`, `chroma_data` and
`huggingface_cache`; the recovered installation historically uses `researchiq_*`
volume names. Exact current container mounts must be rechecked when Docker is safe
to start. `uploads` is a host bind mount and must be copied from the project folder.
Backing up images or Git alone does not capture these data stores.

## Observed host state and capacity

- Both `docker-desktop` and `Ubuntu` WSL distributions reported **Stopped**.
  No Docker Desktop/backend process was found during the check. Keep them stopped
  until the Docker disk copy finishes; checking once is not a guarantee they stay off.
- Installed Docker Desktop file version: `4.97.0.244584`.
- D: exFAT, about 31.0 GB free; E: FAT32, about 14.3 GB free at inspection.
  Neither has room for the 56.4 GB data disk. Use storage with more than 56.4 GB
  available **plus** space for the project and other backup items. FAT32 also cannot
  hold a single file this large. Do not format/delete the current USB contents here.
- No large file hashing, compression, Docker startup, exports or copying were started
  while the laptop is recovering and the user's existing copy is in progress.

## Finish the backup and restore safely

Let the current copy finish. Then copy the final checkpoint document and Git bundle
plus its SHA256 file explicitly; an already-running directory copy may miss new
files or capture `.git` midway through a commit. The verified bundle avoids relying
on that potentially inconsistent `.git` copy. Recopy `.git` only after Git operations
and the first folder copy have completed if also preserving a working-tree backup.

Copy the stopped Docker data disk to sufficiently large protected storage separately.
After the laptop is stable, compare source/destination SHA256 hashes using
`Get-FileHash -Algorithm SHA256 -LiteralPath <path>`; hashing 56 GB reads the entire
file, so it was deliberately not run now. Verify the bundle using
`git bundle verify <path-to-bundle>` from a Git repository. Safely eject only after
all writes complete. A copied file is not a verified restore.

Restore onto a compatible Windows/WSL2 Docker host, preferably matching Docker
Desktop initially. Preserve any existing target data first; do not overwrite an
unrelated Docker disk. With Docker Desktop stopped, follow Docker's documented
data-disk restore procedure, restore the project and private configuration, and
confirm bind-mount paths/project name before starting recovered services. The USB
is backup media: this is **not** a standalone executable application that runs merely
by plugging in the drive. Restore to local SSD storage and use Docker/WSL2.

Because the original shutdown was forced, this preserves crash-state evidence;
it does not certify MySQL/Chroma filesystem health. Keep the original disk and a
pristine backup. On a restore copy, verify MySQL startup/revision, object downloads,
vector retrieval, authentication, personal AI-key decryption and saved chats before
declaring recovery successful. Do not rebuild/pull floating images or reindex until
the recovered image/store compatibility is checked.

If later moving to Linux/ARM rather than compatible Windows Docker Desktop, prepare
coordinated logical MySQL backup, MinIO/Chroma volume exports, matching image/version
inventory and model cache backup once the laptop is safe to run Docker. Do not treat
a Windows Docker VHDX as a portable Linux/ARM Compose deployment.

Reference: [Docker Desktop backup and restore](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/),
checked 7 November 2026. Docker requires the VM to be fully stopped for disk backup;
restoring an image alone does not restore volume data.
