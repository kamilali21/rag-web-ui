"""Opt-in local HTTP acceptance; creates and removes only synthetic fixtures.

Run: PHASE14_LIVE_ACCEPTANCE=1 python -m tests.phase14_live_acceptance
Requires the existing local Docker network, schema and MinIO bucket. No model,
indexing, migrations or real-user sessions are used. Catalog readiness fixtures
are SQL-only; this is not an ingestion test.
"""
import hashlib
import io
import json
import os
import uuid
from datetime import datetime

import httpx
from fastapi import Request
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import AcademicDocumentMetadata, Document, KnowledgeBase, User
from app.models.authentication import AuthSession
from app.models.base import Base
from app.models.knowledge import ProcessingTask
from app.services.auth_sessions import cookie_names, create_session
from app.services.public_corpus import get_minio_client
from tests.baseline_smoke import fixture_pdf


def snapshot(db):
    names = ("users", "knowledge_bases", "documents", "processing_tasks", "document_chunks",
             "document_uploads", "academic_document_metadata", "chats", "messages", "roles",
             "user_roles", "researcher_profiles", "publication_requests", "withdrawal_requests")
    result = {}
    for name in names:
        rows = [dict(row) for row in db.execute(select(Base.metadata.tables[name])).mappings()]
        serialized = sorted(json.dumps(row, default=str, sort_keys=True) for row in rows)
        result[name] = hashlib.sha256(json.dumps(serialized).encode()).hexdigest()
    return result


def run():
    if os.getenv("PHASE14_LIVE_ACCEPTANCE") != "1":
        raise SystemExit("Opt in explicitly with PHASE14_LIVE_ACCEPTANCE=1")
    if settings.AUTH_ORIGIN != "http://127.0.0.1.nip.io":
        raise SystemExit("This fixture is restricted to the local Windows deployment")
    db = SessionLocal()
    baseline = snapshot(db)
    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    db.rollback()
    users, collections, documents, clients, paths = [], [], [], [], []
    storage = get_minio_client()
    name = "phase14_" + uuid.uuid4().hex[:16]
    pdf = fixture_pdf()
    checks = []

    def check(client, method, path, expected=200, **kwargs):
        response = client.request(method, path, **kwargs)
        assert response.status_code == expected, (method, path, response.status_code)
        return response

    try:
        for suffix in ("owner", "other"):
            user = User(username=f"{name}_{suffix}", email=f"{name}_{suffix}@example.invalid",
                        is_active=True, email_verified_at=datetime.utcnow())
            db.add(user); db.flush(); users.append(user.id)
            kb = KnowledgeBase(name=f"{name}_{suffix}", user_id=user.id, scope="private", is_system_managed=False)
            db.add(kb); db.flush(); collections.append(kb.id)
            path = f"kb_{kb.id}/{name}.pdf"
            doc = Document(knowledge_base_id=kb.id, file_name=f"{name}.pdf", file_path=path,
                           file_size=len(pdf), content_type="application/pdf")
            doc.academic_metadata = AcademicDocumentMetadata(title=f"{name} synthetic irrigation",
                authors_text="Synthetic Researcher", document_type="paper", publication_year=2026,
                publication_status="draft", abstract="Synthetic catalog acceptance only")
            db.add(doc); db.flush(); documents.append(doc.id)
            db.add(ProcessingTask(document_id=doc.id, knowledge_base_id=kb.id, status="completed"))
            token, csrf = create_session(db, user, Request({"type": "http", "method": "GET", "headers": []}))
            session_name, csrf_name = cookie_names()
            clients.append(httpx.Client(base_url="http://nginx", timeout=30,
                headers={"Host": "127.0.0.1.nip.io", "Origin": settings.AUTH_ORIGIN, "X-CSRF-Token": csrf},
                cookies={session_name: token, csrf_name: csrf}))
            paths.append(path)
            storage.put_object(settings.MINIO_BUCKET_NAME, path, io.BytesIO(pdf), len(pdf), content_type="application/pdf")
        db.commit()
        owner, other = clients
        with httpx.Client(base_url="http://nginx", timeout=30) as anonymous:
            check(anonymous, "GET", "/api/insights/documents", 401)
        public = check(owner, "GET", "/api/insights/documents?limit=50").json()["items"]
        assert public and all(row["scope"] == "public" for row in public)
        assert not ({row["id"] for row in public} & set(documents))
        checks.append(f"Real public catalog: {len(public)} ready papers on first page")
        private = check(owner, "GET", "/api/insights/documents?scope=private").json()["items"]
        assert [row["id"] for row in private] == [documents[0]]
        both = check(owner, "GET", f"/api/insights/documents?scope=both&search={name}").json()["items"]
        assert [row["id"] for row in both] == [documents[0]]
        for endpoint in (f"/api/insights/documents/{documents[0]}?scope=both",
                         f"/api/knowledge-base/{collections[0]}/documents/{documents[0]}/content"):
            check(other, "GET", endpoint, 404)
        assert check(owner, "GET", f"/api/knowledge-base/{collections[0]}/documents/{documents[0]}/content?inline=true").content == pdf
        checks.append("Private/Both owner boundary and owner-only PDF download")
        ids = [documents[0], public[0]["id"]]
        payload = {"scope": "both", "mode": "compare", "document_ids": ids}
        selected = check(owner, "POST", "/api/insights/selection", json=payload).json()["documents"]
        assert [row["id"] for row in selected] == ids
        check(other, "POST", "/api/insights/selection", 404, json=payload)
        check(owner, "POST", "/api/insights/selection", 422, json={**payload, "document_ids": [True]})
        check(owner, "POST", "/api/insights/selection", json={"scope": "public", "mode": "analyse", "document_ids": [public[0]["id"]]})
        checks.append("Compare/Analyse selection, exact ID order and crafted-ID rejection")
        filtered = check(owner, "GET", f"/api/insights/documents?scope=private&search={name}&author=Synthetic&document_type=paper&year_from=2026&year_to=2026").json()
        assert len(filtered["items"]) == 1
        first = check(owner, "GET", "/api/insights/documents?scope=both&limit=1").json()
        assert first["has_more"]
        second = check(owner, "GET", f'/api/insights/documents?scope=both&limit=1&before_id={first["items"][0]["id"]}').json()
        assert second["items"][0]["id"] < first["items"][0]["id"]
        db.add(ProcessingTask(document_id=documents[0], knowledge_base_id=collections[0], status="failed")); db.commit()
        check(owner, "POST", "/api/insights/selection", 404, json=payload)
        assert check(owner, "GET", "/api/insights/documents?scope=private").json()["items"] == []
        checks.append("Combined filters, stable pagination and fresh readiness revalidation")
        pdf_row = next(row for row in public if row["content_type"] == "application/pdf")
        assert check(owner, "GET", f'/api/corpus/documents/{pdf_row["id"]}/content?inline=true').content.startswith(b"%PDF")
        checks.append("Existing public PDF opens through the unchanged content endpoint")
    finally:
        for client in clients:
            client.close()
        # IDs and object paths are exclusively those created above; never broad cleanup.
        db.rollback()
        for path in paths:
            storage.remove_object(settings.MINIO_BUCKET_NAME, path)
        db.query(ProcessingTask).filter(ProcessingTask.document_id.in_(documents)).delete(synchronize_session=False)
        db.query(AcademicDocumentMetadata).filter(AcademicDocumentMetadata.document_id.in_(documents)).delete(synchronize_session=False)
        db.query(Document).filter(Document.id.in_(documents)).delete(synchronize_session=False)
        db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(collections)).delete(synchronize_session=False)
        db.query(AuthSession).filter(AuthSession.user_id.in_(users)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(users)).delete(synchronize_session=False)
        db.commit()
        assert baseline == snapshot(db), "Existing data changed; investigate concurrent activity"
        assert revision == db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        db.close()
    print(json.dumps({"passed": checks, "cleanup": "synthetic SQL, sessions and objects removed; original rows unchanged", "schema": revision}), flush=True)


if __name__ == "__main__":
    run()
