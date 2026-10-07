"""Scope-aware evidence search; chat synthesis remains the existing chat workflow."""
from fastapi import APIRouter, Depends
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.retrieval_scope import SourceScope, search_documents, search_scope

router = APIRouter()


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: SourceScope = "private"
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/query")
def query_sources(payload: RetrievalRequest, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return {"results": search_scope(db, actor, payload.scope, payload.query, payload.top_k)}


class DocumentRetrievalRequest(RetrievalRequest):
    scope: SourceScope = "both"
    document_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(min_length=1, max_length=20)


@router.post("/documents/query")
def query_documents(payload: DocumentRetrievalRequest, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    """Retrieve only from the complete authorized selection; never broaden it."""
    return {"results": search_documents(db, actor, payload.document_ids, payload.query,
                                        payload.top_k, scope=payload.scope)}
