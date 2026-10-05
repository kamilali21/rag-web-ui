from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from langchain_chroma import Chroma
from app.services.vector_store import VectorStoreFactory

from app import models
from app.db.session import get_db
from app.core.security import get_api_key_user
from app.core.config import settings
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.authorization import require_private_knowledge_base

router = APIRouter()

@router.get("/{knowledge_base_id}/query")
def query_knowledge_base(
    *,
    db: Session = Depends(get_db),
    knowledge_base_id: int,
    query: str,
    top_k: int = 3,
    current_user: models.User = Depends(get_api_key_user),
) -> Any:
    """
    Query a specific knowledge base using API key authentication
    """
    from app.services.retrieval_scope import search_scope
    return {"results": search_scope(db, current_user, "private", query, top_k,
                                    knowledge_base_ids=[knowledge_base_id])}
