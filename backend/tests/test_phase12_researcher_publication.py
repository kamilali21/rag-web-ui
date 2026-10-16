"""Phase 12 profile privacy and request-scoped publication lifecycle tests."""
from app.models import Document, DocumentChunk
from app.models.knowledge import ProcessingTask
from app.models.research import Department
from app.models.researcher import PublicationRequest
from app.api.api_v1 import researcher as researcher_api
from app.services import private_library, researcher_publications as workflow
from tests.test_phase2_authorization import world
from tests.test_phase4_public_corpus import corpus


def prepare_private_document(w):
    document = w.alice_doc
    content = b"Synthetic research on irrigation efficiency and water use."
    document.file_name = "irrigation-study.txt"
    document.file_path = f"kb_{w.alice_kb.id}/{document.file_name}"
    document.file_size = len(content)
    document.content_type = "text/plain"
    document.file_hash = "c" * 64
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_id=document.id, status="completed"))
    w.db.add(DocumentChunk(id="a" * 64, kb_id=w.alice_kb.id, document_id=document.id,
        file_name=document.file_name, chunk_metadata={"page_content": content.decode(), "page": 0}, hash="b" * 64))
    w.db.commit()
    w.storage.objects[document.file_path] = content
    return document, content


def profile_payload(department_id):
    return {"full_name": "Ayesha Researcher", "department_id": department_id,
            "degree": "MSc Agronomy", "research_area": "Water-efficient agriculture",
            "ag_number": "AG-100", "class_name": "MSc-2", "section": "A"}


def create_profile(w, department_id):
    response = w.client.put("/api/researcher/profile", headers=w.headers(w.alice), json=profile_payload(department_id))
    assert response.status_code == 200, response.text
    return response.json()


def request_payload(document_id, department_id, *, consent=True):
    return {"source_document_id": document_id, "public_card_consent": consent,
        "metadata": {"title": "Irrigation efficiency study", "authors_text": "Ayesha Researcher",
            "department_id": department_id, "document_type": "paper", "abstract": "Synthetic abstract",
            "publication_year": 2024, "keywords": ["irrigation", "water"]}}


def setup_request(w, monkeypatch, *, consent=True):
    department = Department(name="Agronomy", code="AGR", is_active=True)
    w.db.add(department); w.db.commit(); w.db.refresh(department)
    document, content = prepare_private_document(w)
    monkeypatch.setattr(workflow, "get_minio_client", lambda: w.storage)
    monkeypatch.setattr(private_library, "get_minio_client", lambda: w.storage)
    monkeypatch.setattr(researcher_api, "get_minio_client", lambda: w.storage)
    create_profile(w, department.id)
    response = w.client.post("/api/researcher/requests", headers=w.headers(w.alice),
        json=request_payload(document.id, department.id, consent=consent))
    assert response.status_code == 201, response.text
    return department, document, content, response.json()


def test_profile_owner_validation_and_bounded_private_photo(corpus, monkeypatch):
    w = corpus
    department = Department(name="Horticulture", code="HORT", is_active=True)
    inactive = Department(name="Inactive", code="INACTIVE", is_active=False)
    w.db.add_all([department, inactive]); w.db.commit()
    response = w.client.put("/api/researcher/profile", headers=w.headers(w.alice), json=profile_payload(department.id))
    assert response.status_code == 200 and response.json()["ag_number"] == "AG-100"
    assert w.client.put("/api/researcher/profile", headers=w.headers(w.alice), json=profile_payload(inactive.id)).status_code == 422
    assert w.client.get("/api/researcher/profile", headers=w.headers(w.bob)).json() is None
    assert w.client.put("/api/researcher/profile", headers=w.headers(w.bob), json=profile_payload(department.id)).status_code == 200
    monkeypatch.setattr(workflow, "get_minio_client", lambda: w.storage)
    image = b"\x89PNG\r\n\x1a\n" + b"synthetic-image-data"
    uploaded = w.client.put("/api/researcher/profile/photo", headers=w.headers(w.alice), files={"file": ("profile.png", image, "image/png")})
    assert uploaded.status_code == 200
    assert w.client.get("/api/researcher/profile/photo", headers=w.headers(w.alice)).content == image
    assert w.client.get("/api/researcher/profile/photo", headers=w.headers(w.bob)).status_code == 404
    invalid = w.client.put("/api/researcher/profile/photo", headers=w.headers(w.alice), files={"file": ("profile.svg", b"<svg/>", "image/svg+xml")})
    assert invalid.status_code == 415
    assert w.client.delete("/api/researcher/profile/photo", headers=w.headers(w.alice)).status_code == 204
    assert w.client.get("/api/researcher/profile/photo", headers=w.headers(w.alice)).status_code == 404


def test_duplicate_foreign_document_and_review_are_request_scoped(corpus, monkeypatch):
    w = corpus
    department, document, content, request = setup_request(w, monkeypatch)
    headers = w.headers(w.alice)
    duplicate = w.client.post("/api/researcher/requests", headers=headers,
        json=request_payload(document.id, department.id))
    assert duplicate.status_code == 409
    foreign = w.client.post("/api/researcher/requests", headers=w.headers(w.bob),
        json=request_payload(document.id, department.id))
    assert foreign.status_code == 404
    request_id = request["id"]
    assert w.client.get("/api/researcher/admin/count", headers=w.headers(w.professor)).json() == {"count": 1}
    assert w.client.get(f"/api/researcher/admin/{request_id}", headers=w.headers(w.alice)).status_code == 403
    # Even an admin cannot use the generic owner-only private document API.
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}/documents/{document.id}/content",
                        headers=w.headers(w.professor)).status_code == 404
    detail = w.client.get(f"/api/researcher/admin/{request_id}", headers=w.headers(w.professor))
    assert detail.status_code == 200 and detail.json()["profile"]["ag_number"] == "AG-100"
    assert detail.json()["document"]["id"] == document.id
    corrected = {**detail.json()["metadata"], "title": "Corrected irrigation study"}
    update = w.client.patch(f"/api/researcher/admin/{request_id}/metadata", headers=w.headers(w.professor), json=corrected)
    assert update.status_code == 200 and update.json()["metadata"]["title"] == "Corrected irrigation study"
    exact = w.client.get(f"/api/researcher/admin/{request_id}/source?inline=true", headers=w.headers(w.professor))
    assert exact.status_code == 200 and exact.content == content
    deny = w.client.post(f"/api/researcher/admin/{request_id}/deny", headers=w.headers(w.professor), json={"reason": "Please correct the study title."})
    assert deny.status_code == 204
    own = w.client.get("/api/researcher/requests", headers=w.headers(w.alice)).json()["publications"][0]
    assert own["status"] == "denied" and own["denial_reason"] == "Please correct the study title."
    assert own["metadata"]["title"] == "Corrected irrigation study"
    assert w.client.get("/api/researcher/admin/count", headers=w.headers(w.professor)).json() == {"count": 0}
    assert w.client.get(f"/api/researcher/admin/{request_id + 1000}/source", headers=w.headers(w.professor)).status_code == 404


def test_approved_copy_publishes_after_index_and_withdrawal_archives(corpus, monkeypatch):
    w = corpus
    department, private_document, private_content, request = setup_request(w, monkeypatch, consent=True)
    original_path, original_chunks = private_document.file_path, [chunk.id for chunk in private_document.chunks]
    original_vectors = dict(w.store.documents)
    request_id = request["id"]
    image = b"\x89PNG\r\n\x1a\n" + b"synthetic-profile-image"
    photo_upload = w.client.put("/api/researcher/profile/photo", headers=w.headers(w.alice),
        files={"file": ("profile.png", image, "image/png")})
    assert photo_upload.status_code == 200
    response = w.client.post(f"/api/researcher/admin/{request_id}/approve", headers=w.headers(w.professor))
    assert response.status_code == 202, response.text
    current = w.db.query(PublicationRequest).filter_by(id=request_id).one()
    assert current.status == "published" and current.public_document_id != private_document.id
    public_document = w.db.get(Document, current.public_document_id)
    assert public_document.academic_metadata.publication_status == "published"
    assert public_document.chunks and w.storage.objects[original_path] == private_content
    assert [chunk.id for chunk in private_document.chunks] == original_chunks
    assert w.store.documents.keys() >= original_vectors.keys()
    assert w.client.get(f"/api/researcher/admin/{request_id}/source", headers=w.headers(w.professor)).status_code == 200
    card = w.client.get(f"/api/researcher/publications/{public_document.id}/researcher-card", headers=w.headers(w.alice))
    assert card.status_code == 200
    assert set(card.json()) == {"full_name", "department_name", "degree", "research_area", "photo_url"}
    assert card.json()["full_name"] == "Ayesha Researcher"
    assert "ag_number" not in card.json() and "class_name" not in card.json() and "section" not in card.json()
    assert card.json()["photo_url"] == f"/api/researcher/publications/{public_document.id}/researcher-photo"
    assert w.client.get(card.json()["photo_url"], headers=w.headers(w.alice)).content == image
    assert w.client.get(f"/api/researcher/admin/{request_id}/profile-photo", headers=w.headers(w.professor)).content == image
    public_listing = w.client.get("/api/corpus/documents?limit=100", headers=w.headers(w.alice)).json()
    assert any(row["id"] == public_document.id for row in public_listing)

    withdrawal = w.client.post(f"/api/researcher/requests/{request_id}/withdrawals", headers=w.headers(w.alice), json={"reason": "Updated version submitted."})
    assert withdrawal.status_code == 201
    withdrawal_id = withdrawal.json()["id"]
    assert w.client.get("/api/researcher/admin/count", headers=w.headers(w.professor)).json() == {"count": 1}
    assert w.client.post(f"/api/researcher/admin/withdrawals/{withdrawal_id}/deny", headers=w.headers(w.professor),
                         json={"reason": "Please keep the current version available."}).status_code == 204
    assert w.client.get("/api/researcher/admin/count", headers=w.headers(w.professor)).json() == {"count": 0}
    assert w.client.get(f"/api/corpus/documents/{public_document.id}", headers=w.headers(w.alice)).status_code == 200
    assert w.client.get("/api/researcher/requests", headers=w.headers(w.alice)).json()["withdrawals"][0]["decision_reason"] == "Please keep the current version available."
    approved = w.client.post(f"/api/researcher/requests/{request_id}/withdrawals", headers=w.headers(w.alice), json={"reason": "Please archive this copy."})
    assert approved.status_code == 201
    assert w.client.post(f"/api/researcher/admin/withdrawals/{approved.json()['id']}/approve", headers=w.headers(w.professor)).status_code == 204
    assert w.client.get(f"/api/corpus/documents/{public_document.id}", headers=w.headers(w.alice)).status_code == 404
    assert w.client.get(f"/api/corpus/documents/{public_document.id}?include_unpublished=true", headers=w.headers(w.professor)).json()["publication_status"] == "archived"
    assert w.client.get("/api/researcher/requests", headers=w.headers(w.alice)).json()["withdrawals"][0]["status"] == "approved"
    assert w.client.get(f"/api/researcher/publications/{public_document.id}/researcher-card", headers=w.headers(w.alice)).status_code == 404


def test_failed_public_ingestion_is_private_and_retryable(corpus, monkeypatch):
    w = corpus
    department, _, _, request = setup_request(w, monkeypatch, consent=False)
    w.store.fail_add = True
    response = w.client.post(f"/api/researcher/admin/{request['id']}/approve", headers=w.headers(w.professor))
    assert response.status_code == 202
    row = w.db.query(PublicationRequest).filter_by(id=request["id"]).one()
    assert row.status == "failed" and row.public_document_id is None
    assert w.client.get("/api/researcher/admin/count", headers=w.headers(w.professor)).json() == {"count": 0}

    w.store.fail_add = False
    retry = w.client.post(f"/api/researcher/admin/{request['id']}/approve", headers=w.headers(w.professor))
    assert retry.status_code == 202
    w.db.expire_all()
    row = w.db.query(PublicationRequest).filter_by(id=request["id"]).one()
    assert row.status == "published" and row.public_document_id is not None
    assert w.client.get(f"/api/corpus/documents/{row.public_document_id}", headers=w.headers(w.alice)).status_code == 200


def test_public_card_never_appears_without_per_request_consent(corpus, monkeypatch):
    w = corpus
    _, _, _, request = setup_request(w, monkeypatch, consent=False)
    response = w.client.post(f"/api/researcher/admin/{request['id']}/approve", headers=w.headers(w.professor))
    assert response.status_code == 202
    row = w.db.query(PublicationRequest).filter_by(id=request["id"]).one()
    assert row.status == "published"
    assert w.client.get(f"/api/researcher/publications/{row.public_document_id}/researcher-card",
                        headers=w.headers(w.alice)).json() is None


def test_deleting_private_source_cancels_pending_request_and_preserves_audit(corpus, monkeypatch):
    w = corpus
    _, document, _, request = setup_request(w, monkeypatch)
    response = w.client.delete(f"/api/knowledge-base/{w.alice_kb.id}/documents/{document.id}", headers=w.headers(w.alice))
    assert response.status_code == 200, response.text
    row = w.db.query(PublicationRequest).filter_by(id=request["id"]).one()
    assert row.status == "cancelled" and row.source_document_id is None
    assert w.client.get("/api/researcher/requests", headers=w.headers(w.alice)).json()["publications"][0]["status"] == "cancelled"
