import hashlib
from typing import List, Any, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import selectinload


from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.models.knowledge import KnowledgeBase, Document, ProcessingTask, DocumentUpload
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    DocumentResponse,
    PreviewRequest,
    PROCESSING_FAILURE,
)
from app.services.document_processor import process_document_background, preview_document, PreviewResult
from app.core.config import settings
from app.core.minio import get_minio_client
from minio.error import MinioException
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.authorization import (
    private_kb_filter, require_private_document, require_private_knowledge_base,
)
from app.services import private_library

router = APIRouter()

logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # Match the existing reverse-proxy request limit.

class TestRetrievalRequest(BaseModel):
    query: str
    kb_id: int
    top_k: int

@router.post("", response_model=KnowledgeBaseResponse)
def create_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_in: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create new knowledge base.
    """
    kb = KnowledgeBase(
        name=kb_in.name,
        description=kb_in.description,
        user_id=current_user.id
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    logger.info(f"Knowledge base created: {kb.name} for user {current_user.id}")
    return kb

@router.get("", response_model=List[KnowledgeBaseResponse])
def get_knowledge_bases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    summary: bool = False,
) -> Any:
    """
    Retrieve knowledge bases.
    """
    knowledge_bases = (
        db.query(KnowledgeBase)
        .filter(private_kb_filter(current_user))
        .order_by(KnowledgeBase.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    if summary:
        return [dict(id=kb.id, name=kb.name, description=kb.description, user_id=kb.user_id,
                     created_at=kb.created_at, updated_at=kb.updated_at, documents=[]) for kb in knowledge_bases]
    return knowledge_bases


@router.get("/catalog")
def private_catalog(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
    kb_id: int | None = None, search: str = Query("", max_length=255),
    category: Literal["Papers", "Theses", "Reports"] | None = None,
    status: Literal["pending", "processing", "completed", "failed", "unknown"] | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
):
    return private_library.catalog(db, current_user, kb_id=kb_id, search=search,
        category=category, status=status, skip=skip, limit=limit)


@router.delete("/{kb_id}/documents/{doc_id}")
def delete_private_document(kb_id: int, doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    private_library.delete_item(db, current_user, kb_id, document_id=doc_id)
    return {"message": "Document deleted"}


@router.get("/{kb_id}/documents/{doc_id}/content")
def private_content(kb_id: int, doc_id: int, inline: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = require_private_document(db, current_user, kb_id, doc_id)
    path = private_library.object_path(kb_id, doc.file_path)
    try:
        response = get_minio_client().get_object(settings.MINIO_BUCKET_NAME, path)
    except Exception:
        raise HTTPException(503, "Document content unavailable") from None
    def chunks():
        try:
            yield from response.stream(64 * 1024)
        finally:
            response.close()
            response.release_conn()
    safe_inline = inline and doc.content_type in {"application/pdf", "text/plain", "text/markdown"}
    media_type = "text/plain" if safe_inline and doc.content_type == "text/markdown" else doc.content_type
    return StreamingResponse(chunks(), media_type=media_type, headers={
        "Content-Disposition": f"{'inline' if safe_inline else 'attachment'}; filename*=UTF-8''{quote(doc.file_name, safe='')}",
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})


@router.delete("/{kb_id}/uploads/{upload_id}")
def delete_private_upload(kb_id: int, upload_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    private_library.delete_item(db, current_user, kb_id, upload_id=upload_id)
    return {"message": "Upload deleted"}

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get knowledge base by ID.
    """
    from sqlalchemy.orm import joinedload
    
    kb = (
        db.query(KnowledgeBase)
        .options(
            joinedload(KnowledgeBase.documents)
            .joinedload(Document.processing_tasks)
        )
        .filter(
            KnowledgeBase.id == kb_id,
            private_kb_filter(current_user)
        )
        .first()
    )

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    return kb

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    kb_in: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update knowledge base.
    """
    kb = require_private_knowledge_base(db, current_user, kb_id)

    for field, value in kb_in.dict(exclude_unset=True).items():
        setattr(kb, field, value)

    db.add(kb)
    db.commit()
    db.refresh(kb)
    logger.info(f"Knowledge base updated: {kb.name} for user {current_user.id}")
    return kb

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete knowledge base and all associated resources.
    """
    logger = logging.getLogger(__name__)
    
    kb = private_library.lock_collection(db, current_user, kb_id)
    if db.query(ProcessingTask.id).filter(ProcessingTask.knowledge_base_id == kb_id,
            ProcessingTask.status.in_(["pending", "processing"])).first():
        raise HTTPException(409, "Wait for processing to finish before deleting")

    try:
        # Initialize services
        minio_client = get_minio_client()
        embeddings = EmbeddingsFactory.create()

        vector_store = VectorStoreFactory.create(
            store_type=settings.VECTOR_STORE_TYPE,
            collection_name=f"kb_{kb_id}",
            embedding_function=embeddings,
        )
        
        # Clean up external resources first
        cleanup_errors = []
        
        # 1. Clean up MinIO files
        try:
            # Delete all objects with prefix kb_{kb_id}/
            # Added by ChatGPT: include staged uploads nested under the collection prefix.
            objects = minio_client.list_objects(settings.MINIO_BUCKET_NAME, prefix=f"kb_{kb_id}/", recursive=True)
            for obj in objects:
                minio_client.remove_object(settings.MINIO_BUCKET_NAME, obj.object_name)
            logger.info(f"Cleaned up MinIO files for knowledge base {kb_id}")
        except MinioException as e:
            cleanup_errors.append(f"Failed to clean up MinIO files: {str(e)}")
            logger.error(f"MinIO cleanup error for kb {kb_id}: {str(e)}")
        
        # 2. Clean up vector store
        try:
            # Added by ChatGPT: use the existing backend-neutral vector store contract.
            vector_store.delete_collection()
            logger.info(f"Cleaned up vector store for knowledge base {kb_id}")
        except Exception as e:
            cleanup_errors.append(f"Failed to clean up vector store: {str(e)}")
            logger.error(f"Vector store cleanup error for kb {kb_id}: {str(e)}")
        
        if cleanup_errors:
            private_library.mark_cleanup_failed(db, current_user, kb_id)
            raise HTTPException(503, "Cleanup incomplete. Collection retained; retry deletion.")
        # Finally, delete database records in a single transaction
        db.query(ProcessingTask).filter_by(knowledge_base_id=kb_id).delete(synchronize_session=False)
        db.delete(kb)
        db.commit()
        
        return {"message": "Knowledge base and all associated resources deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        private_library.mark_cleanup_failed(db, current_user, kb_id)
        logger.error(f"Failed to delete knowledge base {kb_id}: {str(e)}")
        raise HTTPException(status_code=503, detail="Cleanup incomplete. Collection retained; retry deletion.") from None

# Batch upload documents
@router.post("/{kb_id}/documents/upload")
async def upload_kb_documents(
    kb_id: int,
    files: List[UploadFile],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload multiple documents to MinIO.
    """
    private_library.lock_collection(db, current_user, kb_id)
    
    results = []
    uploaded_bytes = 0
    for file in files:
        # A filename is an object-path component, never a path supplied by a client.
        if not file.filename or "/" in file.filename or "\\" in file.filename or len(file.filename) > 200:
            raise HTTPException(400, "Use a filename without path separators, up to 200 characters")
        private_library.lock_collection(db, current_user, kb_id)
        # 1. 计算文件 hash
        file_content = await file.read(MAX_UPLOAD_BYTES - uploaded_bytes + 1)
        uploaded_bytes += len(file_content)
        if uploaded_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Upload request exceeds the 100 MiB limit")
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 2. 检查是否存在完全相同的文件（名称和hash都相同）
        existing_document = db.query(Document).filter(
            Document.file_name == file.filename,
            Document.file_hash == file_hash,
            Document.knowledge_base_id == kb_id
        ).first()
        
        if existing_document:
            # 完全相同的文件，直接返回
            results.append({
                "document_id": existing_document.id,
                "file_name": existing_document.file_name,
                "status": "exists",
                "message": "文件已存在且已处理完成",
                "skip_processing": True
            })
            continue
        if (db.query(Document.id).filter_by(knowledge_base_id=kb_id, file_name=file.filename).first()
                or db.query(DocumentUpload.id).filter_by(knowledge_base_id=kb_id, file_name=file.filename).first()):
            raise HTTPException(409, "Filename already in use; remove its document or upload before uploading again")
        
        # 3. 上传到临时目录
        temp_path = f"kb_{kb_id}/temp/{file.filename}"
        await file.seek(0)
        try:
            minio_client = get_minio_client()
            file_size = len(file_content)  # 使用之前读取的文件内容长度
            minio_client.put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=temp_path,
                data=file.file,
                length=file_size,  # 指定文件大小
                content_type=file.content_type
            )
        except MinioException as e:
            logger.error(f"Failed to upload file to MinIO: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
        
        # 4. 创建上传记录
        upload = DocumentUpload(
            knowledge_base_id=kb_id,
            file_name=file.filename,
            file_hash=file_hash,
            file_size=len(file_content),
            content_type=file.content_type,
            temp_path=temp_path
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)
        
        results.append({
            "upload_id": upload.id,
            "file_name": file.filename,
            "temp_path": temp_path,
            "status": "pending",
            "skip_processing": False
        })
    
    return results

@router.post("/{kb_id}/documents/preview")
async def preview_kb_documents(
    kb_id: int,
    preview_request: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[int, PreviewResult]:
    """
    Preview multiple documents' chunks.
    """
    # Added by ChatGPT: authorize the collection before resolving document/upload IDs.
    require_private_knowledge_base(db, current_user, kb_id)
    results = {}
    for doc_id in preview_request.document_ids:
        document = db.query(Document).join(KnowledgeBase).filter(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id,
            private_kb_filter(current_user)
        ).first()
        
        if document:
            file_path = document.file_path
        else:
            upload = db.query(DocumentUpload).join(KnowledgeBase).filter(
                DocumentUpload.id == doc_id,
                DocumentUpload.knowledge_base_id == kb_id,
                private_kb_filter(current_user)
            ).first()
            
            if not upload:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
            
            file_path = upload.temp_path
        
        preview = await preview_document(
            file_path,
            chunk_size=preview_request.chunk_size,
            chunk_overlap=preview_request.chunk_overlap
        )
        results[doc_id] = preview
    
    return results

@router.post("/{kb_id}/documents/process")
async def process_kb_documents(
    kb_id: int,
    upload_results: List[dict],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process multiple documents asynchronously.
    """
    private_library.lock_collection(db, current_user, kb_id)

    task_info = []
    upload_ids = []
    
    for result in upload_results:
        if result.get("skip_processing"):
            continue
        upload_ids.append(result["upload_id"])
    
    if not upload_ids:
        return {"tasks": []}
    
    uploads = db.query(DocumentUpload).filter(
        DocumentUpload.id.in_(upload_ids),
        DocumentUpload.knowledge_base_id == kb_id
    ).all()
    uploads_dict = {upload.id: upload for upload in uploads}
    if len(uploads_dict) != len(set(upload_ids)):
        raise HTTPException(status_code=400, detail="One or more upload IDs are invalid")
    if len(upload_ids) != len(set(upload_ids)) or db.query(ProcessingTask.id).filter(ProcessingTask.document_upload_id.in_(upload_ids)).first():
        raise HTTPException(409, "Upload already submitted; refresh its processing status")
    
    all_tasks = []
    for upload_id in upload_ids:
        upload = uploads_dict.get(upload_id)
        if not upload:
            continue
            
        task = ProcessingTask(
            document_upload_id=upload_id,
            knowledge_base_id=kb_id,
            status="pending"
        )
        all_tasks.append(task)
    
    db.add_all(all_tasks)
    db.commit()
    
    for task in all_tasks:
        db.refresh(task)
    
    task_data = []
    for i, upload_id in enumerate(upload_ids):
        if i < len(all_tasks):
            task = all_tasks[i]
            upload = uploads_dict.get(upload_id)
            
            task_info.append({
                "upload_id": upload_id,
                "task_id": task.id
            })
            
            if upload:
                task_data.append({
                    "task_id": task.id,
                    "upload_id": upload_id,
                    "temp_path": upload.temp_path,
                    "file_name": upload.file_name
                })
    
    background_tasks.add_task(
        add_processing_tasks_to_queue,
        task_data,
        kb_id
    )
    
    return {"tasks": task_info}

def add_processing_tasks_to_queue(task_data, kb_id):
    """Process documents in FastAPI's background thread pool."""
    for data in task_data:
        process_document_background(
            data["temp_path"],
            data["file_name"],
            kb_id,
            data["task_id"],
            None
        )

    logger.info(
        f"Processed {len(task_data)} document processing tasks"
    )

@router.post("/cleanup")
async def cleanup_temp_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clean up expired temporary files.
    """
    expired_time = datetime.utcnow() - timedelta(hours=24)
    # Added by ChatGPT: cleanup is never a cross-user administration shortcut.
    expired_uploads = db.query(DocumentUpload).join(KnowledgeBase).filter(
        DocumentUpload.created_at < expired_time, private_kb_filter(current_user),
        ~DocumentUpload.processing_tasks.any()
    ).all()
    
    minio_client = get_minio_client()
    for upload in expired_uploads:
        try:
            minio_client.remove_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=upload.temp_path
            )
        except MinioException as e:
            logger.error(f"Failed to delete temp file {upload.temp_path}: {str(e)}")
        
        db.delete(upload)
    
    db.commit()
    
    return {"message": f"Cleaned up {len(expired_uploads)} expired uploads"}

@router.get("/{kb_id}/documents/tasks")
async def get_processing_tasks(
    kb_id: int,
    task_ids: str = Query(..., description="Comma-separated list of task IDs to check status for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get status of multiple processing tasks.
    """
    task_id_list = [int(id.strip()) for id in task_ids.split(",")]
    
    require_private_knowledge_base(db, current_user, kb_id)
        
    tasks = (
        db.query(ProcessingTask)
        .options(
            selectinload(ProcessingTask.document_upload)
        )
        .filter(
            ProcessingTask.id.in_(task_id_list),
            ProcessingTask.knowledge_base_id == kb_id
        )
        .all()
    )
    
    return {
        task.id: {
            "document_id": task.document_id,
            "status": task.status,
            "error_message": PROCESSING_FAILURE if task.error_message else None,
            "upload_id": task.document_upload_id,
            "file_name": task.document_upload.file_name if task.document_upload else None
        }
        for task in tasks
    }

@router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get document details by ID.
    """
    return require_private_document(db, current_user, kb_id, doc_id)

@router.post("/test-retrieval")
async def test_retrieval(
    request: TestRetrievalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Test retrieval quality for a given query against a knowledge base.
    """
    from app.services.retrieval_scope import search_scope
    return {"results": search_scope(db, current_user, "private", request.query, request.top_k,
                                    knowledge_base_ids=[request.kb_id])}
