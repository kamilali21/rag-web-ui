# Chat generation correction — 7 October 2026

Maintenance correction after Phase 11, not a Phase 12 implementation.

## Root cause and reproduced evidence

Every message previously entered permission-scoped retrieval and the research
prompt, which requires a citation on every answer block. A live probe using only
synthetic evidence reproduced `hi` producing a valid JSON greeting with an empty
citations array. The citation validator correctly rejected it, resulting in the
reported invalid-answer error after 7.04 seconds. The same probe's factual
research question passed in 7.37 seconds. An evidence-only prompt can also abstain
on a greeting, explaining the inappropriate insufficient-evidence reply.

The earlier generic error could not be attributed to a specific retained log
entry; it is not claimed to have the same cause. Retrieval failures now have a
distinct sanitized message. Separately, the embedding factory constructed the
local model on every search/upload, repeating initialization and cache checks.

## Correction

- Recognize only complete common greetings after chat/source authorization. Save
  and stream a normal greeting without calling retrieval or an LLM. Greeting plus
  a research question still follows the full evidence/citation path.
- Exclude greetings, abstentions and known error messages from model history;
  persisted conversations remain intact. A greeting-only history no longer adds
  an unnecessary question-rewriting model request to the next research question.
- Retry malformed structured generation once, only before any answer is emitted.
  Preserve evidence validation and recheck permissions before retry/output. Never
  replay partial answers or retry authorization failures. Send the evidence
  envelope only when the first validated answer block is ready.
- Reuse one HuggingFace embedding model per worker. A lock serializes cold starts;
  a one-entry cache is keyed by model and token, and failed initialization is not
  cached. Model selection, dimensions and vector contents are unchanged.
- No frontend, authentication, schema, provider selection or environment change.

## Verification and deployment

- Focused chat/citation/authorization regression: **99 passed, 1 MySQL-only skip**.
- Full isolated backend suite: **307 passed, 40 environment-specific skips**.
- Disposable MySQL chat/Phase 9–11 gate: **111 passed**.
- New tests prove greetings avoid providers, ownership still applies, research
  questions retain citations, retries are bounded and do not duplicate partial
  output, and concurrent model requests share one successful initialization.
- Live HTTP: `hi`, `hello`, `Hello!` and a greeting with a populated library passed
  in **0.146–0.872 seconds**, including saved reopening. A temporary synthetic PDF
  processed successfully; its cited research answer passed in **10.095 seconds**,
  and a history-dependent follow-up in **25.262 seconds**. These are single-run
  observations, not a latency guarantee or a controlled research-query benchmark.
- All emitted citation indices resolved to the synthetic document. Test chats
  33/34, KB 26, document 55, task 57 and session 141 were removed through existing
  lifecycles (session row removed explicitly). Original research rows, objects
  and vectors remain unchanged; Alembic remains `riq_005`.
- An initial readiness attempt received HTTP 502 before backend startup completed;
  its session 140 was removed. Reloaded nginx and reran after health readiness.
- Deployed by restarting the existing bind-mounted backend and reloading nginx.
  Existing frontend/hero deployment is unchanged. Browser inspection was not
  available; verification used real HTTP streams and saved API responses.
- Evidence outside Git: `ResearchIQ-recovery/20261003-cleanup/` contains
  `chat-diagnostic-20261007.json`, `chat-startup-retry-20261007.json`, and
  `chat-reliability-20261007/` with before/after fingerprints and the live receipt.
  The synthetic runners are retained there and in ignored `backend/.pytest_cache`.

The free-model router can still be unavailable or return invalid output after
the bounded retry. Such failures remain visible and are never saved as successful
research answers. Persistent on-disk model-cache hardening remains Phase 21.
Next planned feature remains Phase 12: structured single-document summary.

## Windows corpus-chat correction - 8 October 2026

The 7 October synthetic acceptance did not cover the reported Public conversation
with its restored history, or survival of the embedding cache across container
recreation. This follow-up supersedes the cache deferral above only for the
observed runtime failure; it does not close Phase 21 or start Phase 12.

### Findings and fix

- The recreated backend lacked MiniLM weights. Restored the checksum-verified
  original cache into `researchiq_huggingface_cache`, mounted at
  `/root/.cache/huggingface`. Verified an offline load, reuse, and persistence
  across backend recreation. Local files are now tried first; a fresh install
  can still download the same configured model. Embeddings and vectors were not
  regenerated. Weight SHA-256 remains
  `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
- History rewriting could return empty/oversized text, fail, or stall before
  retrieval. It now has a 20-second deadline and falls back to the original
  question on these failures. Existing source authorization still controls search.
- OpenRouter TLS/connectivity failures were intermittent, not a proven browser
  or VPN block. OpenAI-compatible requests now have a 45-second SDK timeout and
  one SDK retry. These are per-request/inactivity bounds, not a whole-turn SLA.
- With user authorization, changed ignored runtime `.env` from `openrouter/free`
  to `apodex/apodex-1.1-mini:free`. The account has no paid credit; no paid model
  or purchase was used. Alternative probes returned 429/403 or invalid output.
- The selected serving endpoint advertises structured output but rejects
  `json_schema` with HTTP 400. Use its supported `json_object` mode for answers,
  with reasoning disabled and parameter support required. Rewrites stay plain
  text. The existing application validator still rejects wrong fields, invented
  references, model-authored links, and malformed/partial output. Future selected
  OpenRouter models must support JSON mode and disabling reasoning.
- Clarified that broad library/corpus requests refer to supplied evidence, and
  that supported partial answers should name missing details. Unsupported facts
  still require abstention. Added exact greeting typos including `god morning`;
  mixed greeting/research requests still require evidence.

### Acceptance

- Full isolated backend suite: **314 passed, 40 environment-specific skips**.
- Disposable MySQL chat/Phase 9-11 gate: **118 passed**. The first invocation
  inherited production OTP settings, so JWT fixture requests correctly returned
  401 (64 failed / 54 passed). Reran with `EMAIL_OTP_ENABLED=false` only in the
  disposable test container. Production OTP/session settings were never changed.
- Final live HTTP replay used a temporary copy of Public chat 32's real history:
  `god morning` **0.09s**, `how too setup one drive` **5.93s**, OneDrive overview
  **26.71s**, and `What folders can it back up?` **22.16s**. All completed without
  error frames, persisted exactly, and reopened. Research citations resolved to
  permitted OneDrive document 31. The follow-up correctly named Desktop,
  Documents and Pictures.
- Private chat acceptance used a temporary copy of chat 16: cited answer in
  **5.96s**, evidence only from document 28. Both scope passed in **8.12s**, with
  permitted evidence from documents 28/31. Saved reopening passed in both cases.
- These are individual observations, not guaranteed latency or provider uptime.
  Earlier attempts are retained: JSON Schema was rejected; prompt-only output
  could be invalid; some setup/overview attempts abstained. The PDF references
  setup guides but does not contain full installation steps. The final cited
  answers do not make missing step-by-step instructions available.
- Final temporary chats 39/40/41 and sessions 148/149/150 were removed; earlier
  diagnostic clones/sessions were also removed. Before/after hashes confirm all
  original research records and conversations unchanged. Existing failed replies
  remain historical records. No document/object/vector deletion or schema change.
- Deployed by recreating the existing backend for its new cache mount/model
  setting, then restarting for bind-mounted code changes and reloading nginx.
  Frontend/hero and authentication are unchanged. Verification is real HTTP/API;
  no connected-browser visual sign-off is claimed.
- Evidence and runners are outside Git at
  `ResearchIQ-recovery/20261003-cleanup/chat-public-final-20261008/`,
  `chat-private-20261008/`, `chat-both-20261008/`, and
  `chat-model-probe-20261008.json`; test runners also remain in ignored
  `backend/.pytest_cache`.

### Recovery

The pre-change source archive is `chat-before-2b9fa8d-20261008.zip` outside Git.
The protected `chat-env-before-20261008.bak` contains secrets and must not be
committed or published. Roll back only these chat/embedding/factory edits if
needed after preserving subsequent changes; restore just `OPENAI_MODEL` from
the backup to reverse model selection. Keep the cache volume and existing
research volumes. Restart/recreate only backend as appropriate and reload nginx;
no database rollback is required. Preserve the user's separate MinIO image edit.

Checkpoint: `researchiq-chat-corpus-20261008`. At that checkpoint, the next
feature was Phase 12 structured summary. The approved 16 October insertion
moves that feature to Phase 13; the current Phase 12 is researcher publishing.
