# Phase 17 - Contradiction / Evidence Interpretation - 25 October 2026

## Scope and use

In **Insights**, select two to five ready papers, choose **Analyse**, select
**Evidence interpretation** under Analysis focus, and generate. Research overview
remains available. Public/Both may include bounded related public evidence;
Private remains limited to the user's selected private papers.

Results appear in the existing Insights dialog, using the same theme, controls,
citations and evidence snapshots. **Resume last analysis** recovers the most recent
request in that browser tab; the saved-result link reopens it later. There is no
separate results/history page yet. The history browser remains Phase 19.

This implements the amended Master Plan's Phase 17 and section 17's interpretation
model: a claim with supporting, contradicting and qualifying evidence, an
interpretation, and documented context factors. It does not implement Phase 18
candidate research gaps or rank studies as scientifically valid/invalid.

## Implementation and limits

- Extend the existing analysis request with `focus=contradictions`; the default
  overview request remains backward compatible, including old UUID replay.
- Reuse Phase 16's exact-document retrieval, selected research profiles, bounded
  SQL/semantic related discovery, current permissions and pre-save source checks.
  Interpretation replaces the second synthesis stage; it does not add another
  model stage or another retrieval system.
- Produce up to four evidence relationships. Each has a cited base claim,
  supporting/contradicting/qualifying passage groups, a cited interpretation and
  optional population/sample, environment, dataset, methodology, time-period,
  sample-size or measurement factors.
- Validate every reference against retrieved evidence. Require two distinct
  papers per relationship; supporting versus contradicting evidence must also
  span distinct papers. Reject unknown/duplicated IDs and overlapping roles.
  Interpretations cite every nonempty role and at least two papers; factors may
  cite only evidence in that relationship. Factor keys cannot repeat.
- The server derives labels: Potential disagreement, Qualified support or
  Supporting evidence. Empty supported relationships return insufficient evidence,
  explicitly not proof of agreement or absence of contradictions.
- Prompts treat all research text and metadata as untrusted. They distinguish
  incompatible findings from mere topic/context differences and require uncertainty
  about proposed explanations. These instructions and reference checks do not
  constitute independent scientific entailment or validity assessment.
- Persist `analysis_type=contradictions` using existing `riq_007` JSON/evidence
  tables. Saved reads and request recovery remain owner-only, recheck selected
  and related sources, and do not leak results through the Compare endpoint.
  No schema, authentication, publication or model-setting change.
- Render generated content as React text. Theme colors, existing focus handling,
  source/page links and evidence inspection are reused. Role columns stack below
  640px; long filenames/text wrap within the existing scrollable dialog.

Free-provider latency and availability remain variable. The shared provider
policy permits at most two attempts per model stage, without stacking retry types
or using paid fallback. Generation remains synchronous; recovery can reopen a
completed request after a disconnect, but cannot restart work interrupted by a
server process restart.

## Verification and recovery

Tests cover ownership/type isolation, private/unpublished selections, citations,
role consistency, insufficient evidence, factors, idempotency, revocation,
rendering and the focus selector. The opt-in live runner uses fabricated PDFs in
an isolated temporary department, including deliberately conflicting findings.
It disconnects the initial POST and recovers the result by request UUID; it also
checks saved results, source revocation, comparison regression and exact fixture
cleanup against original SQL/object/vector snapshots.

```powershell
docker compose exec -T -e PHASE17_LIVE_ACCEPTANCE=1 backend python -m tests.phase17_live_acceptance
```

Previous verified source tag: `researchiq-analyze-recovery-20261024`.
Previous frontend image: `researchiq-frontend:analyze-recovery-20261024`.
No database downgrade is required to revert application code/images; additive
interpretation records can remain at `riq_007`.

Completed: 479 backend tests passed, 43 opt-in tests skipped; 114 frontend tests
passed, TypeScript passed, and the production frontend build passed. Existing
Tailwind/ESLint configuration warnings remain; this is not a clean lint claim.
Synthetic live interpretation passed in 84.61s, including disconnected-request
recovery, related discovery, citations and source revocation. Comparison regression
passed in 39.58s. Cleanup verified original SQL rows, MinIO objects and Chroma IDs
unchanged. The first cold-start run exceeded its indexing wait; its exact synthetic
collection was removed through the lifecycle after indexing completed, then the
full check passed. The harness now allows cold-start indexing/cleanup time.

Deployment health, served assets, OpenAPI focus and anonymous rejection passed.
Browser automation remained unavailable, so rendered visual acceptance is not claimed.
Frontend image: `sha256:ca12b4098f1a5c52156b5919c80729e27d3acc6e20c3fc181157b19795866c0c`.
Recovery image: `researchiq-frontend:phase17-verified-20261025`.
Checkpoint: `researchiq-phase17-evidence-20261025`. No push.
