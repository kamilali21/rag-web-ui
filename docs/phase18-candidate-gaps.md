# Phase 18 — Candidate Research Gaps — 25 October 2026

## Outcome and use

In **Insights**, select 1–5 permitted ready papers, choose **Analyse → Analysis
focus → Candidate research gaps → Generate analysis**. Results appear in the
existing analysis dialog. Expand supporting quotations or inspect evidence
snapshots; citation links open the source/page. Reopen using the saved-analysis
link or Resume last analysis. The separate history browser remains Phase 19.

This implements the amended plan's Phase 18 and original document section 18.
Categories are Limited Evidence, Conflicting Evidence, Understudied Population,
Understudied Location, Understudied Method, Outdated Evidence, Sparse Recent
Evidence and Limited Field Validation. A category is shown only when a candidate
can be supported; the feature does not fill all categories automatically.

## Implementation and boundaries

- Reuse the existing profile stage, exact-document retrieval and bounded related
  public discovery. The gap stage replaces overview synthesis; it does not add a
  third model stage, another RAG store or a schema migration.
- Public/Both can include up to three related public papers from at most twenty
  metadata-filtered candidates. Private scope stays within selected owner papers.
- Generate at most four structured candidates: category, neutral topic, cited
  evidence pattern and short source quotations. Text and metadata are untrusted;
  prompts cannot alter permissions or retrieval scope.
- Validate known, distinct evidence IDs; each candidate includes a selected-paper
  source. Verify every supporting quotation against its retrieved excerpt after
  whitespace normalization. Require one quotation per cited evidence ID. Conflicting
  Evidence requires at least two distinct cited papers. Reject unsupported references,
  invented quotations, duplicate candidates and explicit unqualified novelty wording.
- Server-authored qualification appears on every result: “Candidate research gap
  within the indexed corpus, based only on the retrieved evidence.” Empty output
  means insufficient evidence, not proof that no gaps exist.
- Recency categories conservatively require known publication years for every
  retrieved paper. The explicit five-calendar-year window ends in the generation
  year. Outdated Evidence requires every retrieved paper to predate it; Sparse
  Recent Evidence requires at least one older paper and at most one recent paper.
  This is an operational coverage rule, not a judgment of scientific validity.
  Unknown/future dates prevent these categories. Dates are rechecked after generation.
- Fresh source/readiness/publication checks occur before saving. Existing
  `analysis_runs`/document/evidence snapshots store type `candidate_gaps`; owner-only
  saved reads and UUID recovery recheck sources and remain isolated from Compare.
- Personal AI settings apply automatically through the existing per-request scope;
  bounded provider retry and schema/citation validation remain in place.
- UI reuses analysis cards, labels, buttons, citation links, responsive widths,
  loading/error/recovery behavior and dark-mode tokens. Generated text is rendered
  as React text, never HTML.

Exact quotations and valid citations do not prove a model's interpretation is
scientifically entailed. The wording guard is supplementary, not exhaustive.
Human review and the later RAG evaluation gate remain necessary. A bounded sample
cannot establish global novelty or absence of research across the whole corpus.

## Verification and recovery

Tests cover owner/public readiness boundaries, replay and saved recovery, quote
and citation validation, all eight categories, date coverage, late source/date
changes, insufficient evidence, escaped rendering and the focus selector.
Synthetic live acceptance includes bounded related discovery, cited gap patterns,
source quotations, saved recovery, revocation, comparison regression and cleanup.

Previous source tag: `researchiq-personal-ai-20261025`.
Previous frontend image: `researchiq-frontend:personal-ai-20261025`.
Schema remains `riq_008`; reverting this phase's source/image requires no downgrade.
Keep additive saved gap records. No push is authorized/requested.

Verification completed on 25 October 2026:

- Affected backend suite: 143 passed. Final candidate-gap suite: 30 passed,
  including publication-date changes during generation and safe validation logs.
- Frontend: 120 tests passed across 19 suites; TypeScript check and production
  frontend build passed. Existing ESLint-option/Tailwind warnings remain.
- Live fabricated public/private papers: processing/indexing, bounded related
  discovery and candidate generation passed in 38.64 seconds. The output identified
  multi-season field validation from the papers' explicit single-season limitation
  and future-work statements, with exact source quotations and resolvable citations.
- Saved reopening, idempotency, cross-user denial, recovery after a deliberate
  client disconnect and removal of saved access after related-source revocation
  passed. Comparison regression passed in 34.39 seconds.
- Synthetic cleanup verified exact original SQL rows, MinIO objects and Chroma
  vector IDs unchanged. An earlier generation failed; another attempt started
  before backend readiness and returned 502. Both cleaned up safely. The final
  uninterrupted acceptance run passed without relaxing citation/quote validation.
- Local deployment health, API schema, served gap UI assets and anonymous 401
  rejection passed. No rendered browser inspection is claimed: automation was
  unavailable. This is not an evaluation of scientific accuracy or a guarantee
  of free-provider availability.

Repeatable backend gate: `python -m pytest tests/test_phase18_candidate_gaps.py -q`
in the isolated existing test image. Live gate, from backend:
`PHASE18_LIVE_ACCEPTANCE=1 python -m tests.phase18_live_acceptance`.
Ignored receipts: `.local/tmp/phase18-final.xml`, `phase18-live-receipt.json`,
`phase18-analysis-result.json` and `phase18-live-ready.log` under backend.

Annotated checkpoint: `researchiq-phase18-candidate-gaps-20261025`.
Deployed frontend recovery image: `researchiq-frontend:phase18-verified-20261025`.
Frontend image ID: `sha256:7c38290a0c9ee7b92cd0f3a5149a1871ccbdc3de123a2875affc0b6aaeaa6873`.
Phase 19 remains unstarted. No push.

## Remaining plan, in order

| Phase | Purpose and expected outcome |
| --- | --- |
| 19 — Analysis history | Browse and reopen the user's saved comparisons and analyses. Persistence and individual saved-result links already exist; the history interface is the remaining gate. |
| 20 — Cross-feature security | Exercise OTP abuse, role bypass, private document-ID guessing, prompt injection, upload abuse and output sanitization across the integrated application; correct confirmed defects. |
| 21 — RAG evaluation | Measure retrieval relevance, citation correctness, answer faithfulness, abstention, comparison/analysis quality and latency against a repeatable evaluation set. |
| 22 — Deployment hardening | Verify HTTPS, secrets, coordinated backups/recovery, health checks, rate limits, logging and isolation of internal data services before public deployment. |

Department/supervisor-scoped publication review and supervisor plagiarism/similarity
review remain the previously recorded later extensions, not additional work in
this phase. A candidate-gap feature does not replace plagiarism assessment.
