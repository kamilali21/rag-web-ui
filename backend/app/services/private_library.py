"""Owner-scoped discovery and deletion over the existing private ingestion records."""
from pathlib import PurePosixPath

from fastapi import HTTPException
from sqlalchemy import select, func, literal, exists, or_

from app.core.config import settings
from app.core.minio import get_minio_client
from app.models.knowledge import KnowledgeBase, Document, DocumentUpload, ProcessingTask
from app.models.researcher import PublicationRequest
from app.services.authorization import private_kb_filter, require_private_knowledge_base
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.vector_store import VectorStoreFactory


def lock_collection(db, actor, kb_id):
    row = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, private_kb_filter(actor)).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Knowledge base not found")
    return row


def catalog(db, actor, *, kb_id=None, search="", category=None, status=None, skip=0, limit=20):
    if kb_id is not None:
        require_private_knowledge_base(db, actor, kb_id)
    # Include staged uploads even when processing failed before creating a Document.
    document_status = select(ProcessingTask.status).where(ProcessingTask.document_id == Document.id).order_by(ProcessingTask.id.desc()).limit(1).scalar_subquery()
    upload_status = select(ProcessingTask.status).where(ProcessingTask.document_upload_id == DocumentUpload.id).order_by(ProcessingTask.id.desc()).limit(1).scalar_subquery()
    linked = exists().where(ProcessingTask.document_upload_id == DocumentUpload.id, ProcessingTask.document_id.isnot(None))
    def columns(model, identity, state):
        return [identity.label("id"), model.knowledge_base_id, model.file_name, model.file_size,
                model.content_type, model.created_at, state.label("status")]
    docs = select(*columns(Document, Document.id, func.coalesce(document_status, "unknown"))).join(KnowledgeBase).where(private_kb_filter(actor))
    uploads = select(*columns(DocumentUpload, -DocumentUpload.id, func.coalesce(upload_status, DocumentUpload.status))).join(KnowledgeBase).where(private_kb_filter(actor), ~linked)
    rows = docs.union_all(uploads).subquery()
    query = db.query(rows)
    if kb_id is not None:
        query = query.filter(rows.c.knowledge_base_id == kb_id)
    if search.strip():
        query = query.filter(rows.c.file_name.icontains(search.strip(), autoescape=True))
    shortcuts = {"Papers": ["paper"], "Theses": ["thesis", "theses", "dissertation"], "Reports": ["report"]}
    if category:
        query = query.filter(or_(*(rows.c.file_name.icontains(word) for word in shortcuts[category])))
    if status:
        query = query.filter(rows.c.status == status)
    total = query.count()
    items = []
    for row in query.order_by(rows.c.created_at.desc(), rows.c.id.desc()).offset(skip).limit(limit).all():
        item = dict(row._mapping)
        state = item.pop("status")
        item["processing_tasks"] = [{"id": 0, "status": state}]
        item["upload_id"] = -row.id if row.id < 0 else None
        items.append(item)
    active = db.query(ProcessingTask.id).join(KnowledgeBase).filter(private_kb_filter(actor), ProcessingTask.status.in_(["pending", "processing"]))
    if kb_id is not None:
        active = active.filter(ProcessingTask.knowledge_base_id == kb_id)
    return {"items": items, "total": total, "has_active_tasks": active.first() is not None}


def object_path(kb_id, path):
    parts = PurePosixPath(path).parts
    if not path.startswith(f"kb_{kb_id}/") or ".." in parts or "\\" in path:
        raise HTTPException(409, "Invalid stored object path; cleanup requires review")
    return path


def mark_cleanup_failed(db, actor, kb_id, document_id=None, upload_ids=None):
    """A partially deleted file must no longer advertise a Ready processing state."""
    db.rollback()
    lock_collection(db, actor, kb_id)
    query = db.query(ProcessingTask).filter(ProcessingTask.knowledge_base_id == kb_id)
    if document_id is not None or upload_ids is not None:
        query = query.filter(or_(ProcessingTask.document_id == document_id if document_id else literal(False),
                                 ProcessingTask.document_upload_id.in_(upload_ids or [])))
    for task in query.with_for_update().all():
        task.status = "failed"
        task.error_message = "Deletion incomplete; retry deletion before using this file."
    db.commit()


def delete_item(db, actor, kb_id, *, document_id=None, upload_id=None):
    lock_collection(db, actor, kb_id)
    document = None
    if document_id is not None:
        document = db.query(Document).filter_by(id=document_id, knowledge_base_id=kb_id).populate_existing().with_for_update().first()
        if document is None:
            raise HTTPException(404, "Document not found")
        # Also cover historical private jobs that failed before linking their document.
        uploads = db.query(DocumentUpload).filter_by(knowledge_base_id=kb_id, file_name=document.file_name).with_for_update().all()
    else:
        uploads = db.query(DocumentUpload).filter_by(id=upload_id, knowledge_base_id=kb_id).with_for_update().all()
        if not uploads:
            raise HTTPException(404, "Upload not found")
        if db.query(Document.id).filter_by(knowledge_base_id=kb_id, file_name=uploads[0].file_name).first():
            raise HTTPException(409, "Remove the associated document first")
    upload_ids = [upload.id for upload in uploads]
    tasks = db.query(ProcessingTask).filter(ProcessingTask.knowledge_base_id == kb_id,
        or_(ProcessingTask.document_id == document_id if document else literal(False),
            ProcessingTask.document_upload_id.in_(upload_ids))).populate_existing().with_for_update().all()
    if any(task.status in {"pending", "processing"} for task in tasks):
        raise HTTPException(409, "Wait for processing to finish before deleting")
    if document and db.query(PublicationRequest.id).filter_by(
            source_document_id=document.id, status="processing").first():
        raise HTTPException(409, "An approved publication copy is still processing")
    paths = {object_path(kb_id, upload.temp_path) for upload in uploads}
    if document:
        paths.add(object_path(kb_id, document.file_path))
    else:
        paths.add(object_path(kb_id, f"kb_{kb_id}/{uploads[0].file_name}"))
    try:
        # Never discard SQL cleanup references until BOTH external stores succeed.
        if document and document.chunks:
            store = VectorStoreFactory.create(store_type=settings.VECTOR_STORE_TYPE,
                collection_name=f"kb_{kb_id}", embedding_function=EmbeddingsFactory.create())
            ids = [chunk.id for chunk in document.chunks]
            for offset in range(0, len(ids), 1000):
                store.delete(ids[offset:offset + 1000])
        client = get_minio_client()
        for path in paths:
            client.remove_object(settings.MINIO_BUCKET_NAME, path)
        for task in tasks:
            db.delete(task)
        db.flush()
        for upload in uploads:
            db.delete(upload)
        if document:
            # Keep the submission audit row when its private source is deleted.
            db.query(PublicationRequest).filter_by(source_document_id=document.id, status="pending").update(
                {PublicationRequest.status: "cancelled"}, synchronize_session=False)
            db.delete(document)
        db.commit()
    except Exception:
        mark_cleanup_failed(db, actor, kb_id, document_id, upload_ids)
        raise HTTPException(503, "Cleanup incomplete. Records retained; retry deletion before using this file.") from None
