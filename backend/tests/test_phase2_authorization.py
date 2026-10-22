"""Added by ChatGPT: real ORM/HTTP authorization checks using disposable in-memory data.

No application startup, credentials, MinIO or Chroma connection is used. Provider
spies verify that forbidden requests never reach retrieval or an LLM.
"""
import asyncio
import base64
import json
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.api_v1.api import api_router
from app.api.openapi.api import router as openapi_router
from app.core.security import create_access_token, get_current_admin, get_password_hash
from app.db.session import get_db
from app.models import AdminAllowlist, Document, KnowledgeBase, Role, User
from app.models.api_key import APIKey
from app.models.base import Base
from app.models.chat import Chat, Message
from app.models.knowledge import DocumentUpload, ProcessingTask
from app.services import authorization as policy


@compiles(LONGTEXT, "sqlite")
def sqlite_longtext(type_, compiler, **kwargs):
    return "TEXT"


@pytest.fixture
def world():
    uri = os.getenv("PHASE2_TEST_DATABASE_URI")
    if uri:
        # Added by ChatGPT: this opt-in mode deletes ONLY a named disposable schema.
        # Initialize it using the existing Alembic chain before running the tests.
        url = make_url(uri)
        assert url.host == "127.0.0.1" and url.database == "researchiq_phase2_test", "Refusing a non-test database"
        engine = sa.create_engine(uri)
        with engine.begin() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "riq_007"
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
    else:
        engine = sa.create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

        @sa.event.listens_for(engine, "connect")
        def configure(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_collation("utf8mb4_bin", lambda a, b: (a > b) - (a < b))

        Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    researcher, admin = Role(name="researcher"), Role(name="admin")
    db.add_all([researcher, admin])
    password_hash = get_password_hash("phase2-test-password")

    def user(name, **kwargs):
        row = User(username=name, email=f"{name}@uaf.edu.pk", hashed_password=password_hash,
                   is_active=True, is_system=False, is_superuser=False, **kwargs)
        row.roles = [researcher]
        db.add(row)
        return row

    alice, bob, professor, superuser, inactive = [user(name) for name in ["alice", "bob", "professor", "root", "inactive"]]
    professor.roles.append(admin)
    superuser.is_superuser = True
    inactive.is_active = False
    system = User(username="institutional_system", email="system@example.com", hashed_password=None,
                  is_system=True, is_active=False, is_superuser=False)
    db.add_all([system, AdminAllowlist(email=professor.email, is_active=True)])
    db.flush()

    def kb(owner, name, **kwargs):
        row = KnowledgeBase(name=name, user_id=owner.id, **kwargs)
        db.add(row)
        db.flush()
        return row

    alice_kb, bob_kb, admin_kb = [kb(owner, name) for owner, name in [(alice, "Alice"), (bob, "Bob"), (professor, "Professor")]]
    public_kb = kb(system, "Institutional", scope="public", is_system_managed=True)
    fake_public = kb(bob, "Not system owned", scope="public", is_system_managed=True)

    def document(collection):
        row = Document(knowledge_base_id=collection.id, file_name=f"{collection.name}.pdf",
                       file_path=f"kb_{collection.id}/test.pdf", file_size=100, content_type="application/pdf", file_hash="a" * 64)
        db.add(row)
        db.flush()
        return row

    alice_doc, bob_doc = document(alice_kb), document(bob_kb)
    chat = Chat(title="Alice chat", user_id=alice.id, knowledge_bases=[alice_kb])
    corrupt_chat = Chat(title="Invalid old association", user_id=alice.id, knowledge_bases=[bob_kb])
    db.add_all([chat, corrupt_chat])
    db.flush()
    db.add(Message(chat_id=corrupt_chat.id, role="assistant", content="Must not disclose"))
    for owner in [alice, bob, professor, superuser, inactive, system]:
        db.add(APIKey(user_id=owner.id, name="fixture", key=f"phase2-{owner.username}", is_active=True))
    uploads = []
    for collection in [alice_kb, bob_kb, public_kb]:
        upload = DocumentUpload(knowledge_base_id=collection.id, file_name="staged.pdf", file_hash="b" * 64,
                                file_size=100, content_type="application/pdf", temp_path=f"kb_{collection.id}/temp/staged.pdf",
                                created_at=datetime.utcnow() - timedelta(days=2))
        db.add(upload)
        uploads.append(upload)
    db.flush()
    task = ProcessingTask(knowledge_base_id=bob_kb.id, document_upload_id=uploads[1].id, status="pending")
    db.add(task)
    db.commit()

    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    app.include_router(openapi_router, prefix="/openapi")

    def database():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = database

    @app.get("/test/admin")
    def admin_dependency(current=Depends(get_current_admin)):
        return {"id": current.id}

    def headers(actor):
        return {"Authorization": "Bearer " + create_access_token({"sub": actor.username})}

    with TestClient(app) as client:
        yield SimpleNamespace(**locals())
    db.close()
    engine.dispose()


def test_roles_require_explicit_assignment_and_current_exact_allowlist(world):
    w = world
    assert policy.effective_roles(w.db, w.alice) == {"researcher"}
    assert policy.effective_roles(w.db, w.professor) == {"researcher", "admin"}
    assert policy.effective_roles(w.db, w.superuser) == {"researcher"}
    w.db.add(AdminAllowlist(email=w.alice.email, is_active=True))
    w.db.commit()
    assert policy.effective_roles(w.db, w.alice) == {"researcher"}
    w.bob.roles.append(w.admin)
    w.db.commit()
    assert policy.effective_roles(w.db, w.bob) == {"researcher"}


def test_admin_revocation_without_new_login(world):
    w = world
    headers = w.headers(w.professor)
    assert w.client.get("/test/admin", headers=headers).status_code == 200
    entry = w.db.query(AdminAllowlist).filter_by(email=w.professor.email).one()
    entry.is_active = False
    w.db.commit()
    assert w.client.get("/test/admin", headers=headers).status_code == 403
    entry.is_active = True
    w.professor.roles.remove(w.admin)
    w.db.commit()
    assert w.client.get("/test/admin", headers=headers).status_code == 403
    w.professor.roles.append(w.admin)
    w.db.delete(entry)
    w.db.commit()
    assert w.client.get("/test/admin", headers=headers).status_code == 403


@pytest.mark.parametrize("email, allowed", [(" PROFESSOR@UAF.EDU.PK ", True), ("professor+alias@uaf.edu.pk", False),
                                         ("professor@uaf.edu.pk.evil.test", False), ("profess\u00f3r@uaf.edu.pk", False)])
def test_email_normalization_has_no_domain_or_alias_shortcuts(world, email, allowed):
    world.professor.email = email
    world.db.commit()
    assert ("admin" in policy.effective_roles(world.db, world.professor)) is allowed


def test_registration_cannot_self_assign_privileges(world):
    w = world
    w.db.add(AdminAllowlist(email="newadmin@uaf.edu.pk", is_active=True))
    w.db.commit()
    response = w.client.post("/api/auth/register", json={"username": "newadmin", "email": "NEWADMIN@uaf.edu.pk",
        "password": "phase2-password", "is_superuser": True, "is_system": True, "roles": ["admin"]})
    assert response.status_code == 200
    created = w.db.query(User).filter_by(username="newadmin").one()
    assert created.email == "newadmin@uaf.edu.pk"
    assert not created.is_superuser and not created.is_system
    assert [role.name for role in created.roles] == ["researcher"]
    assert policy.effective_roles(w.db, created) == {"researcher"}


@pytest.mark.parametrize("actor", ["inactive", "system"])
def test_unavailable_identities_rejected_by_password_jwt_and_api_key(world, actor):
    w = world
    user = getattr(w, actor)
    assert w.client.post("/api/auth/token", data={"username": user.username, "password": "phase2-test-password"}).status_code == 401
    assert w.client.post("/api/auth/test-token", headers=w.headers(user)).status_code == 401
    with patch("app.services.retrieval_scope.EmbeddingsFactory.create") as embeddings:
        response = w.client.get(f"/openapi/knowledge/{w.alice_kb.id}/query", params={"query": "secret"}, headers={"X-API-Key": f"phase2-{user.username}"})
    assert response.status_code == 401
    embeddings.assert_not_called()
    assert w.db.query(APIKey).filter_by(user_id=user.id).one().last_used_at is None


@pytest.mark.parametrize("subject", [None, 1, [], {}, "missing-user"])
def test_invalid_token_subject_is_unauthorized(world, subject):
    token = create_access_token({"sub": subject})
    assert world.client.post("/api/auth/test-token", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("actor", ["alice", "professor", "superuser"])
def test_private_http_boundaries_for_researcher_admin_and_superuser(world, actor):
    w = world
    headers = w.headers(getattr(w, actor))
    prefix = f"/api/knowledge-base/{w.bob_kb.id}"
    requests = [
        ("GET", prefix, {}), ("PUT", prefix, {"json": {"name": "hijack"}}), ("DELETE", prefix, {}),
        ("GET", f"{prefix}/documents/{w.bob_doc.id}", {}),
        ("GET", f"{prefix}/documents/tasks", {"params": {"task_ids": str(w.task.id)}}),
        ("POST", f"{prefix}/documents/upload", {"files": {"files": ("evil.pdf", b"test", "application/pdf")}}),
        ("POST", f"{prefix}/documents/preview", {"json": {"document_ids": [w.bob_doc.id]}}),
        ("POST", f"{prefix}/documents/process", {"json": [{"upload_id": w.uploads[1].id}] }),
        ("POST", "/api/knowledge-base/test-retrieval", {"json": {"kb_id": w.bob_kb.id, "query": "secret", "top_k": 1}}),
        ("POST", "/api/chat/", {"json": {"title": "hijack", "knowledge_base_ids": [w.bob_kb.id]}}),
    ]
    with patch("app.api.api_v1.knowledge_base.get_minio_client") as minio, patch(
        "app.api.api_v1.knowledge_base.EmbeddingsFactory.create"
    ) as embeddings, patch("app.api.api_v1.knowledge_base.process_document_background") as processing:
        for method, path, kwargs in requests:
            response = w.client.request(method, path, headers=headers, **kwargs)
            assert response.status_code == 404, (method, path, response.text)
        minio.assert_not_called()
        embeddings.assert_not_called()
        processing.assert_not_called()
    listed = w.client.get("/api/knowledge-base", headers=headers).json()
    assert w.bob_kb.id not in {row["id"] for row in listed}


def test_nested_document_and_upload_ids_cannot_cross_collections(world):
    w = world
    prefix = f"/api/knowledge-base/{w.alice_kb.id}"
    headers = w.headers(w.alice)
    assert w.client.get(f"{prefix}/documents/{w.bob_doc.id}", headers=headers).status_code == 404
    with patch("app.api.api_v1.knowledge_base.preview_document") as preview:
        result = w.client.post(f"{prefix}/documents/preview", json={"document_ids": [w.uploads[1].id]}, headers=headers)
        assert result.status_code == 404
        preview.assert_not_called()
    assert w.client.post(f"{prefix}/documents/process", json=[{"upload_id": w.uploads[1].id}], headers=headers).status_code == 400
    assert w.client.get(f"{prefix}/documents/tasks", params={"task_ids": str(w.task.id)}, headers=headers).json() == {}


def test_corpus_guard_requires_admin_and_a_nonlogin_system_owner(world):
    w = world
    assert policy.require_corpus_admin(w.db, w.professor, w.public_kb.id).id == w.public_kb.id
    for user, collection, code in [(w.alice, w.public_kb, 403), (w.superuser, w.public_kb, 403),
                                    (w.professor, w.bob_kb, 404), (w.professor, w.fake_public, 404)]:
        with pytest.raises(HTTPException) as error:
            policy.require_corpus_admin(w.db, user, collection.id)
        assert error.value.status_code == code
    # Phase 2 does not enable catalog/public RAG through legacy collection routes.
    assert w.client.get(f"/api/knowledge-base/{w.public_kb.id}", headers=w.headers(w.professor)).status_code == 404
    assert w.client.post("/api/chat/", json={"title": "public", "knowledge_base_ids": [w.public_kb.id]}, headers=w.headers(w.professor)).status_code == 404


def test_stale_chat_sources_and_foreign_chat_access_rejected_before_streaming(world):
    w = world
    for chat, user in [(w.chat, w.bob), (w.chat, w.professor), (w.chat, w.superuser), (w.corrupt_chat, w.alice)]:
        headers = w.headers(user)
        assert w.client.get(f"/api/chat/{chat.id}", headers=headers).status_code == 404
        with patch("app.api.api_v1.chat.generate_response") as generate:
            response = w.client.post(f"/api/chat/{chat.id}/messages", json={"messages": [{"role": "user", "content": "secret"}]}, headers=headers)
        assert response.status_code == 404
        generate.assert_not_called()
    rows = w.client.get("/api/chat/", headers=w.headers(w.alice)).json()
    assert [row["id"] for row in rows] == [w.chat.id]


def test_direct_generation_service_checks_actor_and_exact_chat_sources(world):
    from app.services import chat_service
    w = world
    before = w.db.query(Message).count()

    async def collect(user, ids):
        return [part async for part in chat_service.generate_response("secret", {"messages": []}, ids, w.chat.id, w.db, user)]

    with patch.object(chat_service.EmbeddingsFactory, "create") as embeddings, patch.object(chat_service.LLMFactory, "create") as llm:
        for user, ids in [(w.professor, [w.alice_kb.id]), (w.alice, [w.bob_kb.id]), (w.alice, []), (w.system, [w.alice_kb.id])]:
            with pytest.raises(HTTPException):
                asyncio.run(collect(user, ids))
        embeddings.assert_not_called()
        llm.assert_not_called()
    assert w.db.query(Message).count() == before


def test_cleanup_is_owner_scoped_even_for_admin(world):
    w = world
    with patch("app.api.api_v1.knowledge_base.get_minio_client") as minio:
        result = w.client.post("/api/knowledge-base/cleanup", headers=w.headers(w.professor))
        assert result.status_code == 200
        minio.return_value.remove_object.assert_not_called()
        result = w.client.post("/api/knowledge-base/cleanup", headers=w.headers(w.alice))
        assert result.status_code == 200
        minio.return_value.remove_object.assert_called_once()
        assert minio.return_value.remove_object.call_args.kwargs["object_name"] == w.uploads[0].temp_path
    assert w.db.query(DocumentUpload).filter_by(id=w.uploads[1].id).count() == 1
    assert w.db.query(DocumentUpload).filter_by(id=w.uploads[2].id).count() == 1


def test_api_key_retrieval_and_key_management_preserve_ownership(world):
    w = world
    from app.services import retrieval_scope as knowledge
    for user in [w.alice, w.professor, w.superuser]:
        with patch.object(knowledge.EmbeddingsFactory, "create") as embeddings:
            result = w.client.get(f"/openapi/knowledge/{w.bob_kb.id}/query", params={"query": "secret"}, headers={"X-API-Key": f"phase2-{user.username}"})
        assert result.status_code == 404
        embeddings.assert_not_called()
        foreign_key = w.db.query(APIKey).filter_by(user_id=w.bob.id).one()
        assert w.client.put(f"/api/api-keys/{foreign_key.id}", json={"name": "hijack"}, headers=w.headers(user)).status_code == 403
        assert w.client.delete(f"/api/api-keys/{foreign_key.id}", headers=w.headers(user)).status_code == 403


def test_owner_access_and_api_key_retrieval_still_work(world):
    w = world
    from app.services import retrieval_scope as knowledge
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_id=w.alice_doc.id, status="completed"))
    w.db.commit()
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}", headers=w.headers(w.alice)).status_code == 200
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}/documents/{w.alice_doc.id}", headers=w.headers(w.alice)).status_code == 200
    assert w.client.get(f"/api/chat/{w.chat.id}", headers=w.headers(w.alice)).status_code == 200
    with patch.object(knowledge.EmbeddingsFactory, "create"), patch.object(knowledge.VectorStoreFactory, "create") as store:
        store.return_value.search_permitted.return_value = []
        result = w.client.get(f"/openapi/knowledge/{w.alice_kb.id}/query", params={"query": "own research"}, headers={"X-API-Key": "phase2-alice"})
        assert result.status_code == 200
        store.assert_called_once()


def test_private_creation_ignores_client_ownership_and_scope_fields(world):
    w = world
    response = w.client.post("/api/knowledge-base", json={"name": "Private by default", "user_id": w.bob.id,
        "scope": "public", "is_system_managed": True}, headers=w.headers(w.alice))
    assert response.status_code == 200
    kb = w.db.get(KnowledgeBase, response.json()["id"])
    assert kb.user_id == w.alice.id and kb.scope == "private" and not kb.is_system_managed


def test_authorized_http_chat_streams_and_persists_citations_from_both_collections(world):
    # Added by ChatGPT: real JWT -> endpoint -> authorization -> RAG -> SQL path;
    # only the embedding/vector/LLM providers are replaced with deterministic fixtures.
    from langchain_core.documents import Document as Evidence
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from app.models.knowledge import DocumentChunk
    from app.services import chat_service
    w = world
    second = w.kb(w.alice, "Second private collection")
    second_doc = w.document(second)
    w.db.commit()
    stores = []
    for kb, doc in [(w.alice_kb, w.alice_doc), (second, second_doc)]:
        store = MagicMock()
        chunk_id = f"phase9-{doc.id}"
        w.db.add(ProcessingTask(knowledge_base_id=kb.id, document_id=doc.id, status="completed"))
        w.db.add(DocumentChunk(id=chunk_id, kb_id=kb.id, document_id=doc.id,
            file_name=doc.file_name, hash=chunk_id,
            chunk_metadata={"page_content": "Synthetic irrigation evidence", "page": 0}))
        store.search_permitted.return_value = [(Evidence(
            page_content="Untrusted provider text", metadata={"chunk_id": chunk_id, "kb_id": kb.id, "document_id": doc.id}
        ), 0.1)]
        stores.append(store)
    w.db.commit()
    headers = w.headers(w.alice)
    created = w.client.post("/api/chat/", json={"title": "Grounded chat", "knowledge_base_ids": [w.alice_kb.id, second.id]}, headers=headers)
    assert created.status_code == 200
    chat_id = created.json()["id"]
    with patch.object(chat_service.EmbeddingsFactory, "create"), patch.object(
        chat_service.VectorStoreFactory, "create", side_effect=stores
    ), patch.object(chat_service.LLMFactory, "create", return_value=FakeListChatModel(
        responses=['{"text":"Irrigation findings differ.","citations":["E1","E2"]}']
    )):
        response = w.client.post(f"/api/chat/{chat_id}/messages", json={"messages": [
            {"role": "user", "content": "Compare irrigation findings."}
        ]}, headers=headers)
    assert response.status_code == 200
    frames = response.text.splitlines()
    assert not any(frame.startswith("3:") for frame in frames)
    assert any(frame.startswith("d:") for frame in frames)
    text = "".join(json.loads(frame[2:]) for frame in frames if frame.startswith("0:"))
    encoded, answer = text.split("__LLM_RESPONSE__", 1)
    context = json.loads(base64.b64decode(encoded))["context"]
    assert {item["metadata"]["document_id"] for item in context} == {w.alice_doc.id, second_doc.id}
    assert "[citation:1][citation:2]" in answer
    saved = w.client.get(f"/api/chat/{chat_id}", headers=headers).json()["messages"]
    assert len(saved) == 2 and saved[-1]["content"] == text


def test_disabled_api_key_and_invalid_or_expired_tokens_are_rejected(world):
    w = world
    key = w.db.query(APIKey).filter_by(user_id=w.alice.id).one()
    key.is_active = False
    w.db.commit()
    response = w.client.get(f"/openapi/knowledge/{w.alice_kb.id}/query", params={"query": "own"}, headers={"X-API-Key": key.key})
    assert response.status_code == 401
    assert w.client.get("/api/knowledge-base", headers={"Authorization": "Bearer invalid"}).status_code == 401
    token = create_access_token({"sub": w.alice.username}, expires_delta=timedelta(seconds=-1))
    assert w.client.get("/api/knowledge-base", headers={"Authorization": f"Bearer {token}"}).status_code == 401
