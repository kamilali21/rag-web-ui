# Future extensions recorded 19 October 2026

These user-requested additions are planned only. They do not change current
administrator rights or activate plagiarism checking in Phase 14. Keep the
existing Phases 14–22 and completed checkpoint numbers unchanged; schedule
these extensions in a later approved gate.

## Department and supervisor review boundaries

When department administrators/supervisors are introduced, their Dashboard queue
and pending count must include only students assigned to their supervision in
their authorized department. Use explicit, administrator-managed department and
student/supervisor assignments, not a student's self-edited profile department
or a free-text supervisor name as authorization evidence.

Enforce the same scope on queue/count, request details, profile/photo access,
exact-request document download, metadata edits, approve/deny, retry, and
withdrawal review. Reject guessed IDs outside the assignment. Never extend
generic private-library access. Define reassignment, revoked supervision,
unassigned requests, and any central-administrator exception explicitly before
implementation, with an audit trail and separate permissions.

Gate: tests and synthetic live acceptance for same-department/different-supervisor,
different-department, reassigned, revoked and unassigned students; counts must
match eligible requests and all out-of-scope review actions must fail closed.

## Supervisor-assisted similarity / plagiarism review

Reuse the existing parsing, embeddings, permitted retrieval and citation system
to surface possible textual overlap in the exact submitted paper and authorized
comparison corpus. Show matching passages, source/page citations, corpus coverage,
and limitations for a human supervisor to review. Do not describe a RAG/LLM
similarity signal as a definitive plagiarism verdict or a whole-internet check;
quotations, references and legitimate shared terminology require interpretation.

Keep access within explicit review assignments; never expose unrelated private
papers. No automatic denial, disciplinary decision, or third-party document
upload. Decide report persistence, retention, rubric and review policy in that
future gate. Evaluate false positives, quoted/cited overlap, paraphrase limits,
prompt injection, missing evidence and permission boundaries before release.
