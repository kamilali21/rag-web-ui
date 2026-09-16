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
    try:
        # Added by ChatGPT: API keys obey the same private ownership policy as JWTs.
        require_private_knowledge_base(db, current_user, knowledge_base_id)
        
        embeddings = EmbeddingsFactory.create()
        
        vector_store = VectorStoreFactory.create(
            store_type=settings.VECTOR_STORE_TYPE,
            collection_name=f"kb_{knowledge_base_id}",
            embedding_function=embeddings,
        )
        
        results = vector_store.similarity_search_with_score(query, k=top_k)
        
        response = []
        for doc, score in results:
            response.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
            
        return {"results": response}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Retrieval unavailable")
