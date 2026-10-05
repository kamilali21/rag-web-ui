from typing import List, Any
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Qdrant
from app.core.config import settings

from .base import BaseVectorStore

class QdrantStore(BaseVectorStore):
    """Qdrant vector store implementation"""
    
    def __init__(self, collection_name: str, embedding_function: Embeddings, **kwargs):
        """Initialize Qdrant vector store"""
        self._store = Qdrant(
            collection_name=collection_name,
            embeddings=embedding_function,
            url=settings.QDRANT_URL,
            prefer_grpc=settings.QDRANT_PREFER_GRPC
        )
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to Qdrant"""
        self._store.add_documents(documents)
    
    def delete(self, ids: List[str]) -> None:
        """Delete documents from Qdrant"""
        self._store.delete(ids)
    
    def as_retriever(self, **kwargs: Any):
        """Return a retriever interface"""
        return self._store.as_retriever(**kwargs)
    
    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """Search for similar documents in Qdrant"""
        return self._store.similarity_search(query, k=k, **kwargs)
    
    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """Search for similar documents in Qdrant with score"""
        return self._store.similarity_search_with_score(query, k=k, **kwargs)

    def search_permitted(self, query: str, document_ids: List[int], kb_id: int, k: int = 4):
        if not document_ids:
            return []
        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
        condition = Filter(must=[FieldCondition(key="metadata.kb_id", match=MatchValue(value=kb_id)),
                                FieldCondition(key="metadata.document_id", match=MatchAny(any=document_ids))])
        # This adapter uses Qdrant's default cosine similarity: higher is better.
        return [(doc, -float(score)) for doc, score in self.similarity_search_with_score(query, k=k, filter=condition)]

    def delete_collection(self) -> None:
        """Delete the entire collection"""
        self._store._client.delete_collection(self._store._collection_name)
