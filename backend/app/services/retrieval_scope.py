"""Permission-scoped retrieval with optional exact Phase 11 document selection."""
from typing import Literal
import math

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import AcademicDocumentMetadata, Department, Document, KnowledgeBase, User
from app.models.knowledge import ProcessingTask, DocumentChunk
from app.services.authorization import private_kb_filter, require_active_user, require_private_knowledge_bases
from app.services.public_corpus import get_corpus
from app.core.config import settings
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.vector_store import VectorStoreFactory

SourceScope = Literal["public", "private", "both"]


def resolve_scope(db: Session, actor: User, scope: SourceScope, *, knowledge_base_ids: list[int] | None = None,
                  document_ids: list[int] | None = None) -> dict[int, list[int]]:
    """Return KB -> ready document IDs, using SQL rather than client/vector claims.

    Empty means no permitted sources; callers must not fall back to an unfiltered
    search. Re-resolve before exposing evidence if an external request intervenes.
    Private collection selections also apply inside Both conversations.
    Exact document selections reject the entire request if any ID is unavailable.
    """
    require_active_user(actor)
    if scope not in {"public", "private", "both"}:
        raise HTTPException(422, "Scope must be public, private or both")
    if document_ids is not None and (not isinstance(document_ids, list) or not 1 <= len(document_ids) <= 20
            or any(type(value) is not int or value <= 0 for value in document_ids)):
        raise HTTPException(422, "Select between 1 and 20 positive integer document IDs")
    if knowledge_base_ids is not None:
        if scope == "public":
            raise HTTPException(422, "Collection selection applies only to private sources")
        require_private_knowledge_bases(db, actor, knowledge_base_ids)
    permitted = []
    if scope in {"private", "both"}:
        private = private_kb_filter(actor)
        if knowledge_base_ids is not None:
            private = and_(private, KnowledgeBase.id.in_(knowledge_base_ids))
        permitted.append(private)
    if scope in {"public", "both"}:
        corpus = get_corpus(db, actor)
        permitted.append(and_(KnowledgeBase.id == corpus.id, KnowledgeBase.scope == "public",
                              KnowledgeBase.is_system_managed.is_(True),
                              AcademicDocumentMetadata.publication_status == "published"))
    latest_status = select(ProcessingTask.status).where(
        ProcessingTask.document_id == Document.id,
        ProcessingTask.knowledge_base_id == Document.knowledge_base_id,
    ).order_by(ProcessingTask.id.desc()).limit(1).scalar_subquery()
    query = db.query(Document.knowledge_base_id, Document.id).join(KnowledgeBase).outerjoin(
        AcademicDocumentMetadata, AcademicDocumentMetadata.document_id == Document.id,
    ).filter(or_(*permitted), latest_status == "completed")
    if document_ids is not None:
        query = query.filter(Document.id.in_(document_ids))
    rows = query.order_by(Document.knowledge_base_id, Document.id).all()
    if document_ids is not None and len(rows) != len(set(document_ids)):
        raise HTTPException(404, "Selected documents are unavailable")
    sources: dict[int, list[int]] = {}
    for kb_id, document_id in rows:
        sources.setdefault(kb_id, []).append(document_id)
    return sources


def search_scope(db: Session, actor: User, scope: SourceScope, query: str, top_k: int = 5,
                 *, knowledge_base_ids: list[int] | None = None, document_ids: list[int] | None = None):
    if not query.strip() or len(query) > 4000 or not 1 <= top_k <= 20:
        raise HTTPException(422, "Use a non-empty query up to 4000 characters and top_k between 1 and 20")
    require_active_user(actor)
    actor_id = actor.id
    sources = resolve_scope(db, actor, scope, knowledge_base_ids=knowledge_base_ids, document_ids=document_ids)
    if not sources:
        return []
    db.rollback()  # Release the read snapshot before the external requests.
    candidates = []
    candidate_limit = min(top_k * 5, 100)
    try:
        embeddings = EmbeddingsFactory.create()
        for kb_id, permitted_ids in sources.items():
            store = VectorStoreFactory.create(store_type=settings.VECTOR_STORE_TYPE,
                collection_name=f"kb_{kb_id}", embedding_function=embeddings)
            # Bound each provider filter and keep a bounded candidate pool across collections.
            for offset in range(0, len(permitted_ids), 500):
                batch = permitted_ids[offset:offset + 500]
                for candidate, score in store.search_permitted(query, batch, kb_id, k=candidate_limit):
                    chunk_id = candidate.metadata.get("chunk_id")
                    if isinstance(chunk_id, str) and math.isfinite(float(score)):
                        candidates.append((float(score), kb_id, chunk_id))
                candidates = sorted(set(candidates))[:candidate_limit]
    except Exception:
        raise HTTPException(503, "Scoped retrieval unavailable") from None
    # A fresh SQL read is essential under MySQL REPEATABLE READ after publication/owner changes.
    db.rollback()
    actor = db.get(User, actor_id)
    require_active_user(actor)
    permitted = resolve_scope(db, actor, scope, knowledge_base_ids=knowledge_base_ids, document_ids=document_ids)
    ids = [chunk_id for _, _, chunk_id in candidates]
    rows = db.query(DocumentChunk, Document).join(Document, Document.id == DocumentChunk.document_id).filter(
        DocumentChunk.id.in_(ids), DocumentChunk.kb_id == Document.knowledge_base_id).all()
    trusted = {(chunk.kb_id, chunk.id): (chunk, doc) for chunk, doc in rows
               if doc.id in permitted.get(chunk.kb_id, [])}
    results, seen = [], set()
    for score, kb_id, chunk_id in candidates:
        key = (kb_id, chunk_id)
        if key not in trusted or key in seen:
            continue
        chunk, document = trusted[key]
        metadata = chunk.chunk_metadata or {}
        content = metadata.get("page_content")
        if not isinstance(content, str) or not content:
            continue
        academic = document.academic_metadata
        department = db.get(Department, academic.department_id) if academic and academic.department_id else None
        results.append({"content": content, "score": score, "metadata": {
            "chunk_id": chunk_id, "document_id": document.id, "kb_id": kb_id,
            "scope": document.knowledge_base.scope, "file_name": document.file_name,
            "page": metadata.get("page"), "knowledge_base_name": document.knowledge_base.name,
            "title": academic.title if academic else document.file_name,
            "authors": academic.authors_text if academic else None,
            "department": department.name if department else None,
            "year": academic.publication_year if academic else None}})
        seen.add(key)
        if len(results) == top_k:
            break
    return results


def search_documents(db: Session, actor: User, document_ids: list[int], query: str,
                     top_k: int = 5, *, scope: SourceScope = "both"):
    """Exact selection for research workflows; never fall back to the whole scope."""
    if document_ids is None:
        raise HTTPException(422, "Select document IDs before retrieving evidence")
    return search_scope(db, actor, scope, query, top_k, document_ids=document_ids)
