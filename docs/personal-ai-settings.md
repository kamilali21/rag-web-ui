# Private AI provider settings — 25 October 2026

User-requested extension after Phase 17. Planned Phase 18 is not started or renumbered.

## Using the feature

Open **Profile → Your AI provider**. Choose OpenRouter or OpenAI, select/enter a
supported model, enter your provider API key and accept provider billing/data use.
Save, then optionally **Check saved connection**. The check makes one small AI
request without any research documents. New Chat, Summary, Compare and Analyse
requests (including evidence interpretation) use the same personal settings.
Already-running calls finish with the configuration they started with.

OpenRouter defaults to `openrouter/free`; other OpenRouter model IDs may be entered
if they support JSON and structured outputs. Direct OpenAI initially supports `gpt-4.1-mini`,
`gpt-4.1`, `gpt-4o-mini` and `gpt-4o`. These are a compatibility list, not a claim
that one is the best/latest model. Model availability and billing depend on the
user's provider account. No paid fallback is added.

Leave the key field blank to change the model while retaining the same provider's
saved key. Changing provider requires a replacement key. **Remove personal key**
restores the existing shared application configuration. Without personal settings,
the application behaves as before. Embedding/indexing settings remain unchanged.

## Security and behavior

- Additive Alembic `riq_008` adds only `user_ai_settings`, one row per user.
- AES-256-GCM encrypts each key with a fresh random nonce and authenticated data
  bound to the user ID, provider and format version. The dedicated encryption key
  stays outside SQL. A copied/tampered credential fails closed.
- Owner identity comes from existing authentication. There is no user-ID parameter,
  admin credential route or public profile projection. Responses contain only
  configured/provider/model/last four characters; responses use `Cache-Control: no-store`.
- Bounded manual input validation avoids echoing keys in FastAPI validation errors.
  Provider errors never return/log exception bodies. The browser uses a password
  input, keeps the value only during entry/submission and clears it after each
  operation. No key is saved in localStorage or sessionStorage.
- Provider destinations are server allowlisted HTTPS URLs. Users cannot enter
  custom endpoints. Personal credentials use SDK `max_retries=0`; existing bounded
  application retry and citation/permission validation remain in force.
- A request-local ContextVar scope surrounds each service invocation, including
  async chat streams and all analysis stages, and resets after completion/errors.
  Shared environment settings are never mutated. A personal key error does not
  fall back to application credentials.
- Keys are private from other users and admin screens. A trusted operator with
  server access and the encryption key can decrypt them; encryption is not a
  protection from a fully compromised application server. HTTPS is required for
  public deployment. Never commit `.env`, SQL data dumps or encryption secrets.
- Summary reserves 4,000 tokens rather than 1,200; Summary/Chat request low-effort
  reasoning on OpenRouter rather than disabling reasoning on models that require it.
  Structured output and citations are still validated. Provider outages, quotas
  and invalid responses can still occur; BYOK is not a guarantee against them.

## Deployment and recovery

Set `AI_KEY_ENCRYPTION_KEY` to an independent, random 32-byte value encoded as
URL-safe base64. Keep it stable across deployments and back it up securely outside
the database. Missing/invalid encryption configuration disables personal-key
save/use; it does not disable the existing shared model for unconfigured users.
Losing/replacing the encryption key requires users to replace their saved API keys.
Rotation with existing records needs an explicit decrypt/re-encrypt operation;
do not simply overwrite the secret.

Test `riq_008` on disposable MySQL first, back up live SQL locally, apply the
additive migration and verify original rows unchanged, then recreate backend to
load the encryption environment variable. No backend image rebuild is needed
locally when cryptography is already installed. It is now an explicit dependency
for future clean builds. Rebuild/deploy the frontend separately.

Rollback application code to `researchiq-phase17-evidence-20261025` and frontend
image `researchiq-frontend:phase17-verified-20261025`. The additive settings table
can remain. Its downgrade refuses to discard stored credentials: owners must
remove settings first if a database downgrade is required. Removing a saved key
does not revoke it at the provider or erase old encrypted database backups.

## Verification

Tests cover owner/admin isolation, masking, input bounds, encryption and tampering,
context concurrency/reset, fixed provider destinations, no fallback, all four AI
entry points, frontend save/remove/check behavior and disposable MySQL roundtrip.
The opt-in `tests.personal_ai_live_acceptance` runner uses synthetic PDFs/users,
temporarily assigns the existing OpenRouter key only to its synthetic owner,
uses `openrouter/free`, and verifies Summary/Chat/Analyse/Compare and cleanup.
No paid OpenAI call is made by this acceptance runner.

Verification: 117 frontend tests, TypeScript and the final production frontend
build passed. The full backend run passed 495 tests with 44 opt-in skips and two
old isolated-chat mocks needing the new credential resolver stubbed. After fixing
those mocks, the affected 71-test suite passed (one live opt-in skip). Disposable
MySQL migration passed. Live migration preserved all values in 25 original tables.

The initial synthetic personal-key run reached a completed comparison result
(23.64s), after its connection, Summary, Chat and Analyse assertions. Its final
cleanup receipt was lost at interruption. A repeat run passed connection, Summary
and Chat but Analyse returned temporary HTTP 503; its cleanup explicitly verified
original SQL/MinIO/Chroma snapshots unchanged. No synthetic users or keys remain.
Thus real provider success and failure handling were exercised, but an uninterrupted
all-green live runner receipt is not claimed. OpenAI routing is tested with provider
doubles; no paid OpenAI key was supplied and no paid call was made.

The frontend and backend are deployed. Health, anonymous rejection, encryption
configuration and served Profile assets/CSS passed. Browser automation timed out;
rendered visual acceptance is not claimed. Existing ESLint-option/Tailwind build
warnings remain. SQL backup: ignored `.local/backups/pre-personal-ai-20261025.sql`.
Final frontend image ID: `sha256:9bb1ca8e1c3d81dc998ced32c38ba55d60b17f8d19e457e98d3d166eb3c28082`.
Checkpoint: `researchiq-personal-ai-20261025`; no push.

References: [OpenAI key handling](https://developers.openai.com/api/reference/overview),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[GPT-4.1 mini capabilities](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
