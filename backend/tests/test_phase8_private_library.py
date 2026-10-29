"""Private catalog and lifecycle acceptance using the real ORM and ingestion worker."""
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from app.models.knowledge import Document, DocumentChunk, DocumentUpload, ProcessingTask
from app.services import private_library, document_processor
from app.api.api_v1 import knowledge_base
from tests.test_phase2_authorization import world
from tests.test_phase4_public_corpus import Storage, Store


@pytest.fixture
def library(world, monkeypatch):
    w = world
    if w.engine.dialect.name == "sqlite":
        with w.engine.connect() as connection:
            connection.connection.driver_connection.create_function("now", 0, lambda: datetime.utcnow().isoformat(" "))
    w.storage, w.store = Storage(), Store()
    for module in (private_library, knowledge_base, document_processor):
        monkeypatch.setattr(module, "get_minio_client", lambda: w.storage)
    monkeypatch.setattr(document_processor, "SessionLocal", w.factory)
    monkeypatch.setattr(private_library.EmbeddingsFactory, "create", lambda: object())
    monkeypatch.setattr(private_library.VectorStoreFactory, "create", lambda **kwargs: w.store)
    return w


def upload(w, name="private-paper.txt"):
    path = f"/api/knowledge-base/{w.alice_kb.id}/documents"
    result = w.client.post(path + "/upload", files={"files": (name, b"Synthetic Phase 8 irrigation evidence: interval seven days.", "text/plain")}, headers=w.headers(w.alice))
    assert result.status_code == 200, result.text
    submitted = w.client.post(path + "/process", json=result.json(), headers=w.headers(w.alice))
    assert submitted.status_code == 200, submitted.text
    w.db.rollback()
    return w.db.get(ProcessingTask, submitted.json()["tasks"][0]["task_id"])


def test_catalog_owned_bounded_literal_filters_and_orphan_states(library):
    w = library
    task = upload(w)
    assert task.status == "completed"
    orphan = w.uploads[0]
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_upload_id=orphan.id, status="failed", error_message="SECRET PROVIDER ERROR"))
    w.db.commit()
    def get(**params):
        result = w.client.get("/api/knowledge-base/catalog", params=params, headers=w.headers(w.alice))
        assert result.status_code == 200, result.text
        return result.json()
    all_rows = get()
    assert all(row["knowledge_base_id"] == w.alice_kb.id for row in all_rows["items"])
    assert all_rows["total"] == 3
    assert "SECRET" not in str(all_rows) and "file_path" not in str(all_rows)
    assert get(status="failed")["items"][0]["upload_id"] == orphan.id
    assert get(status="completed", category="Papers")["items"][0]["id"] == task.document_id
    assert get(search="%_")["total"] == 0
    first, second = get(limit=1), get(limit=1, skip=1)
    assert first["items"][0]["id"] != second["items"][0]["id"]
    for params in ({"limit": 101}, {"skip": -1}, {"status": "bad"}, {"category": "bad"}):
        assert w.client.get("/api/knowledge-base/catalog", params=params, headers=w.headers(w.alice)).status_code == 422
    summaries = w.client.get("/api/knowledge-base?summary=true", headers=w.headers(w.alice)).json()
    assert summaries[0]["documents"] == []


@pytest.mark.parametrize("actor", ["bob", "professor", "superuser"])
def test_foreign_catalog_and_deletion_never_reach_storage(library, actor):
    w = library
    headers = w.headers(getattr(w, actor))
    for method, path in [
        ("GET", f"/api/knowledge-base/catalog?kb_id={w.alice_kb.id}"),
        ("DELETE", f"/api/knowledge-base/{w.alice_kb.id}/documents/{w.alice_doc.id}"),
        ("GET", f"/api/knowledge-base/{w.alice_kb.id}/documents/{w.alice_doc.id}/content"),
        ("DELETE", f"/api/knowledge-base/{w.alice_kb.id}/uploads/{w.uploads[0].id}"),
    ]:
        assert w.client.request(method, path, headers=headers).status_code == 404
    assert not w.storage.objects and not w.store.documents


@pytest.mark.parametrize("failure", ["storage", "store"])
def test_delete_failure_retains_references_then_retry_removes_only_target(library, failure):
    w = library
    first, second = upload(w), upload(w, "keep.txt")
    doc_id, other_id = first.document_id, second.document_id
    chunks = [row.id for row in w.db.query(DocumentChunk).filter_by(document_id=doc_id)]
    setattr(getattr(w, failure), "fail_delete", True)
    path = f"/api/knowledge-base/{w.alice_kb.id}/documents/{doc_id}"
    result = w.client.delete(path, headers=w.headers(w.alice))
    assert result.status_code == 503 and "secret" not in result.text.lower()
    w.db.rollback()
    assert w.db.get(Document, doc_id) and w.db.get(Document, other_id)
    assert w.db.query(DocumentChunk).filter_by(document_id=doc_id).count() == len(chunks)
    failed = w.client.get("/api/knowledge-base/catalog?status=failed", headers=w.headers(w.alice)).json()
    assert doc_id in {row["id"] for row in failed["items"]}
    setattr(getattr(w, failure), "fail_delete", False)
    assert w.client.delete(path, headers=w.headers(w.alice)).status_code == 200
    w.db.rollback()
    assert w.db.get(Document, doc_id) is None and w.db.get(Document, other_id)
    assert not set(chunks) & w.store.documents.keys()
    assert f"kb_{w.alice_kb.id}/keep.txt" in w.storage.objects


def test_partial_private_ingestion_is_linked_visible_and_deletable(library):
    w = library
    w.store.fail_add = True
    task = upload(w)
    assert task.status == "failed" and task.document_id is not None
    assert w.db.query(DocumentChunk).filter_by(document_id=task.document_id).count() > 0
    result = w.client.get("/api/knowledge-base/catalog?status=failed", headers=w.headers(w.alice))
    assert result.json()["items"][0]["id"] == task.document_id
    result = w.client.delete(f"/api/knowledge-base/{w.alice_kb.id}/documents/{task.document_id}", headers=w.headers(w.alice))
    assert result.status_code == 200, result.text
    assert not w.store.documents and not w.storage.objects


def test_pending_jobs_block_deletion_and_duplicate_submissions(library):
    w = library
    upload_id = w.uploads[0].id
    task = ProcessingTask(knowledge_base_id=w.alice_kb.id, document_upload_id=upload_id, status="pending")
    w.db.add(task); w.db.commit()
    base = f"/api/knowledge-base/{w.alice_kb.id}"
    assert w.client.delete(base + f"/uploads/{upload_id}", headers=w.headers(w.alice)).status_code == 409
    assert w.client.delete(base, headers=w.headers(w.alice)).status_code == 409
    assert w.client.post(base + "/documents/process", json=[{"upload_id": upload_id}], headers=w.headers(w.alice)).status_code == 409
    assert w.client.get("/api/knowledge-base/catalog?search=nomatch", headers=w.headers(w.alice)).json()["has_active_tasks"]


def test_failed_pre_document_upload_removal_and_mismatched_ids(library):
    w = library
    staged = w.uploads[0]
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_upload_id=staged.id, status="failed")); w.db.commit()
    root = f"/api/knowledge-base/{w.alice_kb.id}"
    assert w.client.delete(root + f"/documents/{w.bob_doc.id}", headers=w.headers(w.alice)).status_code == 404
    assert w.client.delete(root + f"/uploads/{w.uploads[1].id}", headers=w.headers(w.alice)).status_code == 404
    assert w.client.delete(root + f"/uploads/{staged.id}", headers=w.headers(w.alice)).status_code == 200


def test_chroma_deletion_covers_legacy_generated_vector_ids():
    from app.services.vector_store.chroma import ChromaVectorStore
    store = object.__new__(ChromaVectorStore)
    store._store = MagicMock()
    store.delete(["relational-chunk"])
    store._store.delete.assert_called_once_with(["relational-chunk"])
    store._store._collection.delete.assert_called_once_with(where={"chunk_id": {"$in": ["relational-chunk"]}})


def test_private_content_download_and_inline_are_owner_scoped(library):
    w = library
    task = upload(w)
    result = w.client.get(f"/api/knowledge-base/{w.alice_kb.id}/documents/{task.document_id}/content?inline=true", headers=w.headers(w.alice))
    assert result.status_code == 200 and b"seven days" in result.content
    assert result.headers["content-disposition"].startswith("inline;")
    assert result.headers["cache-control"] == "no-store" and result.headers["content-security-policy"] == "sandbox"


def test_whole_collection_cleanup_failure_is_retryable(library):
    w = library
    task = upload(w)
    w.storage.list_objects = lambda *args, **kwargs: [type("Object", (), {"object_name": p}) for p in list(w.storage.objects)]
    w.store.delete_collection = lambda: w.store.documents.clear()
    w.store.fail_delete = True
    w.storage.fail_delete = True
    path = f"/api/knowledge-base/{w.alice_kb.id}"
    assert w.client.delete(path, headers=w.headers(w.alice)).status_code == 503
    w.db.rollback()
    assert w.db.get(Document, task.document_id)
    w.storage.fail_delete = False
    assert w.client.delete(path, headers=w.headers(w.alice)).status_code == 200


def test_private_processing_errors_are_redacted_on_every_read(library):
    w = library
    w.store.fail_add = True
    task = upload(w)
    assert task.status == "failed" and "secret" not in task.error_message
    # Also protect historical records written before exception sanitization.
    task.error_message = "SECRET provider token and internal path"
    w.db.commit()
    base = f"/api/knowledge-base/{w.alice_kb.id}"
    for path in ["/api/knowledge-base", base, base + f"/documents/{task.document_id}",
                 base + f"/documents/tasks?task_ids={task.id}"]:
        result = w.client.get(path, headers=w.headers(w.alice))
        assert result.status_code == 200, result.text
        assert "SECRET" not in result.text and "Document processing failed" in result.text


def test_private_upload_reads_are_bounded_before_writing_storage(library, monkeypatch):
    w = library
    monkeypatch.setattr(knowledge_base, "MAX_UPLOAD_BYTES", 32)
    response = w.client.post(f"/api/knowledge-base/{w.alice_kb.id}/documents/upload",
        files={"files": ("oversized.txt", b"x" * 33, "text/plain")}, headers=w.headers(w.alice))
    assert response.status_code == 413
    assert not w.storage.objects
    assert not w.db.query(DocumentUpload).filter_by(file_name="oversized.txt").first()


def test_private_docx_expansion_is_rejected_before_parser_or_embeddings(library, monkeypatch):
    w = library
    compressed = BytesIO()
    with ZipFile(compressed, "w", compression=ZIP_DEFLATED) as archive:
        with archive.open("word/document.xml", "w") as member:
            for _ in range(101):
                member.write(b"x" * (1024 * 1024))
    assert len(compressed.getvalue()) < 1024 * 1024
    parser, embeddings = MagicMock(), MagicMock()
    monkeypatch.setattr(document_processor, "Docx2txtLoader", parser)
    monkeypatch.setattr(document_processor.EmbeddingsFactory, "create", embeddings)
    base = f"/api/knowledge-base/{w.alice_kb.id}/documents"
    staged = w.client.post(base + "/upload", files={"files": ("oversized.docx", compressed.getvalue(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}, headers=w.headers(w.alice))
    assert staged.status_code == 400
    assert not w.db.query(DocumentUpload).filter_by(file_name="oversized.docx").first()
    assert not w.storage.objects
    parser.assert_not_called()
    embeddings.assert_not_called()
