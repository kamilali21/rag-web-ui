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
