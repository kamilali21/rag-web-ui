"""SQL and provider boundaries for Public / Private / Both retrieval."""
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock
from langchain_core.documents import Document as Evidence

from app.models import AcademicDocumentMetadata, Document
from app.models.knowledge import ProcessingTask, DocumentChunk
from app.services import retrieval_scope as retrieval
from app.services.public_corpus import provision_corpus
from app.services.retrieval_scope import resolve_scope
from tests.test_phase2_authorization import world


@pytest.fixture
def sources(world):
    w = world
    w.corpus = provision_corpus(w.db)
    def doc(kb, name, publication, state="completed"):
        row = Document(knowledge_base_id=kb.id, file_name=name, file_path=f"kb_{kb.id}/{name}", file_size=12, content_type="text/plain")
        row.academic_metadata = AcademicDocumentMetadata(title=name, publication_status=publication)
        w.db.add(row); w.db.flush()
        w.db.add(ProcessingTask(knowledge_base_id=kb.id, document_id=row.id, status=state))
        return row
    w.published = doc(w.corpus, "published.txt", "published")
    w.draft = doc(w.corpus, "draft.txt", "draft")
    w.archived = doc(w.corpus, "archived.txt", "archived")
    w.fake = doc(w.fake_public, "fake-public.txt", "published")
    w.failed = doc(w.corpus, "failed.txt", "published", "failed")
    for row in [w.alice_doc, w.bob_doc]:
        w.db.add(ProcessingTask(knowledge_base_id=row.knowledge_base_id, document_id=row.id, status="completed"))
    w.source_documents = [w.alice_doc, w.bob_doc, w.published, w.draft, w.archived, w.fake, w.failed]
    for row in w.source_documents:
        w.db.add(DocumentChunk(id=f"chunk-{row.id}", kb_id=row.knowledge_base_id, document_id=row.id,
            file_name=row.file_name, hash=f"hash-{row.id}",
            chunk_metadata={"page_content": f"SQL evidence {row.id}", "page": 3}))
    w.db.commit()
    return w


def test_each_scope_selects_only_owned_private_and_published_system_sources(sources):
    w = sources
    private = {w.alice_kb.id: [w.alice_doc.id]}
    public = {w.corpus.id: [w.published.id]}
    assert resolve_scope(w.db, w.alice, "private") == private
    assert resolve_scope(w.db, w.alice, "public") == public
    assert resolve_scope(w.db, w.alice, "both") == {**private, **public}
    assert resolve_scope(w.db, w.bob, "both") == {w.bob_kb.id: [w.bob_doc.id], **public}


@pytest.mark.parametrize("actor", ["professor", "superuser"])
def test_admin_and_legacy_superuser_cannot_expand_private_scope(sources, actor):
    w = sources
    assert resolve_scope(w.db, getattr(w, actor), "private") == {}
    assert resolve_scope(w.db, getattr(w, actor), "both") == {w.corpus.id: [w.published.id]}


def test_latest_attempt_and_publication_changes_remove_sources(sources):
    w = sources
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_id=w.alice_doc.id, status="failed"))
    w.published.academic_metadata.publication_status = "draft"
    w.db.commit()
    assert resolve_scope(w.db, w.alice, "both") == {}


@pytest.mark.parametrize("actor", ["inactive", "system"])
def test_inactive_and_system_actors_are_rejected_before_resolving(sources, actor):
    with pytest.raises(HTTPException) as error:
        resolve_scope(sources.db, getattr(sources, actor), "both")
    assert error.value.status_code == 401


def test_unknown_scope_never_falls_back_to_all_sources(sources):
    with pytest.raises(HTTPException) as error:
        resolve_scope(sources.db, sources.alice, "selected_documents")
    assert error.value.status_code == 422


@pytest.fixture
def provider(sources, monkeypatch):
    factory = MagicMock()
    def store(**kwargs):
        kb_id = int(kwargs["collection_name"].split("_")[1])
        result = MagicMock()
        # Deliberately hostile provider: ignores the filter and returns all known
        # chunk IDs with forged text/metadata. SQL must still enforce the boundary.
        result.search_permitted.return_value = [(Evidence(page_content="FORGED SECRET",
            metadata={"chunk_id": f"chunk-{doc.id}", "kb_id": 999, "file_name": "forged.pdf"}), 0.1)
            for doc in sources.source_documents]
        factory.stores[kb_id] = result
        return result
    factory.stores = {}
    factory.side_effect = store
    monkeypatch.setattr(retrieval.EmbeddingsFactory, "create", MagicMock())
    monkeypatch.setattr(retrieval.VectorStoreFactory, "create", factory)
    return factory


@pytest.mark.parametrize("scope", ["private", "public", "both"])
def test_filter_is_passed_before_search_and_sql_rehydrates_evidence(sources, provider, scope):
    w = sources
    allowed = resolve_scope(w.db, w.alice, scope)
    results = retrieval.search_scope(w.db, w.alice, scope, "irrigation", 20)
    assert {r["metadata"]["document_id"] for r in results} == {d for ids in allowed.values() for d in ids}
    assert set(provider.stores) == set(allowed)
    for kb_id, ids in allowed.items():
        provider.stores[kb_id].search_permitted.assert_called_once_with("irrigation", ids, kb_id, k=100)
    for result in results:
        assert result["content"] == f"SQL evidence {result['metadata']['document_id']}"
        assert result["metadata"]["file_name"] != "forged.pdf"
        assert result["metadata"]["page"] == 3


def test_empty_scope_never_opens_a_provider(sources, provider):
    assert retrieval.search_scope(sources.db, sources.professor, "private", "empty") == []
    provider.assert_not_called()
    retrieval.EmbeddingsFactory.create.assert_not_called()


@pytest.mark.parametrize("change", ["unpublish", "owner", "inactive", "failed"])
def test_revocation_during_provider_call_is_seen_in_fresh_sql_snapshot(sources, provider, change):
    w = sources
    actor_id, corpus_id, public_id, private_id, alice_kb_id, bob_id = (
        w.alice.id, w.corpus.id, w.published.id, w.alice_doc.id, w.alice_kb.id, w.bob.id)
    original = provider.side_effect
    def changed_store(**kwargs):
        store = original(**kwargs)
        hits = store.search_permitted.return_value
        def search(*args, **kwargs):
            # Separate connection/session exercises MySQL REPEATABLE READ in the
            # optional real-engine gate, as well as SQLite in the isolated suite.
            with w.factory() as other:
                if change == "unpublish":
                    other.query(AcademicDocumentMetadata).filter_by(document_id=public_id).one().publication_status = "draft"
                elif change == "owner":
                    from app.models import KnowledgeBase
                    other.get(KnowledgeBase, alice_kb_id).user_id = bob_id
                elif change == "inactive":
                    from app.models import User
                    other.get(User, actor_id).is_active = False
                else:
                    other.add(ProcessingTask(knowledge_base_id=alice_kb_id, document_id=private_id, status="failed"))
                other.commit()
            return hits
        store.search_permitted.side_effect = search
        return store
    provider.side_effect = changed_store
    if change == "inactive":
        with pytest.raises(HTTPException) as error:
            retrieval.search_scope(w.db, w.alice, "both", "revoked")
        assert error.value.status_code == 401
    else:
        result = retrieval.search_scope(w.db, w.alice, "both", "revoked")
        expected = private_id if change == "unpublish" else public_id
        assert {row["metadata"]["document_id"] for row in result} == {expected}


def test_foreign_selected_collection_rejected_before_provider(sources, provider):
    with pytest.raises(HTTPException) as error:
        retrieval.search_scope(sources.db, sources.alice, "private", "secret", knowledge_base_ids=[sources.bob_kb.id])
    assert error.value.status_code == 404
    provider.assert_not_called()


def test_provider_failure_is_closed_and_does_not_disclose_details(sources, provider):
    provider.side_effect = RuntimeError("secret provider token")
    with pytest.raises(HTTPException) as error:
        retrieval.search_scope(sources.db, sources.alice, "both", "question")
    assert error.value.status_code == 503
    assert "secret" not in str(error.value.detail)


def test_scores_are_merged_bounded_and_deduplicated_across_collections(sources, provider):
    w = sources
    original = provider.side_effect
    def ranked(**kwargs):
        store = original(**kwargs)
        store.search_permitted.return_value = [
            (Evidence(page_content="ignored", metadata={"chunk_id": f"chunk-{w.alice_doc.id}"}), 0.8),
            (Evidence(page_content="ignored", metadata={"chunk_id": f"chunk-{w.published.id}"}), 0.1),
            (Evidence(page_content="ignored", metadata={"chunk_id": f"chunk-{w.published.id}"}), 0.2),
            (Evidence(page_content="ignored", metadata={"chunk_id": "missing"}), -1),
            (Evidence(page_content="ignored", metadata={"chunk_id": f"chunk-{w.alice_doc.id}"}), float("nan")),
        ]
        return store
    provider.side_effect = ranked
    result = retrieval.search_scope(w.db, w.alice, "both", "rank", 1)
    assert len(result) == 1 and result[0]["metadata"]["document_id"] == w.published.id
    assert result[0]["score"] == 0.1


def test_chat_with_no_trusted_evidence_does_not_generate_an_answer(sources, provider, monkeypatch):
    from app.services import chat_service
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    w = sources
    original = provider.side_effect
    def empty(**kwargs):
        store = original(**kwargs)
        store.search_permitted.return_value = []
        return store
    provider.side_effect = empty
    model = FakeListChatModel(responses=["Must not be generated"])
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: model)
    response = w.client.post(f"/api/chat/{w.chat.id}/messages", json={"messages": [
        {"role": "user", "content": "A question without evidence"}]}, headers=w.headers(w.alice))
    assert "insufficient evidence" in response.text and "Must not be generated" not in response.text
    assert "__LLM_RESPONSE__" not in response.text and 'd:' in response.text


@pytest.mark.parametrize("body", [
    {"query": "test", "scope": "all"}, {"query": "test", "document_ids": [1]},
    {"query": " "}, {"query": "test", "top_k": 0}, {"query": "test", "top_k": 21}])
def test_http_rejects_invalid_or_client_supplied_authorization(sources, provider, body):
    assert sources.client.post("/api/retrieval/query", json=body, headers=sources.headers(sources.alice)).status_code == 422
    provider.assert_not_called()


def test_http_authentication_and_both_scope(sources, provider):
    w = sources
    assert w.client.post("/api/retrieval/query", json={"query": "q"}).status_code == 401
    response = w.client.post("/api/retrieval/query", json={"query": "q", "scope": "both"}, headers=w.headers(w.alice))
    assert response.status_code == 200
    assert {r["metadata"]["document_id"] for r in response.json()["results"]} == {w.alice_doc.id, w.published.id}


def test_native_vector_adapters_push_filters_down_and_empty_never_searches():
    from app.services.vector_store.chroma import ChromaVectorStore
    from app.services.vector_store.qdrant import QdrantStore
    for adapter in [ChromaVectorStore, QdrantStore]:
        store = object.__new__(adapter)
        store._store = MagicMock()
        store._store.similarity_search_with_score.return_value = [(Evidence(page_content="text"), 0.8)]
        assert store.search_permitted("q", [], 11) == []
        store._store.similarity_search_with_score.assert_not_called()
        rows = store.search_permitted("q", [12, 13], 11, k=7)
        args = store._store.similarity_search_with_score.call_args
        assert args.kwargs["k"] == 7
        condition = args.kwargs["filter"]
        if adapter is ChromaVectorStore:
            assert condition == {"$and": [{"kb_id": 11}, {"document_id": {"$in": [12, 13]}}]}
            assert rows[0][1] == 0.8
        else:
            assert condition.must[0].key == "metadata.kb_id" and condition.must[0].match.value == 11
            assert condition.must[1].key == "metadata.document_id" and condition.must[1].match.any == [12, 13]
            assert rows[0][1] == -0.8
