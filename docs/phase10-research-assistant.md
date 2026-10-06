# Phase 10 — Research Assistant

**Complete and deployed — 6 October 2026.** Implements Master Integration Plan
sections 12–13 and the Phase 10 definition of done. Exact selected-document
retrieval remains Phase 11.

## Implemented

- Reuses owned chats/messages, KB associations, the LLM factory, LangChain
  retrieval/history, streaming and the saved-answer envelope.
- Alembic `riq_005` persists Public/Private/Both conversation scope. Old chats
  default to Private; Public needs no private KB, and Both includes only selected
  owned private KBs plus the published institutional corpus. No admin bypass.
- SQL authorizes ready documents before vector search and rechecks before output.
  Server-owned history replaces client-submitted assistant history.
- Bounded Pydantic answer blocks reference deterministic E1/E2 evidence IDs.
  Unknown references, uncited claims, invented bibliography fields, model-authored
  links/HTML and malformed output are rejected. SQL supplies citation metadata;
  citation popups show title/author/department/year/page/excerpt and PDF links.
- Missing evidence supports explicit abstention. Saved answers redact evidence
  when a source is withdrawn. Scientific faithfulness evaluation remains Phase 20.
- The Research Assistant UI exposes source selection and saved conversation scope.
- Live ingestion exposed identical page text colliding in chunk IDs. New IDs use
  SQL document ID and chunk position; existing chunks/vectors are untouched.

## Verification

- Full isolated backend suite before the final error-message adjustment:
  **251 passed, 40 environment-specific skips**.
- Final affected baseline/retrieval/assistant suite: **60 passed, 1 MySQL-only skip**.
- Final disposable MySQL authorization/corpus/retrieval/assistant suite:
  **113 passed**. Earlier additional migration/revocation gate: **30 passed**.
- Frontend: **74 tests passed**; production build and type checks passed.
- Production `riq_004` → `riq_005` migration preserved all original table
  fingerprints, excluding the newly defaulted column. Downgrade refuses Public/Both
  conversations rather than silently changing their meaning.
- Final live synthetic gate passed Private/Public/Both cited streams, deterministic
  citation mapping and SQL metadata, saved reopening, foreign-user 404, follow-up,
  missing-evidence abstention, empty selection, exact PDF bytes, source withdrawal,
  and SQL chunk/Chroma vector agreement.
- Test KB 24, documents 53/54, chats 27–30 and temporary sessions were removed
  through existing lifecycles. Cleanup called those same services directly without
  loading embeddings unnecessarily. All five original documents and original SQL,
  MinIO and Chroma data were preserved.
- The aggregate snapshot initially differed because conversation 21 gained two
  messages during the run. Independent reconciliation proved every original row
  unchanged; messages 178/179 were preserved. The raw receipt and reconciliation
  are both retained, rather than rewriting the failed aggregate assertion.
- Frontend image: `researchiq-frontend:phase10-20261006`, image ID
  `sha256:2a987df8e1bb5f081d1226ac41970ce7db8ce997a14fc5e6eed41923071cc77d`.
  HTTP asset checks verified the deployed source selector and corrected error text.
- Earlier Chrome inspection covered Library and the Research Assistant list.
  This session's browser helper pipe was unavailable and its browser inventory
  empty; no new visual browser sign-off is claimed.

## Runtime fixes and limitations

- Original NVIDIA free-model requests returned HTTP 503 overload errors. The user
  approved `OPENAI_MODEL=openrouter/free`; no other `.env` setting changed.
- Reasoning and visible output share the provider budget. Generation is bounded at
  4,096 tokens while the prompt requests answers within 1,024 tokens; the JSON and
  citation limits remain. See [OpenRouter reasoning budgets](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
- The [free router](https://openrouter.ai/openrouter/free) can choose different
  models. Three final-gate requests needed one explicit retry after invalid model
  output. Availability/output quality are not guaranteed; failures remain visible,
  recoverable, and are never saved as successfully completed answers.
- Provider unavailability, invalid output and actual source withdrawal now have
  distinct sanitized errors. The frontend no longer suggests every failure means
  sources changed. Credentials and provider diagnostics stay private.
- nginx API idle timeout increased from 60 to 180 seconds after a real stream
  timeout; configuration validation and live reload passed.
- The verified MiniLM model cache was restored after container recreation. Model,
  dimensions and vectors did not change. Persistent model-cache hardening and
  repeated model initialization remain documented deployment/performance work.

## Recovery and evidence

Artifacts outside Git: `C:\Users\tayya\Projects\ResearchIQ-recovery\20261003-cleanup`.

- Baseline code archive: `phase10-before-code.zip`, commit `1457dbd`.
- SQL backup: `phase10-before-20261005.sql`, SHA-256
  `566eef30c774482cf1b38a6bd850206ade11ff117bdc8de9c03ee97c389f65ce`.
- Final receipts: `phase10-final-20261006`, also retained in ignored
  `backend/.pytest_cache/phase10-final-20261006`. See `phase10-live-receipt.json`,
  before/after fingerprints and `preservation-reconciliation.json`.
- Live synthetic runner: ignored `backend/.pytest_cache/phase10_router_gate.py`,
  with an external copy `phase10_final_acceptance.py`. It makes temporary fixtures
  and requires the configured providers; do not run it during active ingestion.
- Previous frontend image: `researchiq-frontend:before-phase10-20261005`.
  Retag it as `researchiq-frontend`, recreate only frontend with
  `docker compose up -d --no-deps --no-build frontend`, then reload nginx.
- Do not remove `source_scope` or restore the private-only backend while Public/Both
  chats exist. Preserve their semantics first. Never overwrite current user data
  with an old backup merely to undo code.

## Next existing-plan task

Phase 11: authorize exact immutable document IDs and constrain retrieval to that
set for Summarize/Compare/Analyze, reusing Phase 9's existing retrieval service.
