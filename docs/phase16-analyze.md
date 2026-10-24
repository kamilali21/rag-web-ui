# Phase 16 - Bounded Analyze Research - 23 October 2026

## Scope and usage

In Insights, select one to five ready papers and choose **Analyse**, optionally
enter a research question, then choose **Generate analysis**. Public and Both
scope offer related public evidence; Private scope stays within the selected
owner-owned private papers. The UI explains the discovery bounds before submission.

This implements the existing amended Phase 16: research profiles, related-paper
discovery and bounded cross-study synthesis. Contradiction interpretation remains
Phase 17, candidate gaps Phase 18 and the history browser Phase 19.

## Implementation

1. `POST /api/insights/analyses` validates 1-5 distinct exact document IDs and
   current access/readiness. Public papers must be published; private papers must
   be owned by the requester. Admin status does not bypass private ownership.
2. Retrieve at most six passages per selected paper, each capped at 1,200 characters.
   Build structured profiles for objective, methodology, dataset/sample, findings,
   limitations and future work. Each profile citation must belong to that paper.
3. Derive bounded topic terms from selected titles, the question and validated
   objective claims. Narrow published/ready public candidates in SQL by available
   selected departments and topic matches in titles/abstracts. Missing department
   metadata uses topic filtering alone; missing signals never expand to the entire
   corpus. Consider at most 20 candidates, ordered by descending document ID.
4. Semantically rank evidence within those exact candidate IDs. Select up to
   three distinct related papers, then retrieve at most four passages per related
   paper. Private scope and the opt-out never run public discovery.
5. Synthesize seven cited sections: overall summary, key insights, common findings,
   major limitations, methodological differences, research trends and future
   directions. Common findings, methodological differences and trends require
   citations from at least two distinct papers for each claim.
6. Recheck current source permissions, file hashes and SQL-backed excerpts before
   model stages and before saving. Persist selected/related roles, results and
   immutable evidence snapshots using Phase 15's `riq_007` tables. No schema change.

`GET /api/insights/analyses/{id}` is owner-only and checks all selected and related
sources again. Revocation or deletion of a related source also hides the saved
result. Compare and Analyse read endpoints enforce their own workflow type.
Per-owner request UUIDs support replay without generating another successful run.

Generation reuses the existing free-model configuration and shared structured
provider policy. There are two model stages, each with at most two attempts total
(one bounded rate-limit/transient-provider retry or output correction). No paid fallback, new
provider or second RAG system is introduced. Evidence, metadata and generated
profiles are treated as untrusted data. Model output is validated JSON rendered
as React text, never executable HTML.

Live acceptance exposed an existing shared-generator incompatibility: the free
router selected an endpoint requiring reasoning, while the request explicitly
disabled reasoning. The provider returned HTTP 400. Replaced it with low reasoning
effort (excluding reasoning text from the response) to support mandatory-reasoning
endpoints and reduce their default latency; structured-output constraints,
token bounds, citation validation and the configured model stay intact. A direct
synthetic provider check returned a valid profile, and the affected regression
suite passed after the correction. OpenRouter documents mandatory reasoning in
its [reasoning configuration](https://github.com/OpenRouterTeam/docs/blob/main/guides/best-practices/reasoning-tokens.mdx).

Further live checks identified two distinct failure paths: intermittent free-router
HTTP 404/5xx responses, and the SDK throwing `LengthFinishReasonError` before the
normal JSON validation path. Temporary routing failures now use the same single
retry allowance. Comparisons reserve at least 4,000 output tokens, with a bounded
size-based ceiling of 10,000. A truncation correction may increase the stage budget
once, never above 12,000 tokens. Repeated truncation is rejected without saving a
partial result. Rate limiting, transient routing, malformed output and truncation
share the same two-attempt limit; their retries do not stack. Provider exception
types/status codes are logged without prompts, credentials or evidence text.

## Presentation and limitations

Results use the existing theme colors, buttons, scrollable tables and dialog.
They include loading/error/retry states, coverage counts, selected versus related
source labels, expandable profiles/evidence and source-page links. Saved links
reopen through the API instead of regenerating. Keyboard/focus handling and mobile
dialog constraints reuse the existing components.

Discovery is deliberately bounded and can miss relevant papers beyond the SQL
candidate limit, other departments or unmatched topic terms. Semantic ranking
indicates relevance, not scientific quality or confidence. An empty section means
information was not identified in retrieved evidence, not that it does not exist.
Citation checks verify source identities; they do not independently prove scientific
claims or entailment. The notice qualifies results as a limited evidence synthesis,
not an exhaustive literature review or a definitive gap/contradiction finding.

As in Phase 15, processing is synchronous with persisted status. Closing the UI
does not cancel server processing; a process interruption can leave a processing
record. There is no job queue or automatic recovery worker in this phase.

## Repeatable checks

```powershell
# From backend with development test dependencies installed
python -m pytest tests/test_phase15_comparison.py tests/test_phase16_research_analysis.py -q

# From repository root, explicitly opt in to synthetic live data and configured providers
docker compose exec -T -e PHASE16_LIVE_ACCEPTANCE=1 backend python -m tests.phase16_live_acceptance
```

The live runner reuses Phase 15's upload/index/cleanup harness and adds a temporary
department and related public PDF. Department filtering confines related discovery
to those fabricated papers. It checks saved evidence, citations, idempotency,
ownership and related-source revocation, then runs the existing comparison
regression. Cleanup removes only its fixtures and verifies original SQL rows,
MinIO object identities and Chroma vector IDs.

## Recovery

The previous verified source is `researchiq-phase15-compare-20261022`; the previous
frontend image is `researchiq-frontend:phase15-verified-20261022`. Phase 16 requires
no database migration or model-setting changes. A compatible code/image rollback
can leave additive analysis records intact at `riq_007`. Do not downgrade the
schema or restore an old database just to roll back the Analyse UI/service.

## Verification and checkpoint

- Backend regression: 444 passed, 43 skipped before the final provider corrections;
  the final affected comparison/analysis suite passed all 69 tests afterward.
- Frontend: 109 tests passed; TypeScript and production build passed. Existing
  build warnings about ESLint options and Tailwind line-clamp remain.
- Synthetic Analyse acceptance passed in 83.65 seconds: profiles, bounded related
  discovery, citations, saved reopening/replay, ownership and source revocation.
  Its subsequent comparison exposed SDK truncation. After fixing that path, a
  separate live comparison regression passed in 27.95 seconds. These are separate
  acceptance runs, not a claim that the final combined harness was rerun.
- Every fixture cleanup confirmed original SQL rows, MinIO objects and Chroma
  vector IDs unchanged. No real papers were sent to the provider by these tests.
- Frontend image `sha256:318e481f0b51afa12644582ede197faea58adf8af86d1e7630ca727e46f140c9`
  is deployed; backend source restarted. Health, served Analyse assets and
  anonymous API rejection passed. Browser rendering could not be inspected
  because no browser is connected; component tests cover presentation behavior.
- Annotated recovery tag: `researchiq-phase16-analyze-20261023`. No push.

Phase 16 is complete. The next gate is Phase 17 evidence interpretation. External
free-model availability and latency remain variable; retries are bounded and
failed/partial results are never represented as completed analyses.

## Analyse recovery correction - 24 October 2026

User testing exposed intermittent research-profile validation failures and lost
results after closing the dialog. Server records showed that disconnected
requests could subsequently complete; a 499 in nginx did not mean generation
had failed. One completed run took several minutes. The exact original invalid
output was not logged, so it cannot be attributed to a specific schema violation.

- Increase the profile response budget from 1,800 to 4,000 tokens for one paper,
  scaling to a bounded 8,000 for five papers. Explicitly request concise claims
  and include the full schema bounds in the existing single correction attempt.
  Log validation categories and stage duration without evidence or output text.
- Preserve an opaque request UUID in tab session storage and the URL. Add
  **Resume last analysis** and an owner-checked request lookup, reusing all saved
  source-access checks. No private text, questions or results enter browser storage.
- Reopened processing results poll every five seconds for up to five minutes;
  manual status checking remains available. Recovery never starts another model
  call. This is one-request recovery, not Phase 19's analysis-history browser.
- Generation remains synchronous. The free provider can still be slow or
  unavailable; server restarts do not restart interrupted generation. No queue,
  schema change or paid-model fallback is introduced.
- A fresh fixture exposed a provider HTTP-200/SDK-parser TypeError. Malformed
  completion-envelope failures at the installed SDK boundary now share the
  same one-retry allowance. Unrelated application TypeErrors are not retried.
  The regression reproduces null choices through the installed adapter.
- Verification: 74 affected backend tests; 22 Insights frontend tests; TypeScript
  and production build passed. One overloaded-machine UI test timed out during
  the build and passed when rerun afterward. Existing lint-configuration and
  Tailwind warnings remain. Deployed image:
  `sha256:7c232ebd3c8a50917c8e32b350086f8ac434cff51da8a2b8e93fc5a34e7414ce`.
- Live Analyse passed in 54.37 seconds with request-UUID recovery, ownership,
  citations, saved reopening and related-source revocation. Health, served
  frontend assets and anonymous rejection passed. Browser inspection timed out;
  no rendered-browser acceptance is claimed.
- The same fixture's comparison regression passed in 25.36 seconds. Cleanup
  confirmed original SQL rows, MinIO objects and Chroma vector IDs unchanged.
  Recovery tag: `researchiq-analyze-recovery-20261024`.
