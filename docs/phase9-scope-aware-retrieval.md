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

## Next unfinished task within Phase 9

Connect the resolved set to the existing vector-store search contract, with
allowed document IDs constrained BEFORE retrieval. Recheck SQL permission and
publication after external calls before returning evidence. Verify Public,
Private and Both with unpublished/foreign vectors, empty sets and concurrent
revocation; preserve the working private RAG path.

This first increment is a tested authorization foundation, not a completed
Phase 9 retrieval workflow. It is not wired into live chat yet. Research
Assistant/chat integration remains Phase 10; exact user-selected document
retrieval remains Phase 11. Do not introduce a replacement RAG pipeline.
