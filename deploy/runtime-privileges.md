# Workstream 1: operator-reviewed runtime privilege preparation

Status: **prepared, not executed**. No live user, password, grant, bucket, volume or
schema has been changed. Review on the target host before rollout. Never run this
against the only recovered copy. Keep access-controlled backups and existing images.

## MySQL

Create two independent accounts restricted to the target Docker network (choose
their permitted host with the operator; do not assume `%` is necessary). Configure
`MYSQL_USER`/`MYSQL_PASSWORD` with the runtime account. The database container now
receives only its database name and bootstrap root password; its entrypoint must
not auto-create the runtime account with schema-wide ALL privileges.

The runtime account needs only SELECT, INSERT, UPDATE, DELETE on the application's
database, including `alembic_version`. The separate migration account needs those
plus CREATE, ALTER, DROP, INDEX, REFERENCES on that database for current migrations.
Neither needs global privileges, GRANT OPTION, FILE, PROCESS or SYSTEM_USER. Review
future migrations for additional needs rather than granting ALL preemptively.
Existing accounts can inherit broader privileges through roles; inspect both direct
and effective role grants. Do not merely add narrower grants to a broad account.

Provision through a protected DBA session with passwords entered securely, not in
command-line arguments, shell history, reports or checked-in SQL. Before runtime
startup, use the tested backend image for a **one-off** `alembic upgrade head` with
the migration identity supplied through an access-controlled temporary env file
outside Git/build contexts. Keep all other production validation settings secure
and `RUN_STARTUP_MIGRATIONS=false`; that flag disables automatic app startup DDL,
not explicit Alembic commands. Run on the isolated data network without host ports.
Stop/remove that one-off container and protected env file after success. Do not add
migration credentials to the backend service, shared runtime environment or image.
This is a future authorized operation, not a command to execute during remediation.

Verify on disposable data: schema-at-head startup succeeds using DML-only credentials;
an outdated revision refuses startup without modification; runtime CRUD works;
runtime CREATE/ALTER/DROP, another database and grant changes are denied. Review
`SHOW GRANTS FOR CURRENT_USER` privately; do not publish hashes or raw grant output.

## MinIO

Use separate `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` for bootstrap administration.
Pre-create the configured bucket. Create a distinct runtime identity with only the
policy below (replace the sample bucket with the configured name). Do not attach
consoleAdmin, readwrite-all-buckets or additional inherited policies. Backend
`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` belong to this limited identity, never root.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:ListBucketMultipartUploads"],
      "Resource": ["arn:aws:s3:::documents"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
      "Resource": ["arn:aws:s3:::documents/*"]
    }
  ]
}
```

Verify with a harmless synthetic object: bucket-existence check, upload including
multipart, read/download and delete succeed. Bucket creation/deletion, policy/user
administration and unrelated-bucket access must fail. Inspect that there are no
anonymous/public bucket policies. These are capability tests still pending operator
approval; source configuration cannot prove effective server-side permissions.

## Non-root storage and isolation acceptance

On **separate restored target volumes**, make only upload staging and the HF cache
writable by UID/GID 10001. Preserve cache contents/model/index compatibility. Do not
recursively change live production or Windows data ownership. A missing writable
cache may trigger a model download; verify the existing embedding cache offline first.
Verify UID 10001, empty effective capabilities, no-new-privileges and read-only root
filesystem in the built container, then synthetic PDF ingestion, retrieval, profile
photo handling and cleanup within the 256 MiB temporary mount. A failed temp/cache
check blocks rollout; never compensate by restoring root or broadly writable source.

Only the backend and data services join the internal data network. Frontend/Nginx
must not join it. Chroma has no application-level service authentication here: network
isolation is a mitigation, not proof of immunity to a compromised trusted container.
With authorized staging checks, verify host/cloud firewall and external IPv4/IPv6
denial of MySQL, Chroma, MinIO and application ports; only Nginx 80/443 is exposed.
Verify public HTTPS, exact-host handling, Secure/HttpOnly cookies, foreign-origin
CSRF denial and browser sessions; do not reuse tunnel-origin rewriting in production.

Rollback: retain the old images/configuration and consistent backups. Do not delete
volumes or widen runtime grants to work around failures. Rolling back to a pre-F01
backend can re-enable legacy application keys, so keep public exposure disabled
until the retirement fix is present in the chosen rollback image.
