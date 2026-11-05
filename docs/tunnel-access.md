# HTTPS development-tunnel sign-in

The local Docker deployment can be accessed using the configured HTTPS tunnel
from another device. This is development access, not completion of production
deployment hardening. Keep the tunnel's own access controls enabled.

## Configuration

Set local `.env` (never commit credentials):

```dotenv
AUTH_ORIGIN=https://zxcpn3pm-80.inc1.devtunnels.ms
AUTH_ALLOW_LOCAL_HTTP=true
AUTH_LOCAL_ORIGIN=http://127.0.0.1.nip.io
```

Do not append a trailing slash to either origin. Use the HTTPS URL on other
devices and `http://127.0.0.1.nip.io` on the host laptop. The additional origin is
optional and accepts only explicit loopback HTTP origins while local HTTP is
enabled; it does not allow arbitrary LAN/public HTTP origins. Disable it for
production. The tunnel keeps Secure, host-only cookies; the laptop uses separate
local-development cookie names. Both session cookies are HttpOnly, with CSRF checks.

VS Code Dev Tunnels was observed forwarding the browser's origin as
`http://localhost:80`, Host as `localhost`, forwarded host as the exact tunnel
hostname, and forwarded protocol as `https`. Merely changing `AUTH_ORIGIN` was
therefore insufficient.

The development `nginx.conf` restores the configured HTTPS origin only when all
those values match and `Sec-Fetch-Site` is `same-origin`. Every other Origin is
passed through unchanged to the backend's exact-origin check. Missing/null origins,
other tunnel hosts, and cross-site/same-site fetch metadata do not match the rule.
Forwarded headers are not authentication: session, permission and CSRF checks
remain mandatory. Do not replace this rule with an unconditional Origin rewrite,
wildcard tunnel allowlist, or a general trust of forwarded headers.

When the tunnel address changes, update both `AUTH_ORIGIN` and the exact hostname/
HTTPS origin in the Nginx map. To preserve the original Origin instead, configure
the tunnel host accordingly and remove the normalization rule. Microsoft describes
the rewrite and preservation option in
[Dev Tunnels issue 284](https://github.com/microsoft/dev-tunnels/issues/284).

Apply environment changes without rebuilding images:

```powershell
docker compose -f docker-compose.yml up -d --no-deps --no-build backend
docker exec researchiq-nginx-1 nginx -t
# Run the reload only if the configuration test passed.
docker exec researchiq-nginx-1 nginx -s reload
```

For Nginx-only edits, just validate and reload Nginx. The production Nginx template
is unchanged and does not include this development-tunnel exception.

## Verification on 31 October 2026

- Captured the failed mobile request's origin/host headers only; no credentials,
  cookies, or request bodies were recorded. Temporary diagnostic logging removed.
- Nginx configuration validation passed; configuration reloaded.
- Eleven credential-free POST `/api/auth/logout` checks through local Nginx:
  exact observed rewrite and original configured HTTPS origin returned 200;
  cross-site, same-site, unrelated origin/host, different tunnel, HTTP forwarding,
  missing fetch metadata, missing origin, and null origin returned 403.
- Backend health and secure-cookie configuration passed. No test sessions created.
- These proxy checks simulate tunnel headers. The tunnel's access-control gate
  rejected an unauthenticated external probe; actual mobile sign-in requires the
  user's tunnel-authenticated browser.
- User confirmed mobile sign-in succeeded and the dashboard opened after the
  Nginx fix. This is user-observed mobile acceptance, separate from the automated
  proxy checks above.

## Local-laptop coexistence fix — 1 November 2026

- Added the optional, loopback-only `AUTH_LOCAL_ORIGIN`. Cookie selection uses
  the request URL, not an attacker-supplied Origin/forwarded-host downgrade.
- Authentication regression: 48 passed, 5 opt-in skipped in a network-disabled
  disposable container using synthetic data. Covers local/HTTPS login, separate
  cookie flags, authenticated reads, CSRF rejection and independent logout.
- Backend recreated without rebuilding; Nginx validated/reloaded. Credential-free
  live proxy checks accepted the laptop and tunnel origins and rejected an
  unrelated origin. No existing user session was logged out by these checks.
