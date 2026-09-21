"""Added by ChatGPT: minimal public corpus API, without catalog/academic/analysis UI contracts."""
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Document, User
from app.models.knowledge import ProcessingTask
from app.services import public_corpus as corpus
from app.services.authorization import require_admin
from app.schemas.academic import MetadataPatch, MetadataRead
from app.services import academic

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


class RenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_name: str = Field(min_length=1, max_length=150)


def _summary(kb):
    return {"id": kb.id, "name": kb.name, "description": kb.description,
            "user_id": kb.user_id, "scope": kb.scope, "is_system_managed": kb.is_system_managed}


def _task(task):
    return {"id": task.id, "upload_id": task.document_upload_id, "document_id": task.document_id,
            "status": task.status, "error_message": "Processing failed; retry is available." if task.status == "failed" else None}


@router.get("")
def read_corpus(db: Database, actor: Actor):
    return _summary(corpus.get_corpus(db, actor))


@router.post("")
def ensure_corpus(db: Database, actor: Actor):
    require_admin(db, actor)
    return _summary(corpus.provision_corpus(db))


@router.get("/documents")
def documents(db: Database, actor: Actor, before_id: int | None = Query(None, ge=1),
              limit: int = Query(50, ge=1, le=100), include_unpublished: bool = False):
    kb = corpus.get_corpus(db, actor, manage=include_unpublished)
    query = corpus.document_query(db, kb.id, published=not include_unpublished).options(selectinload(Document.academic_metadata))
    if before_id is not None:
        query = query.filter(Document.id < before_id)
    return [corpus.document_summary(doc) for doc in query.order_by(Document.id.desc()).limit(limit).all()]


@router.get("/documents/{document_id}")
def document(document_id: int, db: Database, actor: Actor, include_unpublished: bool = False):
    return corpus.document_summary(corpus.get_document(db, actor, document_id, manage=include_unpublished))


@router.get("/documents/{document_id}/content")
def content(document_id: int, db: Database, actor: Actor, include_unpublished: bool = False):
    doc = corpus.get_document(db, actor, document_id, manage=include_unpublished)
    path = corpus._object_path(doc.knowledge_base_id, doc.file_path)
    try:
        response = corpus.get_minio_client().get_object(settings.MINIO_BUCKET_NAME, path)
    except Exception:
        raise HTTPException(503, "Document content unavailable") from None

    def chunks():
        try:
            yield from response.stream(64 * 1024)
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(chunks(), media_type=doc.content_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc.file_name, safe='')}",
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


# Added by ChatGPT: academic fields cannot set ownership, processing or publication state.
@router.get("/documents/{document_id}/metadata", response_model=MetadataRead)
def metadata(document_id: int, db: Database, actor: Actor, include_unpublished: bool = False):
    return academic.read_metadata(db, actor, document_id, include_unpublished=include_unpublished)


@router.patch("/documents/{document_id}/metadata", response_model=MetadataRead)
def edit_metadata(document_id: int, payload: MetadataPatch, db: Database, actor: Actor):
    return academic.update_metadata(db, actor, document_id, payload)


@router.post("/query")
def query(payload: QueryRequest, db: Database, actor: Actor):
    return {"results": corpus.query_corpus(db, actor, payload.query, payload.top_k)}


@router.post("/documents/upload", status_code=202)
async def upload_document(db: Database, actor: Actor, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task = await corpus.upload(db, actor, file)
    background_tasks.add_task(corpus.process_upload, task.id, actor.id)
    return _task(task)


@router.get("/tasks/{task_id}")
def task_status(task_id: int, db: Database, actor: Actor):
    kb = corpus.get_corpus(db, actor, manage=True)
    task = db.query(ProcessingTask).filter_by(id=task_id, knowledge_base_id=kb.id).first()
    if task is None:
        raise HTTPException(404, "Task not found")
    return _task(task)


@router.post("/tasks/{task_id}/retry", status_code=202)
def retry(task_id: int, db: Database, actor: Actor, background_tasks: BackgroundTasks):
    task = corpus.retry_upload(db, actor, task_id)
    background_tasks.add_task(corpus.process_upload, task.id, actor.id)
    return _task(task)


@router.delete("/tasks/{task_id}")
def delete_failed_upload(task_id: int, db: Database, actor: Actor):
    corpus.delete_upload(db, actor, task_id)
    return {"message": "Failed upload and stored resources deleted"}


@router.patch("/documents/{document_id}")
def rename(document_id: int, payload: RenameRequest, db: Database, actor: Actor):
    return corpus.document_summary(corpus.rename_document(db, actor, document_id, payload.file_name))


@router.post("/documents/{document_id}/publish")
def publish(document_id: int, db: Database, actor: Actor):
    return corpus.document_summary(corpus.set_publication(db, actor, document_id, True))


@router.post("/documents/{document_id}/unpublish")
def unpublish(document_id: int, db: Database, actor: Actor):
    return corpus.document_summary(corpus.set_publication(db, actor, document_id, False))


@router.delete("/documents/{document_id}")
def delete(document_id: int, db: Database, actor: Actor):
    corpus.delete_document(db, actor, document_id)
    return {"message": "Document and stored resources deleted"}
