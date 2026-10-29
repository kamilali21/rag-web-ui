"""Owner-scoped profiles and request-scoped publication review."""
import logging
import warnings
from datetime import datetime
from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.minio import get_minio_client
from app.models import AcademicDocumentMetadata, Document, KnowledgeBase, User
from app.models.knowledge import ProcessingTask
from app.models.research import Department
from app.models.researcher import PublicationRequest, ResearcherProfile, WithdrawalRequest
from app.schemas.academic import MetadataPatch
from app.schemas.researcher import PublicationMetadataInput, ResearcherProfileWrite
from app.services import private_library, public_corpus
from app.services.authorization import require_active_user

logger = logging.getLogger(__name__)
MAX_PROFILE_PHOTO_BYTES = 3 * 1024 * 1024
PROFILE_PHOTO_TYPES = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"), "WEBP": ("image/webp", "webp")}
MAX_PROFILE_PHOTO_PIXELS = 16_000_000
MAX_PUBLICATION_BYTES = public_corpus.MAX_FILE_BYTES
PUBLIC_METADATA_FIELDS = (
    "title", "authors_text", "abstract", "department_id", "document_type", "publication_year",
    "publication_date", "supervisor", "keywords", "doi", "language",
)


def _profile_dict(profile, department=None):
    if profile is None:
        return None
    return {"full_name": profile.full_name, "department_id": profile.department_id,
            "department_name": department.name if department else None, "degree": profile.degree,
            "research_area": profile.research_area, "ag_number": profile.ag_number,
            "class_name": profile.class_name, "section": profile.section,
            "photo_url": "/api/researcher/profile/photo" if profile.photo_path else None,
            "created_at": profile.created_at, "updated_at": profile.updated_at}


def _require_corpus_admin(db: Session, actor: User):
    return public_corpus.get_corpus(db, actor, manage=True)


def get_profile(db: Session, actor: User):
    require_active_user(actor)
    profile = db.query(ResearcherProfile).filter_by(user_id=actor.id).first()
    department = db.get(Department, profile.department_id) if profile else None
    return _profile_dict(profile, department)


def save_profile(db: Session, actor: User, payload: ResearcherProfileWrite):
    require_active_user(actor)
    db.query(User.id).filter_by(id=actor.id).with_for_update().one()
    department = db.query(Department).filter_by(id=payload.department_id).populate_existing().with_for_update().first()
    if department is None or not department.is_active:
        raise HTTPException(422, "Choose an active department")
    profile = db.query(ResearcherProfile).filter_by(user_id=actor.id).populate_existing().with_for_update().first()
    if profile is None:
        profile = ResearcherProfile(user_id=actor.id)
    for name, value in payload.model_dump().items():
        setattr(profile, name, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_dict(profile, department)


def _photo_type(content: bytes):
    from PIL import Image, UnidentifiedImageError

    if len(content) > MAX_PROFILE_PHOTO_BYTES:
        raise HTTPException(413, "Choose an image up to 3 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content), formats=list(PROFILE_PHOTO_TYPES)) as image:
                result = PROFILE_PHOTO_TYPES[image.format]
                if image.width * image.height > MAX_PROFILE_PHOTO_PIXELS or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Oversized or animated profile image")
                image.verify()
            # verify() alone does not decode JPEG pixels. Force a bounded full decode too.
            with Image.open(BytesIO(content), formats=list(PROFILE_PHOTO_TYPES)) as image:
                image.load()
            return result
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(415, "Use a valid still PNG, JPEG or WebP image up to 16 megapixels") from None


def save_profile_photo(db: Session, actor: User, content: bytes):
    require_active_user(actor)
    mime, extension = _photo_type(content)
    db.query(User.id).filter_by(id=actor.id).with_for_update().one()
    profile = db.query(ResearcherProfile).filter_by(user_id=actor.id).populate_existing().with_for_update().first()
    if profile is None:
        raise HTTPException(409, "Save your researcher profile before adding a photo")
    path = f"researcher_profiles/{actor.id}/{uuid4().hex}.{extension}"
    client = get_minio_client()
    try:
        client.put_object(settings.MINIO_BUCKET_NAME, path, BytesIO(content), len(content), content_type=mime)
        old_path = profile.photo_path
        profile.photo_path, profile.photo_content_type = path, mime
        db.commit()
    except Exception:
        db.rollback()
        try:
            client.remove_object(settings.MINIO_BUCKET_NAME, path)
        except Exception:
            pass
        raise HTTPException(503, "Profile photo could not be saved") from None
    if old_path:
        try:
            client.remove_object(settings.MINIO_BUCKET_NAME, old_path)
        except Exception as error:
            logger.warning("Old profile photo cleanup failed (%s)", type(error).__name__)
    return {"photo_url": "/api/researcher/profile/photo"}


def remove_profile_photo(db: Session, actor: User):
    profile = db.query(ResearcherProfile).filter_by(user_id=actor.id).populate_existing().with_for_update().first()
    if profile is None or not profile.photo_path:
        return
    path = profile.photo_path
    try:
        get_minio_client().remove_object(settings.MINIO_BUCKET_NAME, path)
    except Exception:
        raise HTTPException(503, "Profile photo could not be removed; the profile is unchanged") from None
    profile.photo_path = profile.photo_content_type = None
    db.commit()


def _stream_photo(path: str, content_type: str):
    response = None
    try:
        response = get_minio_client().get_object(settings.MINIO_BUCKET_NAME, path)
        parts = []
        size = 0
        for part in response.stream(64 * 1024):
            size += len(part)
            if size > MAX_PROFILE_PHOTO_BYTES:
                raise HTTPException(404, "Profile photo unavailable")
            parts.append(part)
        content = b"".join(parts)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, "Profile photo unavailable") from None
    finally:
        if response is not None:
            response.close()
            response.release_conn()
    if not content or len(content) > MAX_PROFILE_PHOTO_BYTES:
        raise HTTPException(404, "Profile photo unavailable")
    return content, content_type


def profile_photo(db: Session, actor: User):
    require_active_user(actor)
    profile = db.query(ResearcherProfile).filter_by(user_id=actor.id).first()
    if profile is None or not profile.photo_path:
        raise HTTPException(404, "Profile photo not found")
    return _stream_photo(profile.photo_path, profile.photo_content_type)


def eligible_documents(db: Session, actor: User):
    require_active_user(actor)
    rows = db.query(Document, KnowledgeBase).join(KnowledgeBase).filter(
        KnowledgeBase.user_id == actor.id, KnowledgeBase.scope == "private",
        KnowledgeBase.is_system_managed.is_(False), Document.file_size <= MAX_PUBLICATION_BYTES,
    ).order_by(Document.created_at.desc()).all()
    eligible = []
    for document, kb in rows:
        try:
            public_corpus._filename(document.file_name)
        except HTTPException:
            continue
        tasks = db.query(ProcessingTask).filter_by(document_id=document.id).order_by(ProcessingTask.id.desc()).all()
        if tasks and all(task.status == "completed" for task in tasks) and document.chunks:
            eligible.append({"id": document.id, "knowledge_base_id": kb.id, "file_name": document.file_name,
                             "file_size": document.file_size, "content_type": document.content_type})
    return eligible


def _validate_request_metadata(db: Session, metadata: PublicationMetadataInput | MetadataPatch):
    values = metadata.model_dump(exclude_unset=True, mode="json")
    department_id = values.get("department_id")
    if department_id is not None:
        department = db.query(Department).filter_by(id=department_id).populate_existing().with_for_update().first()
        if department is None or not department.is_active:
            raise HTTPException(422, "Choose an active department")
    year, published_date = values.get("publication_year"), values.get("publication_date")
    if year is not None and published_date is not None and year != int(published_date[:4]):
        raise HTTPException(422, "Publication year must match the publication date")
    return values


def create_request(db: Session, actor: User, source_document_id: int, metadata: PublicationMetadataInput,
                   public_card_consent: bool):
    require_active_user(actor)
    document = db.query(Document).join(KnowledgeBase).filter(
        Document.id == source_document_id, KnowledgeBase.user_id == actor.id,
        KnowledgeBase.scope == "private", KnowledgeBase.is_system_managed.is_(False),
    ).populate_existing().with_for_update().first()
    if document is None:
        raise HTTPException(404, "Private document not found")
    if document.file_size > MAX_PUBLICATION_BYTES:
        raise HTTPException(413, "This file exceeds the public corpus size limit")
    public_corpus._filename(document.file_name)
    if db.query(ResearcherProfile.user_id).filter_by(user_id=actor.id).first() is None:
        raise HTTPException(409, "Complete your researcher profile before requesting publication")
    tasks = db.query(ProcessingTask).filter_by(document_id=document.id).populate_existing().with_for_update().all()
    if not tasks or any(task.status != "completed" for task in tasks) or not document.chunks:
        raise HTTPException(409, "Only fully processed and indexed documents can be submitted")
    active = db.query(PublicationRequest.id).filter(
        PublicationRequest.owner_id == actor.id, PublicationRequest.source_document_id == source_document_id,
        PublicationRequest.status.in_(["pending", "processing", "published"]),
    ).first()
    if active:
        raise HTTPException(409, "This document already has an active or published request")
    snapshot = _validate_request_metadata(db, metadata)
    row = PublicationRequest(owner_id=actor.id, source_document_id=source_document_id,
                             metadata_snapshot=snapshot, public_card_consent=public_card_consent)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def request_dict(row: PublicationRequest, document=None):
    return {"id": row.id, "status": row.status, "metadata": row.metadata_snapshot,
            "public_card_consent": row.public_card_consent, "source_document_id": row.source_document_id,
            "source_file_name": document.file_name if document else None,
            "public_document_id": row.public_document_id, "denial_reason": row.denial_reason,
            "created_at": row.created_at, "updated_at": row.updated_at}


def my_requests(db: Session, actor: User):
    require_active_user(actor)
    publications = db.query(PublicationRequest, Document).outerjoin(
        Document, Document.id == PublicationRequest.source_document_id).filter(
        PublicationRequest.owner_id == actor.id).order_by(PublicationRequest.created_at.desc(), PublicationRequest.id.desc()).all()
    result = []
    for row, source in publications:
        public_doc = db.get(Document, row.public_document_id) if row.public_document_id else None
        result.append({**request_dict(row, source), "publication_status":
                       public_doc.academic_metadata.publication_status if public_doc and public_doc.academic_metadata else None})
    withdrawals = db.query(WithdrawalRequest, PublicationRequest, Document).join(
        PublicationRequest, PublicationRequest.id == WithdrawalRequest.publication_request_id).outerjoin(
        Document, Document.id == PublicationRequest.public_document_id).filter(
        WithdrawalRequest.owner_id == actor.id).order_by(WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc()).all()
    return {"publications": result, "withdrawals": [
        {"id": row.id, "publication_request_id": publication.id, "title": publication.metadata_snapshot.get("title"),
         "public_document_id": publication.public_document_id, "file_name": document.file_name if document else None,
         "status": row.status, "reason": row.reason, "decision_reason": row.decision_reason,
         "created_at": row.created_at} for row, publication, document in withdrawals]}


def cancel_request(db: Session, actor: User, request_id: int):
    row = db.query(PublicationRequest).filter_by(id=request_id, owner_id=actor.id).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Publication request not found")
    if row.status != "pending":
        raise HTTPException(409, "Only requests awaiting review can be cancelled")
    row.status = "cancelled"
    db.commit()


def create_withdrawal(db: Session, actor: User, request_id: int, reason: str | None):
    publication = db.query(PublicationRequest).filter_by(id=request_id, owner_id=actor.id).populate_existing().with_for_update().first()
    if publication is None or publication.status != "published" or publication.public_document_id is None:
        raise HTTPException(404, "Published paper not found")
    public_doc = db.query(Document).filter_by(id=publication.public_document_id).first()
    if public_doc is None or public_doc.academic_metadata is None or public_doc.academic_metadata.publication_status != "published":
        raise HTTPException(409, "This paper is no longer published")
    if db.query(WithdrawalRequest.id).filter_by(publication_request_id=publication.id, status="pending").first():
        raise HTTPException(409, "A withdrawal request is already awaiting review")
    row = WithdrawalRequest(publication_request_id=publication.id, owner_id=actor.id, reason=reason)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def pending_count(db: Session, actor: User):
    _require_corpus_admin(db, actor)
    publications = db.query(PublicationRequest.id).filter_by(status="pending").count()
    withdrawals = db.query(WithdrawalRequest.id).filter_by(status="pending").count()
    return {"count": publications + withdrawals}


def admin_requests(db: Session, actor: User, status: str | None = None):
    _require_corpus_admin(db, actor)
    query = db.query(PublicationRequest).filter(PublicationRequest.status.in_(
        [status] if status else ["pending", "processing", "failed"])).order_by(
        PublicationRequest.created_at.asc(), PublicationRequest.id.asc()).limit(100)
    rows = query.all()
    result = []
    for row in rows:
        profile = db.query(ResearcherProfile).filter_by(user_id=row.owner_id).first()
        department = db.get(Department, profile.department_id) if profile else None
        source = db.get(Document, row.source_document_id) if row.source_document_id else None
        result.append({**request_dict(row, source), "requester_id": row.owner_id,
                       "profile": _profile_dict(profile, department), "request_type": "publication"})
    withdrawal_query = db.query(WithdrawalRequest).filter(WithdrawalRequest.status == (status or "pending")).order_by(
        WithdrawalRequest.created_at.asc(), WithdrawalRequest.id.asc()).limit(100)
    for row in withdrawal_query.all():
        publication = db.get(PublicationRequest, row.publication_request_id)
        profile = db.query(ResearcherProfile).filter_by(user_id=row.owner_id).first()
        department = db.get(Department, profile.department_id) if profile else None
        public_doc = db.get(Document, publication.public_document_id) if publication and publication.public_document_id else None
        result.append({"id": row.id, "status": row.status, "request_type": "withdrawal",
                       "publication_request_id": publication.id if publication else None,
                       "public_document_id": publication.public_document_id if publication else None,
                       "source_file_name": public_doc.file_name if public_doc else None,
                       "title": publication.metadata_snapshot.get("title") if publication else None,
                       "reason": row.reason, "decision_reason": row.decision_reason,
                       "requester_id": row.owner_id, "profile": _profile_dict(profile, department),
                       "created_at": row.created_at})
    return sorted(result, key=lambda item: item["created_at"])[:100]


def admin_request_detail(db: Session, actor: User, request_id: int):
    _require_corpus_admin(db, actor)
    row = db.query(PublicationRequest).filter_by(id=request_id).first()
    if row is None:
        raise HTTPException(404, "Publication request not found")
    profile = db.query(ResearcherProfile).filter_by(user_id=row.owner_id).first()
    department = db.get(Department, profile.department_id) if profile else None
    document = db.get(Document, row.source_document_id) if row.source_document_id else None
    kb = db.get(KnowledgeBase, document.knowledge_base_id) if document else None
    if document and (kb is None or kb.scope != "private" or kb.user_id != row.owner_id or kb.is_system_managed):
        raise HTTPException(404, "Requested private document unavailable")
    return {**request_dict(row, document), "requester_id": row.owner_id,
            "profile": _profile_dict(profile, department),
            "admin_photo_url": f"/api/researcher/admin/{request_id}/profile-photo" if profile and profile.photo_path else None,
            "document": {"id": document.id, "file_name": document.file_name, "file_size": document.file_size,
                         "content_type": document.content_type} if document else None}


def admin_profile_photo(db: Session, actor: User, request_id: int):
    _require_corpus_admin(db, actor)
    row = db.query(PublicationRequest).filter_by(id=request_id).first()
    if row is None:
        raise HTTPException(404, "Publication request not found")
    profile = db.query(ResearcherProfile).filter_by(user_id=row.owner_id).first()
    if profile is None or not profile.photo_path:
        raise HTTPException(404, "Profile photo not found")
    return _stream_photo(profile.photo_path, profile.photo_content_type)


def admin_request_document(db: Session, actor: User, request_id: int):
    _require_corpus_admin(db, actor)
    row = db.query(PublicationRequest).filter_by(id=request_id).first()
    if row is None or row.source_document_id is None:
        raise HTTPException(404, "Requested document not found")
    document = db.query(Document).filter_by(id=row.source_document_id).first()
    kb = db.get(KnowledgeBase, document.knowledge_base_id) if document else None
    if document is None or kb is None or kb.scope != "private" or kb.user_id != row.owner_id or kb.is_system_managed:
        raise HTTPException(404, "Requested document not found")
    return document


def _source_bytes(document: Document):
    if document.file_size > MAX_PUBLICATION_BYTES:
        raise HTTPException(413, "The document exceeds the public corpus size limit")
    path = private_library.object_path(document.knowledge_base_id, document.file_path)
    response = None
    try:
        response = get_minio_client().get_object(settings.MINIO_BUCKET_NAME, path)
        parts = []
        size = 0
        for part in response.stream(64 * 1024):
            size += len(part)
            if size > MAX_PUBLICATION_BYTES:
                raise HTTPException(413, "The document exceeds the public corpus size limit")
            parts.append(part)
        content = b"".join(parts)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Requested document content is unavailable") from None
    finally:
        if response is not None:
            response.close()
            response.release_conn()
    if not content or len(content) > MAX_PUBLICATION_BYTES or len(content) != document.file_size:
        raise HTTPException(503, "Requested document content failed integrity checks")
    return content


def approve_publication(db: Session, actor: User, request_id: int):
    _require_corpus_admin(db, actor)
    row = db.query(PublicationRequest).filter_by(id=request_id).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Publication request not found")
    if row.status not in {"pending", "failed"}:
        raise HTTPException(409, "This request is not ready for approval")
    try:
        clean_metadata = PublicationMetadataInput.model_validate(row.metadata_snapshot)
    except Exception:
        raise HTTPException(409, "Review and correct the request metadata before approval") from None
    row.metadata_snapshot = _validate_request_metadata(db, clean_metadata)
    if row.status == "failed" and row.processing_task_id:
        task = public_corpus.retry_upload(db, actor, row.processing_task_id)
        row.status = "processing"
        row.reviewed_by, row.reviewed_at = actor.id, datetime.utcnow()
        db.commit()
        return task
    source = db.query(Document).filter_by(id=row.source_document_id).populate_existing().with_for_update().first()
    kb = db.get(KnowledgeBase, source.knowledge_base_id) if source else None
    if source is None or kb is None or kb.user_id != row.owner_id or kb.scope != "private" or kb.is_system_managed:
        row.status = "cancelled"
        row.source_document_id = None
        db.commit()
        raise HTTPException(409, "The submitted private document is no longer available")
    tasks = db.query(ProcessingTask).filter_by(document_id=source.id).populate_existing().with_for_update().all()
    if not tasks or any(task.status != "completed" for task in tasks) or not source.chunks:
        raise HTTPException(409, "The submitted document is no longer fully indexed")
    row.status = "processing"
    row.reviewed_by, row.reviewed_at, row.denial_reason = actor.id, datetime.utcnow(), None
    db.commit()
    try:
        content = _source_bytes(source)
        extension = source.file_name.rsplit(".", 1)[-1]
        name = f"publication-{row.id}.{extension}"
        corpus = public_corpus.get_corpus(db, actor, manage=True)
        task = public_corpus._stage_upload(db, actor, corpus, public_corpus._filename(name), content)
        row = db.query(PublicationRequest).filter_by(id=request_id).populate_existing().with_for_update().one()
        row.processing_task_id = task.id
        db.commit()
        return task
    except Exception:
        db.rollback()
        row = db.query(PublicationRequest).filter_by(id=request_id).with_for_update().first()
        if row and row.status == "processing" and row.processing_task_id is None:
            row.status = "failed"
            db.commit()
        raise


def deny_publication(db: Session, actor: User, request_id: int, reason: str):
    _require_corpus_admin(db, actor)
    row = db.query(PublicationRequest).filter_by(id=request_id).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Publication request not found")
    if row.status != "pending":
        raise HTTPException(409, "Only pending requests can be denied")
    row.status, row.denial_reason = "denied", reason
    row.reviewed_by, row.reviewed_at = actor.id, datetime.utcnow()
    db.commit()


def edit_request_metadata(db: Session, actor: User, request_id: int, payload: PublicationMetadataInput):
    _require_corpus_admin(db, actor)
    row = db.query(PublicationRequest).filter_by(id=request_id).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Publication request not found")
    if row.status not in {"pending", "failed"}:
        raise HTTPException(409, "Only pending or failed request metadata can be edited")
    row.metadata_snapshot = _validate_request_metadata(db, payload)
    db.commit()
    return row


def admin_withdrawal_document(db: Session, actor: User, withdrawal_id: int):
    _require_corpus_admin(db, actor)
    withdrawal = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).first()
    publication = db.get(PublicationRequest, withdrawal.publication_request_id) if withdrawal else None
    document = db.get(Document, publication.public_document_id) if publication and publication.public_document_id else None
    if document is None or document.knowledge_base_id != public_corpus.get_corpus(db, actor, manage=True).id:
        raise HTTPException(404, "Requested public document not found")
    return document


def decide_withdrawal(db: Session, actor: User, withdrawal_id: int, *, approve: bool, reason: str | None = None):
    _require_corpus_admin(db, actor)
    row = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Withdrawal request not found")
    if row.status != "pending":
        raise HTTPException(409, "Only pending withdrawal requests can be decided")
    if approve:
        publication = db.query(PublicationRequest).filter_by(id=row.publication_request_id).first()
        if publication is None or publication.public_document_id is None:
            raise HTTPException(409, "Published document is unavailable")
        public_corpus.archive_document(db, actor, publication.public_document_id)
        row = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).populate_existing().with_for_update().one()
        row.status, row.decision_reason = "approved", reason
    else:
        row.status, row.decision_reason = "denied", reason
    row.reviewed_by, row.reviewed_at = actor.id, datetime.utcnow()
    db.commit()
    return row


def public_researcher_cards(db: Session, document_ids: list[int]):
    if not document_ids:
        return {}
    rows = db.query(PublicationRequest.public_document_id, ResearcherProfile.full_name,
        Department.name, ResearcherProfile.degree, ResearcherProfile.research_area,
        ResearcherProfile.photo_path).join(
        ResearcherProfile, ResearcherProfile.user_id == PublicationRequest.owner_id).join(
        Document, Document.id == PublicationRequest.public_document_id).join(
        AcademicDocumentMetadata, AcademicDocumentMetadata.document_id == Document.id).outerjoin(
        Department, Department.id == ResearcherProfile.department_id).filter(
        PublicationRequest.public_document_id.in_(document_ids),
        PublicationRequest.status == "published", PublicationRequest.public_card_consent.is_(True),
        AcademicDocumentMetadata.publication_status == "published").all()
    return {document_id: {"full_name": full_name, "department_name": department_name,
            "degree": degree, "research_area": research_area,
            "photo_url": f"/api/researcher/publications/{document_id}/researcher-photo" if photo_path else None}
            for document_id, full_name, department_name, degree, research_area, photo_path in rows}


def public_researcher_card(db: Session, document_id: int):
    return public_researcher_cards(db, [document_id]).get(document_id)


def public_researcher_photo(db: Session, document_id: int):
    row = db.query(PublicationRequest, ResearcherProfile).join(
        ResearcherProfile, ResearcherProfile.user_id == PublicationRequest.owner_id).join(
        Document, Document.id == PublicationRequest.public_document_id).join(
        AcademicDocumentMetadata, AcademicDocumentMetadata.document_id == Document.id).filter(
        PublicationRequest.public_document_id == document_id, PublicationRequest.status == "published",
        PublicationRequest.public_card_consent.is_(True), AcademicDocumentMetadata.publication_status == "published").first()
    if row is None or not row[1].photo_path:
        raise HTTPException(404, "Researcher photo not available")
    return _stream_photo(row[1].photo_path, row[1].photo_content_type)


def complete_publication_task(db: Session, task: ProcessingTask, document: Document):
    row = db.query(PublicationRequest).filter_by(processing_task_id=task.id).populate_existing().with_for_update().first()
    if row is None:
        return False
    if row.status != "processing" or not document.chunks:
        raise RuntimeError("Publication request is not ready to complete")
    metadata = document.academic_metadata
    if metadata is None:
        metadata = AcademicDocumentMetadata(document_id=document.id, title=document.file_name)
    for field in PUBLIC_METADATA_FIELDS:
        if field in row.metadata_snapshot:
            value = row.metadata_snapshot[field]
            if field == "publication_date" and value:
                from datetime import date
                value = date.fromisoformat(value)
            setattr(metadata, field, value)
    metadata.publication_status = "published"
    metadata.published_at = datetime.utcnow()
    db.add(metadata)
    row.public_document_id = document.id
    row.status = "published"
    db.commit()
    return True


def fail_publication_task(db: Session, task_id: int):
    row = db.query(PublicationRequest).filter_by(processing_task_id=task_id, status="processing").with_for_update().first()
    if row is not None:
        row.status = "failed"
        db.commit()
