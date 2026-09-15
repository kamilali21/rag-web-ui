# ResearchIQ Integration Progress

<!-- Added by ChatGPT: implementation gates and evidence for the adaptable master plan. -->

Source: `ResearchIQ_Master_Integration_Plan.pdf`, version 1.0, 15 September 2026.

## Working Agreement

- Complete and verify one feature before starting the next.
- Extend the current FastAPI/MySQL/MinIO/Chroma/Next.js application.
- Keep existing private ownership and API compatibility until each replacement is tested.
- Use Alembic for schema changes; test migrations on disposable data before applying them.
- Record deviations, tests, limitations, and the next gate here.
- A mock or sample UI is not a completed backend feature.

## Current Gate: Phase 0 - Blocked At Live LLM Authentication

- Branch: `codex/master-integration`.
- Pre-integration source snapshot: `09a9485` (existing frontend work, not a stability certification).
- Running services: backend, frontend, MySQL, Chroma, MinIO, Nginx.
- Existing database revision: `3580c0dcd005`.
- Initial counts: 2 users, 2 knowledge bases, 4 documents, 190 chunks, 1 chat.
- Actual configured providers: OpenAI-compatible chat, HuggingFace embeddings, Chroma vectors.
- Baseline completion requires a real synthetic PDF upload, processing, retrieval, streamed cited answer, persistence and cleanup.
- Also requires frontend/backend regression tests and review of baseline failures.
- No new ResearchIQ schema or OTP/public corpus endpoints are implemented yet.

### Verified On 15 September 2026

- 22 backend tests passed: 17 existing provider unit tests and 5 new baseline regression tests.
- 13 frontend tests passed using the normal test command after configuring a 15-second interaction timeout.
- Frontend TypeScript check passed.
- Real synthetic test passed registration, login, PDF upload, MinIO storage, PDF extraction, async processing, relational persistence, embeddings and Chroma retrieval.
- Real streamed answer failed: `https://openrouter.ai/api/v1/chat/completions` returned HTTP 401 Unauthorized for configured model `openrouter/free`.
- The synthetic chat, collection, PDF objects, vectors, task and user were removed. Original counts remain 2 users, 2 knowledge bases, 4 documents, 190 chunks and 1 chat.
- Database backup: ignored local file `.local/backups/baseline-20260915.sql`, restricted directory and file permissions. No schema migration has been applied.
- Source fixes are loaded by the existing backend container; no temporary server or changed port.

### Required Next Action

The user must provide valid credentials through `rag-web-ui/.env` (`OPENAI_API_KEY` for the configured OpenRouter endpoint), or select a different configured provider. Do not print secrets or silently switch providers.

After credentials are updated, recreate only the backend service so Compose rereads its environment; a plain restart does not reload `env_file` values. Verify startup, rerun the synthetic acceptance check, inspect citation mapping and persistence, then record the Phase 0 checkpoint. Do not begin Phase 1 until that succeeds.

### Repeatable Checks

```sh
# Frontend, from frontend/
npm run test:ci -- --runInBand --silent
npx tsc --noEmit

# Backend, from backend/, with requirements-dev.txt installed in the test environment
python -m pytest tests/test_minimax_unit.py tests/test_baseline_regressions.py -q

# Opt-in live acceptance test; uses configured providers and synthetic data
python -m tests.baseline_smoke
```

The live smoke script defaults to `http://nginx/api` inside Docker. Set `BASELINE_API_URL` when running elsewhere. It does not send existing research documents to an external provider.

## Plan Corrections To Carry Forward

1. Preserve `/api` compatibility. The running application uses `/api`, while the plan's examples use `/api/v1`. Do not silently break chat, uploads, API keys, or frontend calls by renaming the prefix.
2. Create `departments` before an `admin_allowlist.department_id` foreign key.
3. Add the omitted nullable password migration and explicit non-login system-account rule.
4. Revocable sessions need server-side session persistence, expiry, rotation and CSRF protection. OTP identity verification alone does not provide these.
5. Secure cookies require HTTPS. The present `http://127.0.0.1.nip.io` deployment must be addressed before claiming production-secure authentication.
6. Publication/archive state is missing from the proposed schema. Processing completion and publication are different states; only ready, published public documents may be discovered or retrieved.
7. OTP cooldown/rate-limit accounting must work across API workers and concurrent requests. A table containing only OTP hashes is insufficient for IP limits and delivery failures.
8. Admin allowlist removals must revoke effective content-admin permission; resolving a role only once at sign-in is insufficient.
9. Persist analysis runs/evidence as part of the first real analysis workflow, before history UI. Do not postpone recoverability until every analysis type is implemented.
10. Security tests belong to each feature gate, not only Phase 19.

## Baseline Repairs Verified By Regression Tests

- All selected nonempty knowledge bases contribute through the existing LangChain retriever merger.
- New Chroma insertions use relational chunk IDs; repeated inserts target the same vector IDs.
- Knowledge-base deletion uses the vector-store contract and recursively cleans MinIO object prefixes.
- Migration startup compares the installed database revision with migration-script head and disposes its check connection pool.
- Global LangChain debug output was removed to avoid logging private evidence.
- Chat no longer duplicates the current question in history or mutates the caller's message payload.
- Successful streams emit a completion frame; failures roll back and return a valid JSON error frame without internal provider details.
- Removed the empty backend-root package marker that made pytest import `/app/__init__.py` instead of the actual `/app/app` package in Docker.

## Deferred Findings For Their Feature Gates

- Historical vectors may still use generated IDs. Before per-document deletion/reindexing, reconcile existing Chroma IDs through chunk metadata; do not assume new insert behavior repairs old vectors.
- Ingestion retries, partial failures, repeated chunks, processing-state filters and publication need attention before public corpus support.
- Embedding models are reconstructed for each call, causing repeated HuggingFace requests and avoidable latency. Add bounded, concurrency-safe reuse when stabilizing ingestion/retrieval.
- A mocked chain verifies multi-collection streaming and serialization, but is not a substitute for the currently blocked real LLM acceptance test.

## Remaining Sequential Gates

1. Schema foundation, migration reversal and data preservation.
2. Authorization core and private access regression tests.
3. SMTP OTP and secure revocable sessions, including real delivery verification.
4. System-owned public corpus.
5. Academic metadata.
6. Public catalog and bookmarks.
7. Admin ingestion and publication lifecycle.
8. Private library parity.
9. Permission-scoped retrieval.
10. Research Assistant and citation integrity.
11. Exact document-scoped retrieval.
12. Structured summary.
13. Insights on real catalog data.
14. Compare with evidence persistence.
15. Bounded Analyze workflow.
16. Contradiction interpretation.
17. Corpus-qualified candidate gaps.
18. Analysis history.
19. Cross-feature security testing.
20. RAG evaluation.
21. Deployment hardening and recovery verification.
