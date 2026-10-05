"""Added by ChatGPT: system-owned corpus lifecycle on the existing ingestion/storage stack."""
import hashlib
import logging
import math
import re
from datetime import datetime
from io import BytesIO
from pathlib import PurePosixPath
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile
from sqlalchemy import and_, or_, func
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.mysql import match as mysql_match
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, contains_eager
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.minio import get_minio_client
from app.db.session import SessionLocal
from app.models import AcademicDocumentMetadata, Document, DocumentChunk, KnowledgeBase, User
from app.models.knowledge import DocumentUpload, ProcessingTask
from app.models.research import Bookmark, Department
from app.services.authorization import require_active_user, require_admin, require_corpus_admin
from app.services.document_processor import process_document_background
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.vector_store import VectorStoreFactory

SYSTEM_USERNAME = "researchiq_system"
SYSTEM_EMAIL = "researchiq-system@internal.invalid"
CORPUS_NAME = "UAF Research Corpus"
MAX_FILE_BYTES = 20 * 1024 * 1024
CONTENT_TYPES = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown",
                 ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
logger = logging.getLogger(__name__)


def _system_owner(db: Session, *, lock: bool = False) -> User:
    query = db.query(User).filter(User.username == SYSTEM_USERNAME).populate_existing()
    owner = (query.with_for_update() if lock else query).first()
    if (owner is None or owner.username != SYSTEM_USERNAME or owner.email != SYSTEM_EMAIL
            or not owner.is_system or owner.is_active or owner.is_superuser or owner.hashed_password is not None):
        raise HTTPException(503, "Institutional ownership configuration unavailable")
    return owner


def provision_corpus(db: Session) -> KnowledgeBase:
    """Trusted startup operation; never converts an existing human or private collection."""
    try:
        values = dict(username=SYSTEM_USERNAME, email=SYSTEM_EMAIL, hashed_password=None,
                      is_system=True, is_active=False, is_superuser=False)
        # The unique owner row is also the provisioning mutex across startup workers.
        if db.bind.dialect.name == "mysql":
            statement = mysql_insert(User).values(**values).on_duplicate_key_update(id=User.id)
        else:
            statement = sqlite_insert(User).values(**values).on_conflict_do_nothing()
        db.execute(statement)
        owner = _system_owner(db, lock=True)
        rows = db.query(KnowledgeBase).filter_by(user_id=owner.id).populate_existing().with_for_update().all()
        if rows:
            if len(rows) != 1 or rows[0].scope != "public" or not rows[0].is_system_managed:
                raise HTTPException(503, "Institutional corpus configuration unavailable")
            corpus = rows[0]
        else:
            corpus = KnowledgeBase(name=CORPUS_NAME, description="Shared institutional research at UAF.",
                                   user_id=owner.id, scope="public", is_system_managed=True)
            db.add(corpus)
        db.commit()
        db.refresh(corpus)
        return corpus
    except Exception:
        db.rollback()
        raise


def get_corpus(db: Session, actor: User, *, manage: bool = False) -> KnowledgeBase:
    require_active_user(actor)
    if manage:
        require_admin(db, actor)
    owner = _system_owner(db)
    rows = db.query(KnowledgeBase).filter_by(user_id=owner.id).all()
    if len(rows) != 1 or rows[0].scope != "public" or not rows[0].is_system_managed:
        raise HTTPException(503, "Institutional corpus configuration unavailable")
    if manage:
        return require_corpus_admin(db, actor, rows[0].id)
    return rows[0]


def _lock_corpus(db: Session, actor: User):
    corpus = get_corpus(db, actor, manage=True)
    # ponytail: serialize rare admin writes per corpus; use per-document locks if write throughput demands it.
    db.query(KnowledgeBase).filter_by(id=corpus.id).with_for_update().one()
    return corpus


def document_query(db: Session, corpus_id: int, *, published: bool = True):
    query = db.query(Document).filter(Document.knowledge_base_id == corpus_id)
    if published:
        query = query.join(AcademicDocumentMetadata).filter(AcademicDocumentMetadata.publication_status == "published")
    return query


def get_document(db: Session, actor: User, document_id: int, *, manage: bool = False) -> Document:
    corpus = get_corpus(db, actor, manage=manage)
    query = document_query(db, corpus.id, published=not manage).filter(Document.id == document_id)
    if manage:
        query = query.populate_existing().with_for_update()
    document = query.first()
    if document is None:
        raise HTTPException(404, "Document not found")
    if manage:
        # A locking current read avoids an older MySQL snapshot after waiting on an admin write.
        document.academic_metadata = db.query(AcademicDocumentMetadata).filter_by(
            document_id=document.id).populate_existing().with_for_update().first()
    return document


def document_summary(document: Document):
    return {"id": document.id, "knowledge_base_id": document.knowledge_base_id,
            "file_name": document.file_name, "file_size": document.file_size,
            "content_type": document.content_type, "created_at": document.created_at,
            "publication_status": document.academic_metadata.publication_status if document.academic_metadata else "draft"}


# Added by ChatGPT: bounded relational discovery extends the existing corpus list, not the RAG pipeline.
def list_documents(db: Session, actor: User, *, before_id=None, limit=50, include_unpublished=False,
                   search="", author="", department_id=None, year_from=None, year_to=None, document_type=None, bookmarked=False):
    corpus = get_corpus(db, actor, manage=include_unpublished)
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(422, "Start year must not exceed end year")
    metadata = AcademicDocumentMetadata
    query = db.query(Document, Department, Bookmark.id).outerjoin(metadata, metadata.document_id == Document.id).outerjoin(
        Department, Department.id == metadata.department_id).outerjoin(Bookmark, and_(Bookmark.document_id == Document.id,
        Bookmark.user_id == actor.id)).options(contains_eager(Document.academic_metadata)).filter(
        Document.knowledge_base_id == corpus.id)
    if bookmarked:
        query = query.filter(Bookmark.id.isnot(None))
    if not include_unpublished:
        query = query.filter(metadata.publication_status == "published")
    if before_id is not None:
        query = query.filter(Document.id < before_id)
    if department_id is not None:
        query = query.filter(metadata.department_id == department_id)
    if document_type is not None:
        query = query.filter(metadata.document_type == document_type)
    if year_from is not None:
        query = query.filter(metadata.publication_year >= year_from)
    if year_to is not None:
        query = query.filter(metadata.publication_year <= year_to)
    if author.strip():
        query = query.filter(metadata.authors_text.icontains(author.strip(), autoescape=True))
    if search.strip():
        words = re.findall(r"[^\W_]+", search, flags=re.UNICODE)
        if not words:
            return []
        if len(words) > 20:
            raise HTTPException(422, "Use up to 20 search words")
        indexed_words = [word for word in words if len(word) >= 3]
        if db.bind.dialect.name == "mysql" and indexed_words:
            # Only normalized words become boolean prefix terms; user operators never reach MATCH syntax.
            query = query.filter(mysql_match(metadata.title, metadata.authors_text, metadata.abstract,
                against=" ".join(f"+{word}*" for word in indexed_words), in_boolean_mode=True))
        # ponytail: short acronyms/author substrings scan scoped rows; add a measured ngram index if needed.
        # SQLite is a lightweight fallback; production uses FULLTEXT for ordinary words.
        for word in words if db.bind.dialect.name != "mysql" else [word for word in words if len(word) < 3]:
            query = query.filter(or_(*(column.icontains(word, autoescape=True)
                for column in (metadata.title, metadata.authors_text, metadata.abstract))))
    result = []
    for document, department, bookmark_id in query.order_by(Document.id.desc()).limit(min(max(limit, 1), 100)).all():
        academic = document.academic_metadata
        result.append({**document_summary(document),
            "title": academic.title if academic else document.file_name,
            "authors_text": academic.authors_text if academic else None,
            "department_id": academic.department_id if academic else None,
            "department_name": department.name if department else None,
            "document_type": academic.document_type if academic else None,
            "publication_year": academic.publication_year if academic else None,
            "is_bookmarked": bookmark_id is not None})
    return result


def set_bookmark(db: Session, actor: User, document_id: int, saved: bool):
    """Added by ChatGPT: idempotent user-owned references, never copies or publication permissions."""
    corpus = get_corpus(db, actor)
    # Current reads serialize bookmarks with unpublish/delete and concurrent duplicate saves.
    document = document_query(db, corpus.id).filter(Document.id == document_id).with_for_update().first()
    if document is None:
        raise HTTPException(404, "Document not found")
    bookmark = db.query(Bookmark).filter_by(user_id=actor.id, document_id=document_id).with_for_update().first()
    if saved and bookmark is None:
        db.add(Bookmark(user_id=actor.id, document_id=document_id))
    elif not saved and bookmark is not None:
        db.delete(bookmark)
    db.commit()


# Added by ChatGPT: an admin-only, bounded inbox includes failed uploads without a document yet.
def list_uploads(db: Session, actor: User, *, before_id=None, limit=50, search="", status=None, publication_status=None):
    corpus = get_corpus(db, actor, manage=True)
    query = db.query(ProcessingTask, DocumentUpload, Document, AcademicDocumentMetadata).outerjoin(
        DocumentUpload, DocumentUpload.id == ProcessingTask.document_upload_id).outerjoin(
        Document, Document.id == ProcessingTask.document_id).outerjoin(
        AcademicDocumentMetadata, AcademicDocumentMetadata.document_id == Document.id).filter(
        ProcessingTask.knowledge_base_id == corpus.id,
        or_(Document.id.is_(None), Document.knowledge_base_id == corpus.id),
        or_(DocumentUpload.id.is_(None), DocumentUpload.knowledge_base_id == corpus.id))
    if before_id is not None:
        query = query.filter(ProcessingTask.id < before_id)
    if status:
        query = query.filter(ProcessingTask.status == status)
    if publication_status:
        query = query.filter(func.coalesce(AcademicDocumentMetadata.publication_status, "draft") == publication_status)
    if search.strip():
        query = query.filter(or_(*(column.icontains(search.strip(), autoescape=True) for column in
            (Document.file_name, DocumentUpload.file_name, AcademicDocumentMetadata.title))))
    return [{"id": task.id, "document_id": task.document_id, "upload_id": task.document_upload_id,
        "file_name": document.file_name if document else upload.file_name if upload else "Unavailable source",
        "title": metadata.title if metadata else None, "status": task.status,
        "publication_status": metadata.publication_status if metadata else "draft",
        "created_at": task.created_at,
        "error_message": "Processing failed; retry the retained source." if task.status == "failed" else None}
        for task, upload, document, metadata in query.order_by(ProcessingTask.id.desc()).limit(min(max(limit, 1), 100)).all()]


def archive_document(db: Session, actor: User, document_id: int):
    """Added by ChatGPT: terminal hiding; use unpublish for reversible withdrawal."""
    _lock_corpus(db, actor)
    document = get_document(db, actor, document_id, manage=True)
    tasks = db.query(ProcessingTask).filter_by(document_id=document.id).populate_existing().with_for_update().all()
    if any(task.status in {"pending", "processing"} for task in tasks):
        raise HTTPException(409, "Document is still processing")
    if document.academic_metadata is None:
        document.academic_metadata = AcademicDocumentMetadata(title=document.file_name)
    document.academic_metadata.publication_status = "archived"
    document.academic_metadata.published_at = None
    db.commit()
    return document


def _filename(name: str) -> str:
    if (not name or len(name) > 150 or len(name.encode("utf-8")) > 180 or name in {".", ".."} or "/" in name or "\\" in name
            or any(ord(c) < 32 or ord(c) == 127 for c in name)
            or PurePosixPath(name).suffix.lower() not in CONTENT_TYPES):
        raise HTTPException(400, "Use a filename of up to 150 characters with PDF, DOCX, TXT or MD extension")
    return name


def _object_path(corpus_id: int, path: str) -> str:
    if not path.startswith(f"kb_{corpus_id}/") or ".." in PurePosixPath(path).parts or "\\" in path:
        raise HTTPException(409, "Document storage location is invalid")
    return path


def _store(corpus_id: int):
    return VectorStoreFactory.create(store_type=settings.VECTOR_STORE_TYPE, collection_name=f"kb_{corpus_id}",
                                    embedding_function=EmbeddingsFactory.create())


async def upload(db: Session, actor: User, file: UploadFile) -> ProcessingTask:
    corpus = await run_in_threadpool(get_corpus, db, actor, manage=True)
    name = _filename(file.filename or "")
    content = await file.read(MAX_FILE_BYTES + 1)
    # Added by ChatGPT: synchronous SQL/ZIP/MinIO work must not block the API event loop.
    return await run_in_threadpool(_stage_upload, db, actor, corpus, name, content)


def _stage_upload(db: Session, actor: User, corpus: KnowledgeBase, name: str, content: bytes) -> ProcessingTask:
    if not content or len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "A non-empty document up to 20 MiB is required")
    ext = PurePosixPath(name).suffix.lower()
    if ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(400, "Invalid PDF document")
    if ext == ".docx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                if ("word/document.xml" not in archive.namelist() or len(archive.infolist()) > 5000
                        or sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024):
                    raise BadZipFile()
        except BadZipFile:
            raise HTTPException(400, "Invalid or oversized DOCX document") from None
    # Serialize names with rename/upload. No lock is held across background ingestion.
    _lock_corpus(db, actor)
    if (db.query(Document.id).filter(Document.knowledge_base_id == corpus.id,
            or_(Document.file_name == name, Document.file_path == f"kb_{corpus.id}/{name}")).with_for_update().first()
            or db.query(DocumentUpload.id).filter_by(knowledge_base_id=corpus.id, file_name=name).with_for_update().first()):
        raise HTTPException(409, "This filename is already in use; edit, retry or delete the existing upload")
    path = f"kb_{corpus.id}/temp/{uuid4().hex}{ext}"
    client = get_minio_client()
    try:
        client.put_object(settings.MINIO_BUCKET_NAME, path, BytesIO(content), len(content), content_type=CONTENT_TYPES[ext])
        staged = DocumentUpload(knowledge_base_id=corpus.id, file_name=name, temp_path=path,
                                file_hash=hashlib.sha256(content).hexdigest(), file_size=len(content),
                                content_type=CONTENT_TYPES[ext], created_at=datetime.utcnow())
        db.add(staged)
        db.flush()
        task = ProcessingTask(knowledge_base_id=corpus.id, document_upload_id=staged.id, status="pending")
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    except Exception as error:
        db.rollback()
        logger.warning("Corpus upload failed (%s)", type(error).__name__)
        # Only the newly allocated random object can be removed by this failed transaction.
        try:
            client.remove_object(settings.MINIO_BUCKET_NAME, path)
        except Exception:
            pass
        raise HTTPException(503, "Upload unavailable; please try again") from None


def process_upload(task_id: int, actor_id: int):
    with SessionLocal() as db:
        claimed = False
        try:
            corpus = _lock_corpus(db, db.get(User, actor_id))
            task = db.query(ProcessingTask).filter_by(id=task_id, knowledge_base_id=corpus.id).with_for_update().first()
            if task is None or task.status != "pending":
                return
            staged = task.document_upload
            if staged is None or task.knowledge_base_id != corpus.id or staged.knowledge_base_id != corpus.id:
                raise HTTPException(404, "Upload not found")
            _object_path(corpus.id, staged.temp_path)
            _filename(staged.file_name)
            task.status = staged.status = "processing"
            db.commit()
            claimed = True
            process_document_background(staged.temp_path, staged.file_name, corpus.id, task.id, db,
                                        retain_source=True)
            db.refresh(task)
            if task.status != "completed":
                raise RuntimeError("Ingestion failed")
            # Serialize final draft initialization with an admin publishing/deleting a completed task.
            document = db.query(Document).filter_by(id=task.document_id, knowledge_base_id=corpus.id).populate_existing().with_for_update().first()
            if document is None or not document.chunks:
                raise RuntimeError("No indexed content")
            metadata = db.query(AcademicDocumentMetadata).filter_by(document_id=document.id).with_for_update().first()
            if metadata is None:
                # Only lifecycle state is wired here; academic editing belongs to Phase 5.
                document.academic_metadata = AcademicDocumentMetadata(title=document.file_name, publication_status="draft")
            db.commit()
            try:
                get_minio_client().remove_object(settings.MINIO_BUCKET_NAME, staged.temp_path)
            except Exception as error:
                # Finished documents need only the permanent object; later deletion also retries this cleanup.
                logger.warning("Completed corpus source cleanup failed (%s)", type(error).__name__)
        except Exception:
            db.rollback()
            task = db.get(ProcessingTask, task_id)
            if (task is not None and (claimed or task.status == "pending") and task.knowledge_base is not None
                    and task.knowledge_base.scope == "public" and task.knowledge_base.is_system_managed
                    and task.knowledge_base.user.username == SYSTEM_USERNAME
                    and task.knowledge_base.user.email == SYSTEM_EMAIL and task.knowledge_base.user.is_system):
                task.status, task.error_message = "failed", "Processing failed; an administrator may retry the retained source."
                if task.document_upload:
                    task.document_upload.status = "failed"
                db.commit()


def set_publication(db: Session, actor: User, document_id: int, published: bool):
    _lock_corpus(db, actor)
    document = get_document(db, actor, document_id, manage=True)
    metadata = document.academic_metadata
    if metadata and metadata.publication_status == "archived":
        raise HTTPException(409, "Archived documents cannot be republished; deletion may be retried")
    tasks = db.query(ProcessingTask).filter_by(document_id=document.id).populate_existing().with_for_update().all()
    if published and (not tasks or any(t.status != "completed" for t in tasks) or not document.chunks):
        raise HTTPException(409, "Document must finish processing before publication")
    if metadata is None:
        metadata = document.academic_metadata = AcademicDocumentMetadata(title=document.file_name)
    metadata.publication_status = "published" if published else "draft"
    metadata.published_at = datetime.utcnow() if published else None
    db.commit()
    return document


def rename_document(db: Session, actor: User, document_id: int, name: str):
    corpus = _lock_corpus(db, actor)
    document = get_document(db, actor, document_id, manage=True)
    name = _filename(name)
    if (PurePosixPath(name).suffix.lower() != PurePosixPath(document.file_name).suffix.lower()
            or (document.academic_metadata and document.academic_metadata.publication_status == "archived")
            or any(t.status in {"pending", "processing"} for t in document.processing_tasks)):
        raise HTTPException(409, "Document cannot be renamed in this state or to another file type")
    if name != document.file_name and (db.query(Document.id).filter(Document.knowledge_base_id == corpus.id,
            Document.id != document.id, Document.file_name == name).with_for_update().first()
            or db.query(DocumentUpload.id).filter_by(knowledge_base_id=corpus.id, file_name=name).with_for_update().first()):
        raise HTTPException(409, "Filename already in use")
    document.file_name = name
    # Storage paths/chunk IDs remain immutable; public results use this SQL display name.
    db.commit()
    return document


def delete_document(db: Session, actor: User, document_id: int, *, retain_upload: bool = False):
    _lock_corpus(db, actor)
    document = get_document(db, actor, document_id, manage=True)
    tasks = db.query(ProcessingTask).filter_by(document_id=document.id).populate_existing().with_for_update().all()
    if any(task.status in {"pending", "processing"} for task in tasks):
        raise HTTPException(409, "Document is still processing")
    if document.academic_metadata is None:
        document.academic_metadata = AcademicDocumentMetadata(title=document.file_name)
    document.academic_metadata.publication_status = "archived"
    document.academic_metadata.published_at = None
    db.commit()
    # Hide first, then clean external state. A failed cleanup is safe to retry, never republish.
    _lock_corpus(db, actor)
    document = get_document(db, actor, document_id, manage=True)
    tasks = db.query(ProcessingTask).filter_by(document_id=document.id).populate_existing().with_for_update().all()
    if any(task.status in {"pending", "processing"} for task in tasks):
        raise HTTPException(409, "Document is still processing")
    paths = {_object_path(document.knowledge_base_id, document.file_path)}
    uploads = {task.document_upload.id: task.document_upload for task in tasks if task.document_upload}
    if not retain_upload:
        paths.update(_object_path(document.knowledge_base_id, staged.temp_path) for staged in uploads.values())
    chunk_ids = [chunk.id for chunk in document.chunks]
    try:
        if chunk_ids:
            store = _store(document.knowledge_base_id)
            for offset in range(0, len(chunk_ids), 1000):
                store.delete(chunk_ids[offset:offset + 1000])
        client = get_minio_client()
        for path in paths:
            client.remove_object(settings.MINIO_BUCKET_NAME, path)
        for task in tasks:
            if retain_upload:
                task.document_id = None
            else:
                db.delete(task)
        if not retain_upload:
            for staged in uploads.values():
                db.delete(staged)
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(503, "Document hidden; cleanup failed. Retry deletion before reusing this filename.") from None


def retry_upload(db: Session, actor: User, task_id: int) -> ProcessingTask:
    corpus = _lock_corpus(db, actor)
    task = db.query(ProcessingTask).filter_by(id=task_id, knowledge_base_id=corpus.id).with_for_update().first()
    if task is None:
        raise HTTPException(404, "Task not found")
    if task.status != "failed" or task.document_upload is None:
        raise HTTPException(409, "Only a failed retained upload can be retried")
    if task.document_id:
        try:
            delete_document(db, actor, task.document_id, retain_upload=True)
        except HTTPException as error:
            if error.status_code == 404:
                db.rollback()
                raise HTTPException(409, "Upload changed concurrently; refresh its task status") from None
            raise
        task = db.query(ProcessingTask).filter_by(id=task_id).populate_existing().with_for_update().one()
        if task.status != "failed":
            raise HTTPException(409, "Retry already in progress")
    task.status = task.document_upload.status = "pending"
    task.error_message = task.document_upload.error_message = None
    db.commit()
    return task


def delete_upload(db: Session, actor: User, task_id: int):
    corpus = _lock_corpus(db, actor)
    task = db.query(ProcessingTask).filter_by(id=task_id, knowledge_base_id=corpus.id).with_for_update().first()
    if task is None:
        raise HTTPException(404, "Task not found")
    if task.status != "failed":
        raise HTTPException(409, "Only failed uploads can be removed through this endpoint")
    if task.document_id:
        return delete_document(db, actor, task.document_id)
    staged = task.document_upload
    if staged is not None:
        path = _object_path(corpus.id, staged.temp_path)
        output = _object_path(corpus.id, f"kb_{corpus.id}/{_filename(staged.file_name)}")
        if db.query(Document.id).filter_by(knowledge_base_id=corpus.id, file_path=output).first():
            raise HTTPException(409, "A document still references this upload; remove that document first")
        try:
            client = get_minio_client()
            for location in {path, output}:
                client.remove_object(settings.MINIO_BUCKET_NAME, location)
        except Exception:
            raise HTTPException(503, "Cleanup failed; retry deletion") from None
        db.delete(staged)
    db.delete(task)
    db.commit()


def query_corpus(db: Session, actor: User, query: str, top_k: int):
    from app.services.retrieval_scope import search_scope
    return search_scope(db, actor, "public", query, top_k)
