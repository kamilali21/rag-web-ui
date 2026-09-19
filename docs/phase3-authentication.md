# Phase 3: Email OTP And Sessions

<!-- Added by ChatGPT: activation, verification and recovery without modifying secrets or data volumes. -->

## Scope And Rollout

Phase 3 reuses the Phase 1 authentication tables at `riq_003`; no migration is
needed. Public corpus, OTP-based admin provisioning and later features are not
included. University email and allowlisting alone never grant admin. Existing
explicit roles plus current allowlisting still control admin access; private
research stays owner-only.

`EMAIL_OTP_ENABLED=false` is the default rollout state. It retains existing
password/JWT login while SMTP is being configured. Setting it to `true` disables
password registration, password token issuance, and browser JWT authentication.
There is no automatic fallback if email or session configuration fails. Existing
API keys continue to use the separate, ownership-checked API-key endpoints.

The tested code checkpoint is `researchiq-phase3-tested-20260919`; test commands
and results are recorded in `implementation-progress.md`. On 19 September 2026,
the user explicitly approved local activation: OTP is now enabled, the frontend
is deployed, and Brevo accepted a real OTP request to the confirmed test inbox.
Actual inbox receipt and deployed browser/session/RAG acceptance still need
confirmation before declaring Phase 3 complete. The existing URL is unchanged;
no temporary preview server was created.

## Brevo Configuration

Use Brevo's **SMTP login and SMTP key**, not an API key or account password.
Verify the sender/domain and transactional sending access in your Brevo account.
Official references:
[SMTP setup](https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP),
[SMTP keys](https://help.brevo.com/hc/en-us/articles/7959631848850-Create-and-manage-your-SMTP-keys).

Configure the following locally in the existing root `.env`. Placeholders below
are not working credentials; do not commit actual values or paste them in chat.

```dotenv
EMAIL_OTP_ENABLED=false
AUTH_OTP_SECRET=<independent-random-secret-at-least-32-characters>
AUTH_ORIGIN=http://127.0.0.1.nip.io
AUTH_ALLOW_LOCAL_HTTP=true
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=<Brevo-SMTP-login>
SMTP_PASSWORD=<Brevo-SMTP-key>
SMTP_FROM_EMAIL=<your-verified-sender-email>
```

Keep the flag false during preparation. Set it true only for the explicitly
approved activation/verification window once SMTP and local configuration are ready.

Generate the OTP HMAC secret locally using a cryptographically secure generator;
for example, `openssl rand -hex 32`. It must be independent of the legacy JWT
secret. Rotation invalidates outstanding codes and resets hashed rate-limit
identities, but does not revoke existing sessions. Never rotate it per request.

The user-approved local exception accepts HTTP only for `localhost`, `127.0.0.1`,
`::1`, or `127.0.0.1.nip.io`. It uses distinct `researchiq_local_*` cookies and
does not make HTTP production-safe. Use exactly the configured URL for login,
including any port, with no trailing slash. Do not expose local HTTP mode to
other machines or use a public hostname.

For production use an HTTPS origin and `AUTH_ALLOW_LOCAL_HTTP=false`. Cookies
are host-only `__Host-researchiq_session` (HttpOnly) and
`__Host-researchiq_csrf` (JavaScript-readable), both Secure, SameSite=Lax, path `/`.
SMTP is always TLS with certificate verification, even in local HTTP mode.
Port 465 can use `SMTP_SECURITY=ssl`; no plaintext SMTP fallback exists.

## Proxy And Limits

Nginx already overwrites `X-Real-IP`. Set `AUTH_TRUSTED_PROXIES` to a JSON list of
the actual trusted Nginx peer IP/CIDR as seen by the backend, for example
`["172.20.0.7/32"]` only if that is the actual peer. Do not copy this example
blindly or trust `0.0.0.0/0`. Restrict backend network access to the proxy.
Recheck the peer after container recreation. Unconfigured/untrusted forwarded
headers are ignored; callers behind the proxy then share its IP rate bucket.

Defaults:

- Six-digit codes, five-minute expiry, five attempts, 60-second resend cooldown.
- Send: five attempts per normalized email and 30 per client IP per 15 minutes.
- Verify: 20 attempts per normalized email and 60 per client IP per 15 minutes.
- Limits include failed attempts and sends; rate-limit errors include Retry-After.
- SQL row locks serialize workers; resends invalidate previous challenges.
- IP-throttled requests do not allocate additional per-email limit rows. MySQL
  whole-second cooldown storage and simultaneous signup are regression-tested.
- SMTP runs outside locks. Pending/failed deliveries cannot authenticate.
- HMAC hashes protect low-entropy codes at rest; session and bound CSRF tokens
  have 256 bits of randomness and only SHA-256 hashes are stored.
- Eight-hour fixed sessions. New login rotates this browser's prior session;
  other devices remain signed in. Logout revokes the presented session in SQL.
- Every cookie-authenticated mutation requires exact Origin and a session-bound
  X-CSRF-Token header. Anonymous login POSTs also check exact Origin.

Optional tuning is bounded in `Settings`: OTP expiry 300-600 seconds, attempts
1-10, resend 30-300 seconds, sessions 300-86400 seconds, SMTP timeout 1-30 seconds.
Changing defaults requires corresponding abuse/UX testing.

## Activation Gate

1. Keep a known working source checkpoint and existing backups. Verify Brevo
   settings and the exact origin locally. Audit existing account-email mappings
   and API-key owners before trusting migration from previously unverified
   password registrations; revoke/rotate any untrusted legacy credentials through
   an approved maintenance procedure. Never run `docker compose down -v`.
2. Build the frontend and recreate **only** backend/frontend to load configuration
   and code. Nginx upstream resolution may need its normal reload after changed
   container IPs. Do not recreate databases, alter volumes, or rebuild vectors.
3. Confirm `/api/auth/methods` returns `email_otp: true`. Request a code for an
   inbox you control, check actual receipt, sign in, and confirm `/api/auth/me`.
4. Check resend cooldown, previous-code rejection, logout, refresh-after-logout,
   and browser cookie flags. Verify legacy passwords/JWTs are rejected.
5. Confirm existing account/roles and document ownership are unchanged. Test
   private Library, upload, retrieval, a cited streamed answer and saved chat.
   Use a synthetic fixture, not someone else's private research.
6. Record successful inbox delivery and deployed acceptance in
   `implementation-progress.md`. Until then the gate remains pending. Do not
   begin Phase 4.

The existing `tests.baseline_smoke` uses password signup and cannot run unchanged
after OTP activation. Use the browser for the live email/RAG acceptance gate;
isolated tests cover the actual cookie-authenticated chat endpoint and RAG service
with deterministic external-provider fixtures.

## Housekeeping

Expiration is enforced independently of deletion. Run
`python -m app.services.auth_cleanup` periodically in the configured backend to
remove at most 1,000 records per auth table per run, expired over 24 hours ago.
The expiry indexes bound candidate selection. Refreshed limit rows are rechecked
before deletion. This command was tested only on disposable records; no production
cleanup or scheduler was installed. Monitor table growth and sending quotas before
public deployment. Counts contain no email addresses, codes or session secrets.

## Recovery

Pre-Phase-3 source checkpoint: `researchiq-phase2-tested-20260916` (`9f4aac7`).
No schema downgrade or data deletion is needed for code rollback. Preserve the
user's unrelated citation edits before switching source. Keep the Chroma `/data`
volume fix and the existing `.env`/data.

Disabling OTP is a deliberate maintenance action that **re-enables legacy JWTs
and passwords**, including unexpired previously issued JWTs. Do not use it as an
automatic delivery-error fallback. OTP-created accounts have no password and
cannot use legacy login. Prefer fixing SMTP configuration with OTP still enabled.
If rollback is necessary, assess exposure, communicate the login change, and
invalidate legacy credentials/sessions through an approved recovery procedure.
Successful legacy password login clears stale OTP cookies so they cannot shadow
the new browser JWT. Clearing browser cookies does not revoke other devices.
