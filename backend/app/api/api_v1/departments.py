"""Added by ChatGPT: normalized department reference data, not a document catalog."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.academic import DepartmentCreate, DepartmentPatch, DepartmentRead
from app.services import academic

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[DepartmentRead])
def departments(db: Database, actor: Actor, include_inactive: bool = False,
                after_id: int | None = Query(None, ge=1), limit: int = Query(100, ge=1, le=100)):
    return academic.list_departments(db, actor, include_inactive=include_inactive, after_id=after_id, limit=limit)


@router.get("/{department_id}", response_model=DepartmentRead)
def department(department_id: int, db: Database, actor: Actor):
    return academic.get_department(db, actor, department_id)


@router.post("", status_code=201, response_model=DepartmentRead)
def create(payload: DepartmentCreate, db: Database, actor: Actor):
    return academic.save_department(db, actor, payload)


@router.patch("/{department_id}", response_model=DepartmentRead)
def update(department_id: int, payload: DepartmentPatch, db: Database, actor: Actor):
    return academic.save_department(db, actor, payload, department_id)
