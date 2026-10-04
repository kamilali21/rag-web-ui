"""Phase 9: resolve permitted sources before touching vector stores or an LLM."""
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import AcademicDocumentMetadata, Document, KnowledgeBase, User
from app.models.knowledge import ProcessingTask
from app.services.authorization import private_kb_filter, require_active_user
from app.services.public_corpus import get_corpus

SourceScope = Literal["public", "private", "both"]


def resolve_scope(db: Session, actor: User, scope: SourceScope) -> dict[int, list[int]]:
    """Return KB -> ready document IDs, using SQL rather than client/vector claims.

    Empty means no permitted sources; callers must not fall back to an unfiltered
    search. Re-resolve before exposing evidence if an external request intervenes.
    Chat source selection and exact selected-document mode belong to later gates.
    """
    require_active_user(actor)
    if scope not in {"public", "private", "both"}:
        raise HTTPException(422, "Scope must be public, private or both")
    permitted = []
    if scope in {"private", "both"}:
        permitted.append(private_kb_filter(actor))
    if scope in {"public", "both"}:
        corpus = get_corpus(db, actor)
        permitted.append(and_(KnowledgeBase.id == corpus.id, KnowledgeBase.scope == "public",
                              KnowledgeBase.is_system_managed.is_(True),
                              AcademicDocumentMetadata.publication_status == "published"))
    latest_status = select(ProcessingTask.status).where(
        ProcessingTask.document_id == Document.id,
        ProcessingTask.knowledge_base_id == Document.knowledge_base_id,
    ).order_by(ProcessingTask.id.desc()).limit(1).scalar_subquery()
    rows = db.query(Document.knowledge_base_id, Document.id).join(KnowledgeBase).outerjoin(
        AcademicDocumentMetadata, AcademicDocumentMetadata.document_id == Document.id,
    ).filter(or_(*permitted), latest_status == "completed").order_by(Document.knowledge_base_id, Document.id).all()
    sources: dict[int, list[int]] = {}
    for kb_id, document_id in rows:
        sources.setdefault(kb_id, []).append(document_id)
    return sources
