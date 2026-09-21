"""Added by ChatGPT: Phase 5 HTTP/domain validation, isolation and MySQL concurrency gates."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.models import AcademicDocumentMetadata, AdminAllowlist, Document
from app.models.knowledge import ProcessingTask
from app.models.research import Department
from app.schemas.academic import MetadataPatch, DepartmentCreate
from app.services import academic, public_corpus
from tests.test_phase2_authorization import world
from tests.test_phase3_authentication import otp, login, csrf
from tests.test_phase4_public_corpus import corpus, upload, publish


def department(w, name="Agronomy", code="AGR"):
    response = w.client.post("/api/departments", headers=w.headers(w.professor), json={"name": name, "code": code})
    assert response.status_code == 201, response.text
    w.db.rollback()
    return response.json()["id"]


def patch(w, document_id, values, actor=None):
    response = w.client.patch(f"/api/corpus/documents/{document_id}/metadata",
                              headers=w.headers(actor or w.professor), json=values)
    w.db.rollback()
    return response


def test_metadata_roundtrip_preserves_sources_chunks_and_publication(corpus):
    w = corpus
    dep = department(w)
    doc_id = upload(w)["document_id"]
    doc = w.db.get(Document, doc_id)
    identity = (doc.file_name, doc.file_path, doc.file_hash, [chunk.id for chunk in doc.chunks])
    objects, vectors = dict(w.storage.objects), dict(w.store.documents)
    values = dict(title="  Irrigation efficiency  ", authors_text="A. Researcher; B. Researcher", abstract="Synthetic research only.",
                  department_id=dep, document_type="paper", publication_year=2024, publication_date="2024-03-10",
                  supervisor="Dr. Example", keywords=[" Water ", "water", "Irrigation"], doi="10.1234/synthetic", language="en-PK")
    response = patch(w, doc_id, values)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["title"] == "Irrigation efficiency" and result["keywords"] == ["Water", "Irrigation"]
    assert result["document_id"] == doc_id and result["department_id"] == dep and result["publication_status"] == "draft"
    assert "file_path" not in result and "user_id" not in result
    for key in ["authors_text", "abstract", "document_type", "publication_year", "publication_date", "supervisor", "doi", "language"]:
        assert result[key] == values[key]
    reader = w.headers(w.alice)
    path = f"/api/corpus/documents/{doc_id}/metadata"
    assert w.client.get(path, headers=reader).status_code == 404
    assert w.client.get(path+"?include_unpublished=true", headers=reader).status_code == 403
    assert w.client.get(path+"?include_unpublished=true", headers=w.headers(w.professor)).status_code == 200
    publish(w, doc_id)
    assert w.client.get(path, headers=reader).json()["title"] == result["title"]
    assert patch(w, doc_id, {"title": "Corrected title"}).json()["publication_status"] == "published"
    doc = w.db.get(Document, doc_id)
    assert (doc.file_name, doc.file_path, doc.file_hash, [chunk.id for chunk in doc.chunks]) == identity
    assert w.storage.objects == objects and w.store.documents == vectors
    assert w.db.query(AcademicDocumentMetadata).filter_by(document_id=doc_id).count() == 1


def test_partial_updates_clearing_and_cross_field_validation_are_atomic(corpus):
    w = corpus
    doc_id = upload(w)["document_id"]
    assert patch(w, doc_id, {"publication_year": 2024, "publication_date": "2024-01-01", "authors_text": "Author"}).status_code == 200
    assert patch(w, doc_id, {"title": "Must not stick", "publication_year": 2025}).status_code == 422
    metadata = w.db.get(Document, doc_id).academic_metadata
    assert metadata.title == "research.txt" and metadata.publication_year == 2024
    assert patch(w, doc_id, {"publication_date": "2025-01-01"}).status_code == 422
    response = patch(w, doc_id, {"publication_date": None, "publication_year": 2025, "authors_text": "  ", "keywords": []})
    assert response.status_code == 200
    assert response.json()["authors_text"] is None and response.json()["publication_date"] is None
    assert response.json()["publication_year"] == 2025 and response.json()["keywords"] == []
    assert patch(w, doc_id, {"department_id": 999999, "title": "Also must not stick"}).status_code == 422
    assert w.db.get(Document, doc_id).academic_metadata.title == "research.txt"


@pytest.mark.parametrize("values", [
    {}, {"title": None}, {"title": "  "}, {"title": "x" * 501}, {"title": "null\x00byte"},
    {"authors_text": "x" * 8001}, {"abstract": "x" * 16001}, {"document_type": "invented"},
    {"publication_year": True}, {"publication_year": "2024"}, {"publication_year": 999}, {"publication_year": 10000},
    {"publication_date": "2024-02-30"}, {"publication_date": "0001-01-01"}, {"publication_date": 1700000000}, {"publication_date": "2024-01-01T00:00:00"},
    {"department_id": True}, {"department_id": 0}, {"keywords": "water"}, {"keywords": [" "]},
    {"keywords": ["x"] * 21}, {"keywords": [1]}, {"keywords": ["x" * 101]}, {"keywords": ["bad\x00word"]},
    {"doi": "https://evil.invalid"}, {"language": "en<script>"}, {"publication_status": "published"},
    {"user_id": 1}, {"document_id": 1}, {"file_path": "private/secret"},
])
def test_bounded_metadata_validation(values):
    with pytest.raises(ValidationError):
        MetadataPatch.model_validate(values)


def test_http_rejects_forbidden_fields_and_preserves_metadata(corpus):
    w = corpus
    doc_id = upload(w)["document_id"]
    assert patch(w, doc_id, {"title": "Rejected", "publication_status": "published"}).status_code == 422
    assert patch(w, doc_id, {"title": None}).status_code == 422
    row = w.db.get(Document, doc_id).academic_metadata
    assert row.title == "research.txt" and row.publication_status == "draft"


def test_department_lifecycle_retains_historical_references(corpus):
    w = corpus
    dep = department(w, "  Plant   Sciences ", " plants ")
    doc_id = upload(w)["document_id"]
    assert patch(w, doc_id, {"department_id": dep}).status_code == 200
    publish(w, doc_id)
    reader, admin = w.headers(w.alice), w.headers(w.professor)
    row = w.client.get(f"/api/departments/{dep}", headers=reader).json()
    assert row["name"] == "Plant Sciences" and row["code"] == "PLANTS"
    assert w.client.patch(f"/api/departments/{dep}", headers=admin, json={"is_active": False}).status_code == 200
    assert w.client.get("/api/departments", headers=reader).json() == []
    assert w.client.get("/api/departments?include_inactive=true", headers=reader).status_code == 403
    assert w.client.get("/api/departments?include_inactive=true", headers=admin).json()[0]["id"] == dep
    assert w.client.get(f"/api/departments/{dep}", headers=reader).json()["is_active"] is False
    assert patch(w, doc_id, {"department_id": dep}).status_code == 422
    assert patch(w, doc_id, {"title": "Unrelated correction"}).status_code == 200
    assert w.client.get(f"/api/corpus/documents/{doc_id}/metadata", headers=reader).json()["department_id"] == dep
    assert patch(w, doc_id, {"department_id": None}).status_code == 200
    assert w.client.patch(f"/api/departments/{dep}", headers=admin, json={"is_active": True}).status_code == 200
    assert patch(w, doc_id, {"department_id": dep}).status_code == 200
    assert w.client.delete(f"/api/departments/{dep}", headers=admin).status_code == 405


def test_department_uniqueness_validation_and_bounded_listing(corpus):
    w = corpus
    first, second = department(w), department(w, "Food Science", "FOOD")
    admin, reader = w.headers(w.professor), w.headers(w.alice)
    for values in [{"name": "agronomy", "code": "NEW"}, {"name": "New Department", "code": "agr"}]:
        assert w.client.post("/api/departments", headers=admin, json=values).status_code == 409
    assert w.client.patch(f"/api/departments/{second}", headers=admin, json={"code": "AGR"}).status_code == 409
    for values in [{}, {"name": None}, {"name": "  "}, {"is_active": "false"}, {"code": "x/y"}, {"added_by": 1}]:
        assert w.client.patch(f"/api/departments/{first}", headers=admin, json=values).status_code == 422
    assert w.client.get("/api/departments?limit=1", headers=reader).json()[0]["id"] == first
    assert w.client.get(f"/api/departments?after_id={first}&limit=1", headers=reader).json()[0]["id"] == second
    assert w.client.get("/api/departments?limit=1000", headers=reader).status_code == 422
    assert w.client.get("/api/departments/999999", headers=reader).status_code == 404
    assert w.client.patch("/api/departments/999999", headers=admin, json={"name": "Missing"}).status_code == 404


def test_services_enforce_admin_and_corpus_boundaries(corpus):
    w = corpus
    doc_id = upload(w)["document_id"]
    for actor in [w.alice, w.superuser]:
        assert patch(w, doc_id, {"title": "Denied"}, actor).status_code == 403
        assert w.client.post("/api/departments", headers=w.headers(actor), json={"name": "Denied", "code": "NO"}).status_code == 403
        with pytest.raises(HTTPException) as error:
            academic.update_metadata(w.db, actor, doc_id, MetadataPatch(title="Denied"))
        assert error.value.status_code == 403
        with pytest.raises(HTTPException) as error:
            academic.save_department(w.db, actor, DepartmentCreate(name="Denied", code="NO"))
        assert error.value.status_code == 403
    for actor in [w.alice, w.professor]:
        assert w.client.get(f"/api/corpus/documents/{w.bob_doc.id}/metadata", headers=w.headers(actor)).status_code == 404
    assert patch(w, w.bob_doc.id, {"title": "Private intrusion"}).status_code == 404
    allowlist = w.db.query(AdminAllowlist).filter_by(email=w.professor.email).one()
    allowlist.is_active = False
    w.db.commit()
    assert patch(w, doc_id, {"title": "Revoked"}).status_code == 403
    assert w.client.post("/api/departments", headers=w.headers(w.professor), json={"name": "Denied", "code": "NO"}).status_code == 403
    assert w.client.get("/api/departments").status_code == 401
    assert w.client.get(f"/api/corpus/documents/{doc_id}/metadata").status_code == 401


@pytest.mark.parametrize("status", ["pending", "processing", "failed", "archived"])
def test_metadata_rejects_incomplete_or_deleting_documents(corpus, status):
    w = corpus
    task = upload(w)
    if status == "archived":
        w.db.get(Document, task["document_id"]).academic_metadata.publication_status = status
    else:
        w.db.get(ProcessingTask, task["id"]).status = status
    w.db.commit()
    assert patch(w, task["document_id"], {"title": "Denied"}).status_code == 409


def test_phase5_cookie_mutations_keep_csrf_protection(otp):
    w = otp
    login(w, w.professor.email)
    assert w.client.post("/api/departments", json={"name": "Agronomy", "code": "AGR"}).status_code == 403
    assert w.client.post("/api/departments", headers=csrf(w), json={"name": "Agronomy", "code": "AGR"}).status_code == 201
    path = f"/api/corpus/documents/{w.bob_doc.id}/metadata"
    assert w.client.patch(path, json={"title": "Denied"}).status_code == 403
    public_corpus.provision_corpus(w.db)
    assert w.client.patch(path, headers=csrf(w), json={"title": "Denied"}).status_code == 404


@pytest.mark.parametrize("action", ["department", "metadata"])
def test_mysql_concurrent_creates_and_disjoint_metadata_updates(corpus, action):
    w = corpus
    if w.engine.dialect.name != "mysql":
        pytest.skip("Concurrent row locking requires MySQL")
    doc_id = upload(w)["document_id"] if action == "metadata" else None
    headers = w.headers(w.professor)
    w.db.rollback()
    barrier = Barrier(2)
    def attempt(index):
        with TestClient(w.app) as client:
            barrier.wait(timeout=10)
            if action == "department":
                return client.post("/api/departments", headers=headers, json={"name": "Agronomy", "code": "AGR"}).status_code
            return client.patch(f"/api/corpus/documents/{doc_id}/metadata", headers=headers,
                                json={"title": "Updated title"} if index == 0 else {"authors_text": "Updated author"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    if action == "department":
        assert sorted(results) == [201, 409]
        assert w.db.query(Department).count() == 1
    else:
        assert results == [200, 200]
        row = w.db.get(Document, doc_id).academic_metadata
        assert row.title == "Updated title" and row.authors_text == "Updated author"
