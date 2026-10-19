"""Phase 14 discovery and selection only: no generation or persisted analysis."""
from fastapi import HTTPException
from sqlalchemy import func, or_
from app.models import AcademicDocumentMetadata as Metadata, Department, Document, KnowledgeBase
from app.services.retrieval_scope import ready_document_query


def rows_query(db, actor, scope):
    return ready_document_query(db, actor, scope).with_entities(
        Document, KnowledgeBase.scope, Metadata, Department.name,
    ).outerjoin(Department, Department.id == Metadata.department_id)


def serialize(row):
    document, scope, metadata, department = row
    return {
        "id": document.id, "knowledge_base_id": document.knowledge_base_id,
        "scope": scope, "title": metadata.title if metadata else document.file_name,
        "file_name": document.file_name, "file_size": document.file_size,
        "content_type": document.content_type, "created_at": document.created_at,
        "authors_text": metadata.authors_text if metadata else None,
        "department_id": metadata.department_id if metadata else None,
        "department_name": department, "document_type": metadata.document_type if metadata else None,
        "publication_year": metadata.publication_year if metadata else None,
        "abstract": metadata.abstract if metadata else None,
    }


def catalog(db, actor, *, scope="public", search="", author="", department_id=None,
            document_type=None, year_from=None, year_to=None, before_id=None, limit=20):
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(422, "From year must not exceed to year")
    query = rows_query(db, actor, scope)
    if search.strip():
        query = query.filter(or_(*(field.icontains(search.strip(), autoescape=True) for field in (
            func.coalesce(Metadata.title, Document.file_name), Document.file_name, Metadata.authors_text, Metadata.abstract))))
    if author.strip():
        query = query.filter(Metadata.authors_text.icontains(author.strip(), autoescape=True))
    if department_id is not None:
        query = query.filter(Metadata.department_id == department_id)
    if document_type:
        query = query.filter(Metadata.document_type == document_type)
    if year_from is not None:
        query = query.filter(Metadata.publication_year >= year_from)
    if year_to is not None:
        query = query.filter(Metadata.publication_year <= year_to)
    if before_id is not None:
        query = query.filter(Document.id < before_id)
    rows = query.order_by(Document.id.desc()).limit(limit + 1).all()
    return {"items": [serialize(row) for row in rows[:limit]], "has_more": len(rows) > limit}


def selection(db, actor, scope, document_ids):
    # One current request/snapshot, no trust in previously returned browser rows.
    rows = rows_query(db, actor, scope).filter(Document.id.in_(document_ids)).all()
    if len(rows) != len(document_ids):
        raise HTTPException(404, "Selected documents are unavailable. Refresh your selection.")
    by_id = {row[0].id: serialize(row) for row in rows}
    return [by_id[identity] for identity in document_ids]
