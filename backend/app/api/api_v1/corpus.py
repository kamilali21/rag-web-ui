"""Added by ChatGPT: authorized corpus discovery, academic metadata and document lifecycle APIs."""
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
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
              limit: int = Query(50, ge=1, le=100), include_unpublished: bool = False,
              search: str = Query("", max_length=200), author: str = Query("", max_length=200),
              department_id: int | None = Query(None, ge=1), year_from: int | None = Query(None, ge=1000, le=9999),
              year_to: int | None = Query(None, ge=1000, le=9999),
              document_type: Literal["paper", "thesis", "report", "other"] | None = None, bookmarked: bool = False):
    # Added by ChatGPT: preserve the array/cursor contract while adding server-side academic filters.
    return corpus.list_documents(db, actor, before_id=before_id, limit=limit, include_unpublished=include_unpublished,
        search=search, author=author, department_id=department_id, year_from=year_from, year_to=year_to, document_type=document_type, bookmarked=bookmarked)


@router.get("/documents/{document_id}")
def document(document_id: int, db: Database, actor: Actor, include_unpublished: bool = False):
    return corpus.document_summary(corpus.get_document(db, actor, document_id, manage=include_unpublished))


@router.get("/documents/{document_id}/content")
def content(document_id: int, db: Database, actor: Actor, include_unpublished: bool = False, inline: bool = False):
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

    # Added by ChatGPT: opt-in PDF/plain-text viewing; other formats remain downloads, never active HTML.
    safe_inline = inline and doc.content_type in {"application/pdf", "text/plain", "text/markdown"}
    media_type = "text/plain" if safe_inline and doc.content_type == "text/markdown" else doc.content_type
    return StreamingResponse(chunks(), media_type=media_type, headers={
        "Content-Disposition": f"{'inline' if safe_inline else 'attachment'}; filename*=UTF-8''{quote(doc.file_name, safe='')}",
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox"})


# Added by ChatGPT: bookmarks always derive their owner from the authenticated session.
@router.post("/documents/{document_id}/bookmark", status_code=204)
def save_bookmark(document_id: int, db: Database, actor: Actor):
    corpus.set_bookmark(db, actor, document_id, True)
    return Response(status_code=204)


@router.delete("/documents/{document_id}/bookmark", status_code=204)
def remove_bookmark(document_id: int, db: Database, actor: Actor):
    corpus.set_bookmark(db, actor, document_id, False)
    return Response(status_code=204)


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


# Added by ChatGPT: only current corpus admins may enumerate processing and unpublished work.
@router.get("/tasks")
def tasks(db: Database, actor: Actor, before_id: int | None = Query(None, ge=1),
          limit: int = Query(50, ge=1, le=100), search: str = Query("", max_length=200),
          status: Literal["pending", "processing", "completed", "failed"] | None = None,
          publication_status: Literal["draft", "published", "archived"] | None = None):
    return corpus.list_uploads(db, actor, before_id=before_id, limit=limit, search=search,
                              status=status, publication_status=publication_status)


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


@router.post("/documents/{document_id}/archive")
def archive(document_id: int, db: Database, actor: Actor):
    return corpus.document_summary(corpus.archive_document(db, actor, document_id))
