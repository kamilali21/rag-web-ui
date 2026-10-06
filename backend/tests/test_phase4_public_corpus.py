"""Added by ChatGPT: real HTTP/ORM/ingestion tests with isolated storage/provider fixtures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from langchain_core.documents import Document as Evidence

from app.models import AcademicDocumentMetadata, Document, DocumentChunk, KnowledgeBase, User
from app.models.knowledge import DocumentUpload, ProcessingTask
from app.services import public_corpus as service, document_processor
from tests.test_phase2_authorization import world
from tests.test_phase3_authentication import otp, login, csrf


class Storage:
    def __init__(self):
        self.objects = {}
        self.fail_delete = False

    def put_object(self, bucket_name, object_name, data, length, **kwargs):
        self.objects[object_name] = data.read(length)

    def fget_object(self, bucket_name, object_name, file_path):
        Path(file_path).write_bytes(self.objects[object_name])

    def copy_object(self, bucket_name, object_name, source):
        self.objects[object_name] = self.objects[source.object_name]

    def remove_object(self, bucket_name, object_name):
        if self.fail_delete:
            raise RuntimeError("secret provider failure")
        self.objects.pop(object_name, None)

    def get_object(self, bucket_name, object_name):
        response = MagicMock()
        response.stream.return_value = [self.objects[object_name]]
        return response


class Store:
    def __init__(self):
        self.documents = {}
        self.fail_add = False
        self.fail_delete = False
        self.extra = []

    def add_documents(self, documents):
        for document in documents:
            self.documents[document.metadata["chunk_id"]] = document
        if self.fail_add:
            raise RuntimeError("secret embedding error")

    def delete(self, ids):
        if self.fail_delete:
            raise RuntimeError("secret vector failure")
        for chunk_id in ids:
            self.documents.pop(chunk_id, None)

    def similarity_search_with_score(self, query, k):
        return (self.extra + [(doc, 0.1) for doc in self.documents.values()])[:k]

    def search_permitted(self, query, document_ids, kb_id, k=4):
        return [(doc, score) for doc, score in self.similarity_search_with_score(query, k)
                if doc.metadata.get("document_id") in document_ids and doc.metadata.get("kb_id") == kb_id]


@pytest.fixture
def corpus(world, monkeypatch):
    w = world
    w.corpus = service.provision_corpus(w.db)
    w.storage, w.store = Storage(), Store()
    monkeypatch.setattr(service, "SessionLocal", w.factory)
    monkeypatch.setattr(service, "get_minio_client", lambda: w.storage)
    monkeypatch.setattr(document_processor, "get_minio_client", lambda: w.storage)
    monkeypatch.setattr(service.EmbeddingsFactory, "create", lambda: object())
    monkeypatch.setattr(service.VectorStoreFactory, "create", lambda **kwargs: w.store)
    return w


def upload(w, name="research.txt", content=b"Synthetic UAF irrigation evidence."):
    result = w.client.post("/api/corpus/documents/upload", files={"file": (name, content, "text/plain")},
                           headers=w.headers(w.professor))
    assert result.status_code == 202, result.text
    task_id = result.json()["id"]
    status = w.client.get(f"/api/corpus/tasks/{task_id}", headers=w.headers(w.professor))
    w.db.rollback()
    return status.json()


def publish(w, document_id):
    result = w.client.post(f"/api/corpus/documents/{document_id}/publish", headers=w.headers(w.professor))
    assert result.status_code == 200, result.text
    w.db.rollback()


def test_provisioning_is_idempotent_and_system_owned(corpus):
    w = corpus
    again = service.provision_corpus(w.db)
    assert again.id == w.corpus.id and again.name == service.CORPUS_NAME
    owner = w.db.get(User, again.user_id)
    assert owner.username == service.SYSTEM_USERNAME and owner.email == service.SYSTEM_EMAIL
    assert owner.is_system and not owner.is_active and not owner.is_superuser
    assert owner.hashed_password is None and not owner.roles and not owner.api_keys
    assert again.scope == "public" and again.is_system_managed
    for actor in [w.alice, w.professor]:
        result = w.client.get("/api/corpus", headers=w.headers(actor))
        assert result.status_code == 200 and result.json()["user_id"] == owner.id
        private = w.client.get("/api/knowledge-base", headers=w.headers(actor)).json()
        assert again.id not in {kb["id"] for kb in private}
    assert w.client.post("/api/auth/token", data={"username": owner.username, "password": "anything"}).status_code == 401
    assert w.client.get("/api/corpus", headers=w.headers(owner)).status_code == 401
    assert w.client.post("/api/corpus", headers=w.headers(w.professor)).json()["id"] == again.id


@pytest.mark.parametrize("collision", ["username", "email", "accent", "padding"])
def test_provisioning_never_converts_or_claims_a_human(world, collision):
    w = world
    if collision == "username": w.alice.username = service.SYSTEM_USERNAME
    elif collision == "email": w.alice.email = service.SYSTEM_EMAIL
    elif collision == "accent": w.alice.username = "r\u00e9searchiq_system"
    else: w.alice.username = service.SYSTEM_USERNAME + " "
    if collision in {"accent", "padding"} and w.engine.dialect.name != "mysql":
        pytest.skip("MySQL collation collision")
    w.db.commit()
    original_owner = w.alice_kb.user_id
    collides = w.db.query(User).filter((User.username == service.SYSTEM_USERNAME) | (User.email == service.SYSTEM_EMAIL)).first()
    if collides:
        with pytest.raises(HTTPException) as error:
            service.provision_corpus(w.db)
        assert error.value.status_code == 503
    else:
        # MySQL NO PAD collations treat the padded username as a distinct identity.
        assert service.provision_corpus(w.db).user_id != w.alice.id
    w.db.expire_all()
    assert not w.alice.is_system and w.alice.is_active and w.alice.hashed_password
    assert w.alice_kb.user_id == original_owner and w.alice_kb.scope == "private"


@pytest.mark.parametrize("actor", ["alice", "superuser"])
def test_researchers_cannot_manage_corpus(corpus, actor):
    w = corpus
    headers = w.headers(getattr(w, actor))
    for method, path, kwargs in [
        ("POST", "/api/corpus", {}),
        ("GET", "/api/corpus/documents?include_unpublished=true", {}),
        ("POST", "/api/corpus/documents/upload", {"files": {"file": ("test.txt", b"test", "text/plain")}}),
        ("GET", "/api/corpus/tasks/1", {}), ("POST", "/api/corpus/tasks/1/retry", {}),
        ("DELETE", "/api/corpus/tasks/1", {}), ("PATCH", "/api/corpus/documents/1", {"json": {"file_name": "rename.txt"}}),
        ("POST", "/api/corpus/documents/1/publish", {}), ("POST", "/api/corpus/documents/1/unpublish", {}),
        ("DELETE", "/api/corpus/documents/1", {})]:
        result = w.client.request(method, path, headers=headers, **kwargs)
        assert result.status_code == 403, (path, result.text)
    assert not w.storage.objects and not w.store.documents
    with pytest.raises(HTTPException):
        service.set_publication(w.db, getattr(w, actor), w.bob_doc.id, True)


def test_full_upload_publish_read_query_rename_unpublish_delete(corpus):
    w = corpus
    result = upload(w)
    assert result["status"] == "completed", result
    doc_id = result["document_id"]
    reader, admin = w.headers(w.alice), w.headers(w.professor)
    assert w.client.get("/api/corpus/documents", headers=reader).json() == []
    assert w.client.get(f"/api/corpus/documents/{doc_id}", headers=reader).status_code == 404
    assert w.client.get(f"/api/corpus/documents/{doc_id}/content?include_unpublished=true", headers=reader).status_code == 403
    assert w.client.get(f"/api/corpus/documents/{doc_id}/content?include_unpublished=true", headers=admin).status_code == 200
    assert w.client.post("/api/corpus/query", headers=reader, json={"query": "irrigation"}).json() == {"results": []}
    assert w.client.get("/api/corpus/documents?include_unpublished=true", headers=admin).json()[0]["publication_status"] == "draft"
    publish(w, doc_id)
    listed = w.client.get("/api/corpus/documents", headers=reader).json()
    assert [doc["id"] for doc in listed] == [doc_id] and "file_path" not in listed[0]
    download = w.client.get(f"/api/corpus/documents/{doc_id}/content", headers=reader)
    assert download.status_code == 200 and download.content == b"Synthetic UAF irrigation evidence."
    assert download.headers["X-Content-Type-Options"] == "nosniff"
    evidence = w.client.post("/api/corpus/query", headers=reader, json={"query": "irrigation"}).json()["results"]
    assert len(evidence) == 1 and evidence[0]["metadata"]["document_id"] == doc_id
    assert evidence[0]["content"] == "Synthetic UAF irrigation evidence."
    original_path = w.db.get(Document, doc_id).file_path
    w.db.rollback()
    renamed = w.client.patch(f"/api/corpus/documents/{doc_id}", headers=admin, json={"file_name": "renamed.txt"})
    assert renamed.status_code == 200
    assert w.db.get(Document, doc_id).file_path == original_path
    w.db.rollback()
    # Renaming must not allow another upload to overwrite the immutable source object.
    duplicate = w.client.post("/api/corpus/documents/upload", headers=admin,
                               files={"file": ("research.txt", b"replacement", "text/plain")})
    assert duplicate.status_code == 409
    evidence = w.client.post("/api/corpus/query", headers=reader, json={"query": "irrigation"}).json()["results"]
    assert evidence[0]["metadata"]["file_name"] == "renamed.txt"
    assert w.client.post(f"/api/corpus/documents/{doc_id}/unpublish", headers=admin).status_code == 200
    assert w.client.get(f"/api/corpus/documents/{doc_id}/content", headers=reader).status_code == 404
    publish(w, doc_id)
    assert w.client.delete(f"/api/corpus/documents/{doc_id}", headers=admin).status_code == 200
    w.db.rollback()
    assert w.db.get(Document, doc_id) is None
    assert not w.storage.objects and not w.store.documents
    assert w.db.query(DocumentUpload).filter_by(knowledge_base_id=w.corpus.id).count() == 0
    assert w.db.get(Document, w.bob_doc.id) is not None


def test_public_query_rejects_drafts_private_stale_and_forged_vector_content(corpus):
    w = corpus
    published = upload(w, "published.txt", b"Public evidence from SQL.")
    upload(w, "draft.txt", b"Draft secret.")
    publish(w, published["document_id"])
    chunk = w.db.query(DocumentChunk).filter_by(document_id=published["document_id"]).one()
    w.store.extra = [(Evidence(page_content="Forged secret from vectors", metadata={"chunk_id": chunk.id}), 0.0),
                     (Evidence(page_content="Foreign private secret", metadata={"chunk_id": "missing-private-chunk"}), 0.0)]
    w.db.rollback()
    result = w.client.post("/api/corpus/query", headers=w.headers(w.alice), json={"query": "evidence"})
    assert result.status_code == 200
    assert [doc["content"] for doc in result.json()["results"]] == ["Public evidence from SQL."]
    assert "secret" not in result.text


@pytest.mark.parametrize("failure", ["vector", "object"])
def test_cleanup_failure_hides_document_and_retains_retryable_records(corpus, failure):
    w = corpus
    doc_id = upload(w)["document_id"]
    publish(w, doc_id)
    failing = w.store if failure == "vector" else w.storage
    failing.fail_delete = True
    result = w.client.delete(f"/api/corpus/documents/{doc_id}", headers=w.headers(w.professor))
    assert result.status_code == 503 and "secret" not in result.text
    w.db.rollback()
    assert w.db.get(Document, doc_id).academic_metadata.publication_status == "archived"
    w.db.rollback()
    assert w.client.get(f"/api/corpus/documents/{doc_id}", headers=w.headers(w.alice)).status_code == 404
    assert w.client.post(f"/api/corpus/documents/{doc_id}/publish", headers=w.headers(w.professor)).status_code == 409
    failing.fail_delete = False
    assert w.client.delete(f"/api/corpus/documents/{doc_id}", headers=w.headers(w.professor)).status_code == 200


def test_failed_partial_ingestion_is_hidden_and_retry_reuses_retained_source(corpus):
    w = corpus
    w.store.fail_add = True
    task = upload(w)
    assert task["status"] == "failed" and task["document_id"]
    assert "secret" not in task["error_message"]
    assert w.client.post(f"/api/corpus/documents/{task['document_id']}/publish", headers=w.headers(w.professor)).status_code == 409
    w.store.fail_add = False
    result = w.client.post(f"/api/corpus/tasks/{task['id']}/retry", headers=w.headers(w.professor))
    assert result.status_code == 202, result.text
    status = w.client.get(f"/api/corpus/tasks/{task['id']}", headers=w.headers(w.professor)).json()
    assert status["status"] == "completed", status
    w.db.rollback()
    assert w.db.query(Document).filter_by(knowledge_base_id=w.corpus.id).count() == 1
    assert w.client.get("/api/corpus/documents", headers=w.headers(w.alice)).json() == []
    publish(w, status["document_id"])


def test_revoked_admin_cannot_enqueue_or_continue_ingestion(corpus, monkeypatch):
    w = corpus
    worker = service.process_upload
    monkeypatch.setattr(service, "process_upload", lambda *args: None)
    task = upload(w)
    assert task["status"] == "pending"
    w.professor.roles.remove(w.admin)
    w.db.commit()
    worker(task["id"], w.professor.id)
    w.db.rollback()
    assert w.db.get(ProcessingTask, task["id"]).status == "failed"
    assert not w.store.documents
    assert w.client.post("/api/corpus/documents/upload", headers=w.headers(w.professor),
                         files={"file": ("another.txt", b"test", "text/plain")}).status_code == 403


def test_corpus_endpoints_never_expose_foreign_private_documents(corpus):
    w = corpus
    for actor in [w.alice, w.professor]:
        headers = w.headers(actor)
        for suffix in ["", "/content"]:
            assert w.client.get(f"/api/corpus/documents/{w.bob_doc.id}{suffix}", headers=headers).status_code == 404
    for method, suffix, kwargs in [("PATCH", "", {"json": {"file_name": "hijacked.pdf"}}),
                                    ("DELETE", "", {}), ("POST", "/publish", {}), ("POST", "/unpublish", {})]:
        assert w.client.request(method, f"/api/corpus/documents/{w.bob_doc.id}{suffix}",
                                 headers=w.headers(w.professor), **kwargs).status_code == 404
    assert w.client.get(f"/api/corpus/tasks/{w.task.id}", headers=w.headers(w.professor)).status_code == 404
    assert w.client.post(f"/api/corpus/tasks/{w.task.id}/retry", headers=w.headers(w.professor)).status_code == 404
    assert w.client.delete(f"/api/corpus/tasks/{w.task.id}", headers=w.headers(w.professor)).status_code == 404
    assert not w.storage.objects and not w.store.documents


@pytest.mark.parametrize("name,content,code", [("../bad.txt", b"test", 400), ("bad.exe", b"test", 400),
    ("bad.pdf", b"not a pdf", 400), ("bad.docx", b"not a docx", 400), ("empty.txt", b"", 413)])
def test_upload_validation_precedes_storage(corpus, name, content, code):
    w = corpus
    result = w.client.post("/api/corpus/documents/upload", headers=w.headers(w.professor),
                           files={"file": (name, content, "text/plain")})
    assert result.status_code == code
    assert not w.storage.objects


def test_cookie_authenticated_corpus_keeps_csrf_and_private_isolation(otp, monkeypatch):
    w = otp
    kb = service.provision_corpus(w.db)
    login(w)
    assert w.client.get("/api/corpus").json()["id"] == kb.id
    assert w.client.post("/api/corpus/query", json={"query": "test"}).status_code == 403
    assert w.client.post("/api/corpus/query", json={"query": "test"}, headers=csrf(w)).json() == {"results": []}
    assert w.client.post("/api/corpus", headers=csrf(w)).status_code == 403
    assert w.client.get(f"/api/knowledge-base/{w.bob_kb.id}").status_code == 404


def test_mysql_concurrent_provisioning_has_one_owner_and_one_corpus(world):
    w = world
    if w.engine.dialect.name != "mysql": pytest.skip("Concurrent provisioning requires MySQL")
    barrier = Barrier(2)
    def provision(_):
        with w.factory() as db:
            barrier.wait(timeout=10)
            return service.provision_corpus(db).id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(provision, range(2)))
    assert len(set(ids)) == 1
    assert w.db.query(User).filter_by(username=service.SYSTEM_USERNAME).count() == 1
    assert w.db.query(KnowledgeBase).filter_by(id=ids[0]).count() == 1


def test_failed_upload_without_document_can_be_removed(corpus, monkeypatch):
    w = corpus
    monkeypatch.setattr(document_processor, "TextLoader", MagicMock(side_effect=RuntimeError("bad parser")))
    task = upload(w)
    assert task["status"] == "failed" and task["document_id"] is None
    assert w.storage.objects
    # A copy can succeed before document SQL creation fails; this output must also be cleaned.
    w.storage.objects[f"kb_{w.corpus.id}/research.txt"] = b"orphaned copy"
    result = w.client.delete(f"/api/corpus/tasks/{task['id']}", headers=w.headers(w.professor))
    assert result.status_code == 200, result.text
    w.db.rollback()
    assert w.db.get(ProcessingTask, task["id"]) is None and not w.storage.objects


def test_owner_corruption_fails_closed_without_exposing_public_rows(corpus):
    w = corpus
    doc_id = upload(w)["document_id"]
    publish(w, doc_id)
    w.corpus.user_id = w.professor.id
    w.db.commit()
    assert w.client.get("/api/corpus", headers=w.headers(w.alice)).status_code == 503
    assert w.client.get(f"/api/corpus/documents/{doc_id}", headers=w.headers(w.alice)).status_code == 503
    assert w.client.post("/api/corpus/query", headers=w.headers(w.alice), json={"query": "secret"}).status_code == 503


def test_query_rechecks_publication_after_vector_call(corpus, monkeypatch):
    w = corpus
    doc_id = upload(w)["document_id"]
    publish(w, doc_id)
    search = w.store.similarity_search_with_score
    def unpublish_during_search(query, k):
        candidates = search(query, k)
        with w.factory() as db:
            service.set_publication(db, db.get(User, w.professor.id), doc_id, False)
        return candidates
    monkeypatch.setattr(w.store, "similarity_search_with_score", unpublish_during_search)
    result = w.client.post("/api/corpus/query", headers=w.headers(w.alice), json={"query": "irrigation"})
    assert result.status_code == 200 and result.json() == {"results": []}


def test_no_unauthenticated_access_and_no_later_phase_payloads(corpus):
    w = corpus
    assert w.client.get("/api/corpus").status_code == 401
    assert w.client.get("/api/corpus/documents").status_code == 401
    assert w.client.get("/api/corpus/documents/1/content").status_code == 401
    assert w.client.post("/api/corpus/query", json={"query": "test"}).status_code == 401
    reader, admin = w.headers(w.alice), w.headers(w.professor)
    for body in [{"query": "test", "top_k": 1000}, {"query": ""}, {"query": "test", "kb_id": w.bob_kb.id}]:
        assert w.client.post("/api/corpus/query", json=body, headers=reader).status_code == 422
    assert w.client.patch("/api/corpus/documents/1", json={"file_name": "test.txt", "authors_text": "future"}, headers=admin).status_code == 422


@pytest.mark.parametrize("action", ["upload", "retry"])
def test_mysql_concurrent_mutations_allow_one_winner(corpus, monkeypatch, action):
    w = corpus
    if w.engine.dialect.name != "mysql": pytest.skip("Concurrent lifecycle tests require MySQL")
    task = None
    if action == "retry":
        w.store.fail_add = True
        task = upload(w)
        assert task["status"] == "failed"
    monkeypatch.setattr(service, "process_upload", lambda *args: None)
    headers = w.headers(w.professor)
    w.db.rollback()
    barrier = Barrier(2)
    def attempt(_):
        with TestClient(w.app) as client:
            barrier.wait(timeout=10)
            if action == "upload":
                return client.post("/api/corpus/documents/upload", headers=headers,
                                   files={"file": ("same.txt", b"test", "text/plain")}).status_code
            return client.post(f"/api/corpus/tasks/{task['id']}/retry", headers=headers).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [202, 409]
    assert w.db.query(DocumentUpload).filter_by(knowledge_base_id=w.corpus.id).count() == 1


def test_private_ingestion_keeps_default_source_cleanup_and_ownership(corpus):
    w = corpus
    staged = DocumentUpload(knowledge_base_id=w.alice_kb.id, file_name="private-default.txt",
        file_hash="f" * 64, file_size=16, content_type="text/plain", created_at=datetime.utcnow(),
        temp_path=f"kb_{w.alice_kb.id}/temp/private-default.txt")
    w.db.add(staged)
    w.db.flush()
    task = ProcessingTask(knowledge_base_id=w.alice_kb.id, document_upload_id=staged.id, status="pending")
    w.db.add(task)
    w.db.commit()
    w.storage.objects[staged.temp_path] = b"Private evidence."
    document_processor.process_document_background(staged.temp_path, staged.file_name, w.alice_kb.id, task.id, w.db)
    w.db.refresh(task)
    assert task.status == "completed" and task.document.knowledge_base_id == w.alice_kb.id
    assert task.document.academic_metadata is None
    assert staged.temp_path not in w.storage.objects
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}/documents/{task.document_id}", headers=w.headers(w.alice)).status_code == 200
    assert w.client.get(f"/api/corpus/documents/{task.document_id}", headers=w.headers(w.professor)).status_code == 404


def test_public_chunk_cleanup_ids_are_committed_before_vector_writes(corpus, monkeypatch):
    w = corpus
    add = w.store.add_documents
    def inspect_then_add(documents):
        with w.factory() as db:
            ids = [doc.metadata["chunk_id"] for doc in documents]
            assert db.query(DocumentChunk).filter(DocumentChunk.id.in_(ids)).count() == len(ids)
        add(documents)
    monkeypatch.setattr(w.store, "add_documents", inspect_then_add)
    assert upload(w)["status"] == "completed"


def test_repeated_page_text_keeps_distinct_sql_vector_ids_and_citation_pages(corpus, monkeypatch):
    w = corpus
    class RepeatedPages:
        def __init__(self, *args, **kwargs): pass
        def load(self):
            return [Evidence(page_content="The experiment included 120 plots.", metadata={"page": page}) for page in [0, 1]]
    monkeypatch.setattr(document_processor, "TextLoader", RepeatedPages)
    result = upload(w)
    assert result["status"] == "completed"
    chunks = w.db.query(DocumentChunk).filter_by(document_id=result["document_id"]).all()
    assert len(chunks) == 2 and len({row.id for row in chunks}) == 2
    assert {row.chunk_metadata["page"] for row in chunks} == {0, 1}
    assert {row.id for row in chunks} == set(w.store.documents)
