"""Added by ChatGPT: academic edits reuse corpus authorization and lifecycle locks."""
from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AcademicDocumentMetadata, User
from app.models.knowledge import ProcessingTask
from app.models.research import Department
from app.schemas.academic import DepartmentCreate, DepartmentPatch, MetadataPatch
from app.services import public_corpus as corpus
from app.services.authorization import require_active_user, require_admin


def list_departments(db: Session, actor: User, *, include_inactive=False, after_id=None, limit=100):
    require_active_user(actor)
    if include_inactive:
        require_admin(db, actor)
    query = db.query(Department)
    if not include_inactive:
        query = query.filter(Department.is_active.is_(True))
    if after_id is not None:
        query = query.filter(Department.id > after_id)
    return query.order_by(Department.id).limit(min(max(limit, 1), 100)).all()


def get_department(db: Session, actor: User, department_id: int):
    require_active_user(actor)
    row = db.get(Department, department_id)
    if row is None:
        raise HTTPException(404, "Department not found")
    return row


def save_department(db: Session, actor: User, payload: DepartmentCreate | DepartmentPatch, department_id=None):
    require_admin(db, actor)
    if department_id is None:
        row = Department()
    else:
        row = db.query(Department).filter_by(id=department_id).populate_existing().with_for_update().first()
        if row is None:
            raise HTTPException(404, "Department not found")
    values = payload.model_dump(exclude_unset=True)
    name, code = values.get("name", row.name), values.get("code", row.code)
    # MySQL unique constraints arbitrate concurrent creates; this also gives SQLite consistent casing checks.
    conflict = db.query(Department.id).filter(or_(func.lower(Department.name) == name.lower(), Department.code == code))
    if department_id is not None:
        conflict = conflict.filter(Department.id != department_id)
    if conflict.first():
        raise HTTPException(409, "Department name or code already exists")
    for key, value in values.items():
        setattr(row, key, value)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Department name or code already exists") from None
    db.refresh(row)
    return row


def read_metadata(db: Session, actor: User, document_id: int, *, include_unpublished=False):
    document = corpus.get_document(db, actor, document_id, manage=include_unpublished)
    if document.academic_metadata is None:
        raise HTTPException(404, "Academic metadata not available yet")
    return document.academic_metadata


def update_metadata(db: Session, actor: User, document_id: int, payload: MetadataPatch):
    corpus._lock_corpus(db, actor)
    document = corpus.get_document(db, actor, document_id, manage=True)
    metadata = document.academic_metadata
    tasks = db.query(ProcessingTask).filter_by(document_id=document_id).populate_existing().with_for_update().all()
    if ((metadata and metadata.publication_status == "archived") or not tasks
            or any(task.status != "completed" for task in tasks)):
        raise HTTPException(409, "Metadata editing requires a completed, non-archived document")
    if metadata is None:
        metadata = AcademicDocumentMetadata(document_id=document_id, title=document.file_name, publication_status="draft")
    values = payload.model_dump(exclude_unset=True)
    department_id = values.get("department_id")
    if department_id is not None:
        # Lock assignment against deactivation. Existing inactive references remain readable and removable.
        department = db.query(Department).filter_by(id=department_id).populate_existing().with_for_update().first()
        if department is None or not department.is_active:
            raise HTTPException(422, "Choose an active department")
    year = values.get("publication_year", metadata.publication_year)
    published_date = values.get("publication_date", metadata.publication_date)
    if year is not None and published_date is not None and year != published_date.year:
        raise HTTPException(422, "Publication year must match the publication date")
    for key, value in values.items():
        setattr(metadata, key, value)
    db.add(metadata)
    db.commit()
    db.refresh(metadata)
    return metadata
