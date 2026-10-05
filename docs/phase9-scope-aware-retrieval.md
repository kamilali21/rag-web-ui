# Phase 9: Scope-aware retrieval

Started 4 October 2026 after Phase 8 completion checkpoint `ad8960e`, tag
`researchiq-phase8-verified-20261004`.

Authority: Master Integration Plan phase 9 and sections 12-13:
Public / Private / Both authorization and retrieval constraints. Reuse the
existing SQL ownership, canonical public corpus and vector-store contracts.

## First increment

`app/services/retrieval_scope.py::resolve_scope` computes permitted ready
SQL document IDs grouped by knowledge base, before any vector or LLM call:

- Private: only current-user private, non-system-managed KBs.
- Public: only the canonical system-owned corpus and published documents.
- Both: the union of those sets, with no admin/superuser private bypass.
- Only the latest completed processing attempt qualifies. Failed cleanup,
  pending/processing, drafts, archives, fake public KBs and unknown states do not.
- Invalid scopes and inactive/system actors fail closed; an empty map means no
  permitted sources, never an unrestricted search fallback.

Validation: seven isolated ORM/authorization tests passed. Six read-only live
MySQL checks passed for two current verified users, verifying ownership,
publication/readiness and union behavior. No sessions, data or schema changed.

## Retrieval gate - COMPLETE, checkpointed 5 October 2026

`POST /api/retrieval/query` accepts `scope` (private by default), `query` and
`top_k` (1-20). It rejects unknown fields and scopes; authentication and session
CSRF use the existing dependencies. Clients cannot submit an authorization set.

The shared search service resolves SQL source IDs before opening a provider.
Chroma receives both KB and allowed-document filters in its native query;
Qdrant uses its native metadata conditions. An empty set never searches, and
unsupported/failing providers fail closed. Filters are batched at 500 IDs;
the candidate pool is bounded at five times top_k, up to 100, across stores.
Qdrant cosine scores are normalized to the same lower-is-better ordering.

After vector calls, a new SQL snapshot rechecks account state, private ownership,
canonical corpus identity, publication and processing readiness. Returned text,
filename, page and document identity come from SQL chunks/documents, not vector
claims. Unknown, foreign, stale and duplicate chunk IDs cannot become evidence.
Revocations can reduce the number of returned results; there is no broad fallback.

The existing public corpus query, private retrieval test, API-key query and
private chat now use this same boundary. Chat retains the existing history-aware
retriever, answer chain, streaming protocol and saved messages. It cannot generate
an answer from an empty trusted context. This secures the existing private flow;
the Public/Both Research Assistant controls and hardened citation workflow are
still Phase 10, and exact user-selected document mode is Phase 11.

### Automated verification

- Full isolated backend suite: 220 passed, 39 environment-specific skips.
- Final Phase 9 focused suite: 26 passed, including ranking and empty-context chat.
- MySQL 8 disposable `researchiq_phase2_test` schema: 80 Phase 2/4/9 checks passed.
  Separate-session publication, ownership, processing and account revocation
  checks prove a fresh read under MySQL REPEATABLE READ.
- Native Chroma and Qdrant filter contracts, hostile vector metadata/text,
  no administrator private bypass, invalid inputs, provider failure and
  multi-collection cited chat persistence are covered. Qdrant has adapter unit
  coverage only; the live installation uses Chroma.
- Before Phase 9, mobile Library corrections passed all 24 Library/Public Library
  tests and the production frontend build/type check, deployed at `af169ba`.

Run from backend in the isolated test image (no application .env/network):

```text
python -m pytest -p no:cacheprovider tests -q --disable-warnings --tb=short
python -m pytest -p no:cacheprovider tests/test_phase9_retrieval_scope.py -q
```

### Recovery and live gate

Recovery artifacts are outside Git in
`C:\Users\tayya\Projects\ResearchIQ-recovery\20261003-cleanup`.
Pre-change code: `phase9-before-code.zip` at `af169ba`.
Consistent SQL backup: `phase9-before.sql`, SHA-256
`a18f1180cb5acd568d34f975795aa243444bcdef36d0c4334767489df3bf45fb`.
No schema migration is required; revision remains `riq_004`.

`phase9_live_acceptance.py` stages exact synthetic private and public PDFs,
checks both users against all scopes, publication withdrawal, PDF download,
streamed citations and saved-chat reopen, and cleans through existing lifecycle
APIs. Temporary session IDs are recorded before use and removed in a nested
finally block. Before/after SQL, MinIO and Chroma fingerprints must match.
Completion requires the final receipt to report success and preserved data.

Live scope/citation acceptance passed on 4 October: Public/Private/Both for two
users, draft and foreign exclusion, withdrawal after unpublish, invalid scope
and forged selection rejection, CSRF, authenticated PDF download, real streamed
cited answer and saved conversation reopen. SQL chunk/vector agreement was
checked for all four synthetic documents before cleanup. The tool transcript
records those successful calls; the container-local final receipt was lost when
the user recreated the containers. A subsequent read confirmed all those exact
fixtures and maintenance sessions were removed.

On 5 October the attempted repeat hit its 15-minute cold-model download deadline.
After stopping the only active (synthetic) worker, collection 16/job 39 was cleaned
through the existing lifecycle service. This deletion supplied no embedding
function because vector deletion does not require model inference. No application
deletion behavior or code was changed. All original SQL rows, all three current
documents, MinIO object fingerprints and Chroma fingerprints match the fresh
before snapshot; temporary sessions 95/96 are absent. Durable evidence:
`phase9-20261005/phase9-recovery-validation.json` and before/recovered-after JSONs
in the host recovery directory. The failed repeat receipt is retained honestly.

Fresh SQL backup `phase9-before-20261005.sql` SHA-256:
`86c8b74a7875633d781120a86940f0d691396a16d0d3d0d96291860421b45b66`.
Cold Hugging Face transfers are a runtime limitation, not a passed repeat gate.
A separate helper is recovering the identical model with SHA-256 validation;
Phase 10 must pass a fresh live cited-chat gate before completion.

Next: Phase 10 Research Assistant, reusing chat with Public/Private/Both scopes
and validated evidence references. Phase 11 is not started.

Code rollback, if needed: restore only the Phase 9 application files from the
pre-change code archive/checkpoint and restart only backend after confirming
there are no active processing jobs. The archive is not a full-worktree reset;
preserve user changes, especially docker-compose.yml. No volume replacement,
schema downgrade or data restore is needed for this code-only phase.

Rendered-browser inspection remains unavailable: browser inventory returned
no connected browser. Live API acceptance and automated UI checks must not be
described as a rendered mobile visual test.
