"""Exact selections retain the existing SQL and native vector boundaries."""
import pytest
from fastapi import HTTPException

from app.models import AcademicDocumentMetadata, Document
from app.models.knowledge import DocumentChunk, ProcessingTask
from app.services.retrieval_scope import search_documents
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider


def test_exact_selection_excludes_other_ready_documents_in_the_same_collection(sources, provider):
    w = sources
    sibling = Document(knowledge_base_id=w.alice_kb.id, file_name="same-name.pdf",
        file_path="sibling.pdf", file_size=10, content_type="application/pdf")
    w.db.add(sibling); w.db.flush()
    w.db.add(ProcessingTask(document_id=sibling.id, knowledge_base_id=w.alice_kb.id, status="completed"))
    w.db.add(DocumentChunk(id=f"chunk-{sibling.id}", document_id=sibling.id, kb_id=w.alice_kb.id,
        file_name=sibling.file_name, hash="sibling", chunk_metadata={"page_content": "Unselected text"}))
    w.db.commit()
    w.source_documents.append(sibling)  # Hostile provider returns this extra candidate too.
    ids = [w.alice_doc.id, w.published.id, w.alice_doc.id]
    result = search_documents(w.db, w.alice, ids, "question", 20)
    assert {r["metadata"]["document_id"] for r in result} == set(ids)
    for kb_id, doc_id in [(w.alice_kb.id, w.alice_doc.id), (w.corpus.id, w.published.id)]:
        provider.stores[kb_id].search_permitted.assert_called_once_with("question", [doc_id], kb_id, k=100)
    assert all(r["content"].startswith("SQL evidence") for r in result)


@pytest.mark.parametrize("selection", [None, [], [True], ["1"], [0], [-1], list(range(1, 22)), "1"])
def test_invalid_selection_never_falls_back_to_scope_search(sources, provider, selection):
    with pytest.raises(HTTPException) as error:
        search_documents(sources.db, sources.alice, selection, "question")
    assert error.value.status_code == 422
    provider.assert_not_called()


@pytest.mark.parametrize("unavailable", ["bob_doc", "draft", "archived", "failed", "fake", "missing"])
def test_one_unavailable_selection_rejects_the_whole_request_before_vectors(sources, provider, unavailable):
    w = sources
    doc_id = 999999 if unavailable == "missing" else getattr(w, unavailable).id
    with pytest.raises(HTTPException) as error:
        search_documents(w.db, w.alice, [w.alice_doc.id, doc_id], "question")
    assert error.value.status_code == 404 and error.value.detail == "Selected documents are unavailable"
    provider.assert_not_called()


def test_selection_cannot_expand_requested_scope(sources, provider):
    with pytest.raises(HTTPException) as error:
        search_documents(sources.db, sources.alice, [sources.published.id], "question", scope="private")
    assert error.value.status_code == 404
    provider.assert_not_called()


def test_selected_source_revocation_aborts_instead_of_returning_a_partial_selection(sources, provider):
    w = sources
    public_id, private_id = w.published.id, w.alice_doc.id
    original = provider.side_effect
    def revoke(**kwargs):
        store = original(**kwargs)
        def search(*args, **kwargs):
            with w.factory() as other:
                other.query(AcademicDocumentMetadata).filter_by(document_id=public_id).one().publication_status = "draft"
                other.commit()
            return store.search_permitted.return_value
        store.search_permitted.side_effect = search
        return store
    provider.side_effect = revoke
    with pytest.raises(HTTPException) as error:
        search_documents(w.db, w.alice, [private_id, public_id], "question")
    assert error.value.status_code == 404


@pytest.mark.parametrize("scope,names", [
    ("private", ["alice_doc"]), ("public", ["published"]),
    ("both", ["alice_doc", "published", "alice_doc"]),
])
def test_http_exact_selection_and_sql_citation_metadata(sources, provider, scope, names):
    w = sources
    ids = [getattr(w, name).id for name in names]
    response = w.client.post("/api/retrieval/documents/query", headers=w.headers(w.alice),
        json={"document_ids": ids, "query": "question", "scope": scope, "top_k": 20})
    assert response.status_code == 200
    rows = response.json()["results"]
    assert {row["metadata"]["document_id"] for row in rows} == set(ids)
    assert len(rows) == len(set(ids))
    for row in rows:
        assert row["content"] == f"SQL evidence {row['metadata']['document_id']}"
        assert row["metadata"]["chunk_id"] == f"chunk-{row['metadata']['document_id']}"
        assert row["metadata"]["page"] == 3 and row["metadata"]["file_name"] != "forged.pdf"


@pytest.mark.parametrize("body", [
    {}, {"document_ids": None}, {"document_ids": []}, {"document_ids": [True]},
    {"document_ids": ["1"]}, {"document_ids": [1.0]}, {"document_ids": [0]},
    {"document_ids": [-1]}, {"document_ids": list(range(1, 22))},
    {"document_ids": "1"}, {"document_ids": [1], "scope": "all"},
    {"document_ids": [1], "knowledge_base_ids": [1]},
    {"document_ids": [1], "query": " "}, {"document_ids": [1], "query": "x" * 4001},
    {"document_ids": [1], "top_k": 0}, {"document_ids": [1], "top_k": 21},
])
def test_http_invalid_selection_is_never_broadened(sources, provider, body):
    response = sources.client.post("/api/retrieval/documents/query", headers=sources.headers(sources.alice),
        json={"query": "question", **body})
    assert response.status_code == 422
    provider.assert_not_called()


@pytest.mark.parametrize("unavailable", ["bob_doc", "draft", "archived", "failed", "missing"])
def test_http_rejects_entire_mixed_selection(sources, provider, unavailable):
    w = sources
    bad_id = 999999 if unavailable == "missing" else getattr(w, unavailable).id
    response = w.client.post("/api/retrieval/documents/query", headers=w.headers(w.alice),
        json={"document_ids": [w.alice_doc.id, bad_id], "query": "question"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Selected documents are unavailable"}
    provider.assert_not_called()


def test_http_requires_auth_and_respects_scope_and_admin_private_boundaries(sources, provider):
    w = sources
    body = {"document_ids": [w.alice_doc.id], "query": "question"}
    assert w.client.post("/api/retrieval/documents/query", json=body).status_code == 401
    for actor in [w.professor, w.superuser]:
        assert w.client.post("/api/retrieval/documents/query", json=body,
            headers=w.headers(actor)).status_code == 404
    assert w.client.post("/api/retrieval/documents/query", json={**body, "scope": "public"},
        headers=w.headers(w.alice)).status_code == 404
    provider.assert_not_called()


def test_http_empty_vectors_and_provider_failure_never_trigger_broad_fallback(sources, provider):
    w = sources
    body = {"document_ids": [w.alice_doc.id], "query": "question"}
    original = provider.side_effect
    def empty(**kwargs):
        store = original(**kwargs)
        store.search_permitted.return_value = []
        return store
    provider.side_effect = empty
    response = w.client.post("/api/retrieval/documents/query", json=body, headers=w.headers(w.alice))
    assert response.status_code == 200 and response.json() == {"results": []}
    provider.side_effect = RuntimeError("private provider secret")
    response = w.client.post("/api/retrieval/documents/query", json=body, headers=w.headers(w.alice))
    assert response.status_code == 503 and response.json() == {"detail": "Scoped retrieval unavailable"}
