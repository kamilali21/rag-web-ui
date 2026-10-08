# Windows recovery files — 9 October 2026

The user approved committing the recovery helpers and manifest while keeping
database dumps local. No SQL script or restoration was executed for this commit.

| Tracked file | Purpose |
| --- | --- |
| `check-users.sql` | Read-only counts of users and role assignments |
| `verify.sql` | Read-only table listing |
| `reset-db.sql` | Historical, destructive manual development reset; **never run against the restored application database** |
| `docker-compose.yml` | Records the recovered Windows MinIO image selection (`cgr.dev/chainguard/minio:latest`) |

`reset-db.sql` is retained as recovery history, not an Alembic migration or an
automatic deployment step. The application schema remains managed by Alembic;
revision `riq_005` is unchanged. Committing that file does not authorize executing it.

The following originals are preserved in the repository directory but explicitly
ignored by Git. They contain sensitive application records, password hashes and,
in the Linux backup, API keys and conversation contents. Do not publish them or
copy them into a container image.

| Local backup | Bytes | SHA-256 |
| --- | ---: | --- |
| `researchiq-mysql-backup.sql` | 1200678 | `e717fb1f033403312c98655af1240519c190ae07ab3f198dd09137040a84f0af` |
| `windows-before-restore.sql` | 27433 | `3e7000ef94052069da617f5b0a01821baac1f388bbaab8c67f29268ecbc9f356` |

These checksums identify existing evidence; the dumps were not edited, sanitized,
restored or deleted. Keep an access-controlled off-device backup separately from
the source repository. The audit did not inspect or rewrite Git history.

The MinIO image change records an existing running-environment choice. Production
configuration pins the verified running image by digest; no MinIO/Chroma upgrade
or raw database-volume migration is part of this cleanup.
