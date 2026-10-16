"""Researcher profile and tightly scoped publication-review endpoints."""
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.minio import get_minio_client
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.researcher import (
    PublicationMetadataInput, PublicationRequestCreate, ResearcherProfileWrite,
    ReviewReason, WithdrawalCreate,
)
from app.services import researcher_publications as workflow
from app.services.public_corpus import process_upload

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]


@router.get("/profile")
def read_profile(db: Database, actor: Actor):
    return workflow.get_profile(db, actor)


@router.put("/profile")
def write_profile(payload: ResearcherProfileWrite, db: Database, actor: Actor):
    return workflow.save_profile(db, actor, payload)


@router.get("/profile/photo")
def read_profile_photo(db: Database, actor: Actor):
    content, mime = workflow.profile_photo(db, actor)
    return Response(content, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.put("/profile/photo")
async def write_profile_photo(db: Database, actor: Actor, file: UploadFile = File(...)):
    content = await file.read(workflow.MAX_PROFILE_PHOTO_BYTES + 1)
    return workflow.save_profile_photo(db, actor, content)


@router.delete("/profile/photo", status_code=204)
def delete_profile_photo(db: Database, actor: Actor):
    workflow.remove_profile_photo(db, actor)
    return Response(status_code=204)


@router.get("/eligible-documents")
def publication_eligible_documents(db: Database, actor: Actor):
    return workflow.eligible_documents(db, actor)


@router.get("/requests")
def own_requests(db: Database, actor: Actor):
    return workflow.my_requests(db, actor)


@router.post("/requests", status_code=201)
def request_publication(payload: PublicationRequestCreate, db: Database, actor: Actor):
    row = workflow.create_request(db, actor, payload.source_document_id, payload.metadata, payload.public_card_consent)
    return workflow.request_dict(row)


@router.post("/requests/{request_id}/cancel", status_code=204)
def cancel_publication_request(request_id: int, db: Database, actor: Actor):
    workflow.cancel_request(db, actor, request_id)
    return Response(status_code=204)


@router.post("/requests/{request_id}/withdrawals", status_code=201)
def request_withdrawal(request_id: int, payload: WithdrawalCreate, db: Database, actor: Actor):
    row = workflow.create_withdrawal(db, actor, request_id, payload.reason)
    return {"id": row.id, "status": row.status, "publication_request_id": row.publication_request_id}


@router.get("/admin/count")
def pending_request_count(db: Database, actor: Actor):
    return workflow.pending_count(db, actor)


@router.get("/admin")
def review_queue(db: Database, actor: Actor, status: Literal["pending", "processing", "failed"] | None = None):
    return workflow.admin_requests(db, actor, status)


@router.get("/admin/{request_id}")
def review_request(request_id: int, db: Database, actor: Actor):
    return workflow.admin_request_detail(db, actor, request_id)


@router.get("/admin/{request_id}/profile-photo")
def review_profile_photo(request_id: int, db: Database, actor: Actor):
    content, mime = workflow.admin_profile_photo(db, actor, request_id)
    return Response(content, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/admin/{request_id}/source")
def review_source_document(request_id: int, db: Database, actor: Actor, inline: bool = False):
    document = workflow.admin_request_document(db, actor, request_id)
    path = workflow.private_library.object_path(document.knowledge_base_id, document.file_path)
    try:
        source = get_minio_client().get_object(settings.MINIO_BUCKET_NAME, path)
    except Exception:
        raise HTTPException(503, "Requested document content unavailable") from None

    def content():
        try:
            yield from source.stream(64 * 1024)
        finally:
            source.close()
            source.release_conn()

    safe_inline = inline and document.content_type in {"application/pdf", "text/plain", "text/markdown"}
    media_type = "text/plain" if safe_inline and document.content_type == "text/markdown" else document.content_type
    return StreamingResponse(content(), media_type=media_type, headers={
        "Content-Disposition": f"{'inline' if safe_inline else 'attachment'}; filename*=UTF-8''{quote(document.file_name, safe='')}",
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox"})


@router.patch("/admin/{request_id}/metadata")
def edit_request(request_id: int, payload: PublicationMetadataInput, db: Database, actor: Actor):
    row = workflow.edit_request_metadata(db, actor, request_id, payload)
    return workflow.request_dict(row)


@router.post("/admin/{request_id}/approve", status_code=202)
def approve_request(request_id: int, background_tasks: BackgroundTasks, db: Database, actor: Actor):
    task = workflow.approve_publication(db, actor, request_id)
    background_tasks.add_task(process_upload, task.id, actor.id)
    return {"task_id": task.id, "status": "processing"}


@router.post("/admin/{request_id}/deny", status_code=204)
def deny_request(request_id: int, payload: ReviewReason, db: Database, actor: Actor):
    workflow.deny_publication(db, actor, request_id, payload.reason)
    return Response(status_code=204)


@router.get("/admin/withdrawals/{withdrawal_id}/document")
def review_withdrawal_document(withdrawal_id: int, db: Database, actor: Actor):
    document = workflow.admin_withdrawal_document(db, actor, withdrawal_id)
    from app.services import public_corpus
    path = public_corpus._object_path(document.knowledge_base_id, document.file_path)
    try:
        source = get_minio_client().get_object(settings.MINIO_BUCKET_NAME, path)
    except Exception:
        raise HTTPException(503, "Requested public document content unavailable") from None
    def content():
        try:
            yield from source.stream(64 * 1024)
        finally:
            source.close()
            source.release_conn()

    return StreamingResponse(content(), media_type=document.content_type, headers={
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(document.file_name, safe='')}",
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})


@router.post("/admin/withdrawals/{withdrawal_id}/approve", status_code=204)
def approve_withdrawal(withdrawal_id: int, db: Database, actor: Actor):
    workflow.decide_withdrawal(db, actor, withdrawal_id, approve=True)
    return Response(status_code=204)


@router.post("/admin/withdrawals/{withdrawal_id}/deny", status_code=204)
def deny_withdrawal(withdrawal_id: int, payload: ReviewReason, db: Database, actor: Actor):
    workflow.decide_withdrawal(db, actor, withdrawal_id, approve=False, reason=payload.reason)
    return Response(status_code=204)


@router.get("/publications/{document_id}/researcher-card")
def researcher_card(document_id: int, db: Database, actor: Actor):
    from app.services.public_corpus import get_document
    get_document(db, actor, document_id)
    return workflow.public_researcher_card(db, document_id)


@router.get("/publications/{document_id}/researcher-photo")
def researcher_photo(document_id: int, db: Database, actor: Actor):
    from app.services.public_corpus import get_document
    get_document(db, actor, document_id)
    content, mime = workflow.public_researcher_photo(db, document_id)
    return Response(content, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
