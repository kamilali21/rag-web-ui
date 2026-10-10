# Production preparation

This configuration preserves FastAPI, Next.js, MySQL, Chroma and MinIO behind
Nginx. It is **not activated** on the Windows installation. A domain, server,
valid certificates, verified SMTP and final acceptance are still required.
Do not merge this Compose file with `docker-compose.yml` or the dev override.

## Before choosing the host

Keep the current tested local installation and its checkpoint as rollback.
Prepare access-controlled backups of all three stores plus the embedding cache
and upload staging files. Restore consistent snapshots to explicitly named
volumes on the chosen host. Do not reuse old Linux volumes or start two active
application stacks against one restored database. No `prune`, `down -v` or volume
deletion is needed. The production file intentionally fails when its external
volumes are missing, rather than creating empty stores.

Review current dependency/container advisories before exposing the application;
see `docs/security-cleanup-20261009.md`. Internal Chroma is not an authorization
boundary. Only the application may access it, after SQL permission checks.

## Configure and verify

1. Build and test the source checkpoint. Tag images explicitly:
   `docker build -t researchiq-backend:<checkpoint> ./backend` and
   `docker build -t researchiq-frontend:<checkpoint> ./frontend`.
   Do not use development source mounts or floating `latest` application tags.
2. Copy `deploy/production.env.example` to root `.env.production` and replace
   every placeholder. Use the tested image tags, prepared volume names and a
   real DNS hostname. The backend receives that file at runtime; it is never
   included in build contexts. Keep independent random database/root, storage,
   JWT and OTP secrets. Preserve the MiniLM model used by the existing index.
3. Provision or rotate database/storage credentials on the target host. Merely
   changing MySQL environment variables **does not change users/passwords inside
   a restored MySQL volume**. Give the application a non-root database user;
   its startup Alembic path still needs schema migration permissions. Keep root
   credentials separate and backed up securely.
4. Set the domain's DNS records to the target host. Obtain a valid certificate
   through the hosting provider or your existing ACME client. Mount its full
   chain as `fullchain.pem` and private key as `privkey.pem` in `TLS_DIRECTORY`.
   Arrange automatic renewal and nginx reload using that certificate provider.
   No certificate issuance or DNS change was performed during this cleanup.
5. Configure real SMTP with STARTTLS/TLS and test email delivery. The production
   file enforces verified sessions, exact HTTPS origin and Secure cookies. Its
   dedicated nginx IP is the only trusted proxy. Pick a non-conflicting private
   subnet if the default conflicts with the hosting network.
6. Run `python deploy/preflight.py --env-file .env.production`. It reads resolved
   Compose configuration in memory, never prints secrets, and checks missing
   volumes/certificates, unsafe origins, placeholder credentials, source mounts
   and published internal ports. It does not certify DNS, certificate validity,
   provider availability, all software vulnerabilities or SMTP delivery.
7. On the target host only, after preflight and backups:
   `docker compose --env-file .env.production -f docker-compose.production.yml up -d`.
   For a differently named env file, also set `RESEARCHIQ_PRODUCTION_ENV` to its
   absolute path so runtime environment and Compose interpolation use the same file.

Only Nginx publishes host ports 80/443. Database, vectors, object storage,
backend and frontend have no published ports. Data services use a separate
internal network reachable by the backend, not the frontend or public proxy.
TLS is terminated at Nginx, which overwrites forwarded client headers.
Uvicorn leaves proxy headers untouched so
the existing application can validate the actual nginx peer. Storage/Chroma
image digests match the verified Windows versions; changing them needs its own
compatibility gate and backup.

## Final live gate

Verify HTTPS/redirect and wrong-host rejection, browser login/registration/email
verification/recovery/logout, Secure/HttpOnly session cookies, foreign-origin
CSRF denial, Private/Public Library ownership, upload/process/download, source
filters, streamed cited chat, saved reopening, admin publication/archive,
bookmark behavior, and API-key creation/use/revocation. Confirm internal ports
are unreachable externally. Check a backup/restore drill on disposable volumes.
Do not describe the site as publicly launched until this gate passes.

## Rollback

Retain previous application image tags and configuration. Roll back only the
affected application service without rebuilding or recreating data volumes.
Any new Alembic change requires its recorded migration rollback; this cleanup
introduces none. Never execute the historical root `reset-db.sql` as a production
deployment step. The Windows development configuration and its local HTTP origin
remain separate from this production file.

Configuration unit checks: `python -m unittest discover -s deploy -p 'test_*.py'`.
