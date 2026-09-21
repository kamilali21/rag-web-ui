# Phase 5: Academic Metadata

<!-- Added by ChatGPT: Phase 5 contracts, validation and preservation boundaries. -->

## Scope

Wire the existing `departments` and `academic_document_metadata` tables to the
Phase 4 corpus. No migration, new dependency, file duplication or vector rebuild.
The migration head remains `riq_004`. Public Library search/bookmarks/UI are
Phase 6; admin entry forms are Phase 7; private-library parity is Phase 8.
There is no automatic metadata extraction, DOI lookup or LLM generation.

## API

All routes use the existing authenticated session and mutation Origin/CSRF checks.
An administrator requires both the explicit role and active exact-email allowlist;
neither university email nor superuser status substitutes for these checks.

| Route | Contract |
| --- | --- |
| `GET /api/departments` | Active reference data; `after_id` cursor, `limit` 1-100. Admin may request `include_inactive=true`. |
| `GET /api/departments/{id}` | Authenticated historical lookup, including inactive departments. |
| `POST /api/departments` | Admin create: `name`, `code`, optional boolean `is_active`. |
| `PATCH /api/departments/{id}` | Admin edit name/code/active flag. No hard-delete endpoint. |
| `GET /api/corpus/documents/{id}/metadata` | Published metadata only; admin may request `include_unpublished=true`. |
| `PATCH /api/corpus/documents/{id}/metadata` | Admin partial academic edit on a completed, non-archived corpus document. |

No endpoint grants access to private documents, including an admin's own private
documents. Those retain their original private KB APIs. Academic reads/updates
recheck canonical system ownership. Publication and filename changes still use
the separate Phase 4 lifecycle endpoints.

## Validation

- Unknown fields are rejected. Ownership, document IDs, object paths, task state,
  publication state and timestamps cannot be changed through metadata PATCH.
- Omitted fields are preserved. Explicit `null` clears optional fields; the title
  cannot be cleared. Empty patches are rejected. All edits are transactional.
- Title: trimmed, 1-500 characters. The initial ingestion filename remains the
  fallback until an admin supplies a research title; no inferred bibliography.
- Authors: free text up to 8,000 characters; abstract up to 16,000; supervisor up
  to 255. Optional blank strings become null. Control characters are rejected,
  apart from ordinary tabs/newlines. These are plain text, never trusted HTML.
- Types: `paper`, `thesis`, `report`, `other`, or null. Extend this explicit
  vocabulary deliberately when real catalog requirements call for it.
- Year: an integer from 1000 to 9999, matching the existing constraint. Dates must
  be real `YYYY-MM-DD` calendar dates within that range. If both exist, their
  years must match, including when only one is patched. Dates need not be past.
- Keywords: null or an array of at most 20 strings, each 1-100 characters.
  Trimmed and deduplicated case-insensitively, preserving the first spelling.
- Department: positive integer ID of an active department when assigned. Existing
  inactive references remain readable; unrelated edits and clearing are allowed.
- DOI: optional bare `10.<4-9 digits>/<non-whitespace suffix>` identifier, up to
  255 characters. This is syntax validation, not proof the DOI exists.
- Language: optional 2-8 letter primary tag with bounded alphanumeric subtags,
  at most 35 characters. This is not a complete language-registry validator.
- Department names: normalized whitespace, 1-150 characters. Codes: uppercase,
  1-32 ASCII letters/digits/underscore/hyphen, starting with a letter or digit.
  Existing database unique constraints arbitrate concurrent duplicates; conflicts
  return 409. PATCH cannot null out department fields.

Department rows are not guessed or seeded from an unofficial UAF list. An
authorized administrator enters the actual institutional names/codes. Deactivate
instead of deleting so historical metadata and allowlist references remain valid.

## Consistency And Recovery

Metadata updates reuse the corpus write mutex and current document/metadata/task
row locks. They never change publication status, files, chunk IDs/text, vectors or
the existing citation format. Distinct-field concurrent PATCHes preserve each
other; concurrent edits of the same field are serialized, last writer wins.
Department assignment locks the department row against simultaneous deactivation.

Edits to an already published document are immediately visible; no editorial
revision/history workflow is introduced. Admin forms should submit only changed
fields. Catalog joins/search and exposing metadata in citation UX remain later
phases. Current corpus retrieval still uses file identity and authorized chunks.

Run `test_phase5_academic_metadata.py` together with Phase 4, 3, 2 and baseline
tests using the isolated-runtime instructions in `implementation-progress.md`.
MySQL concurrency coverage uses the guarded disposable `researchiq_phase2_test`
database only. Never point these destructive fixtures at the application database.

Recovery source: `eee6c37`, tag `researchiq-pre-phase5-20260921`. Reverting Phase 5
code requires no schema downgrade and must retain all department/metadata rows,
private data, MinIO objects and Chroma `/data`. The user-requested admin appointment
is a separate data operation: source rollback does not revoke it. Explicit
revocation can deactivate the exact allowlist entry or remove only that admin
role; never alter researcher ownership or authentication credentials to revoke it.
