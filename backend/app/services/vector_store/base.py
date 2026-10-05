from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

class BaseVectorStore(ABC):
    """Abstract base class for vector store implementations"""

    def search_permitted(self, query: str, document_ids: List[int], kb_id: int, k: int = 4):
        """Search only these SQL-authorized documents; smaller scores rank first.

        Unsupported adapters must fail closed, never fall back to an unfiltered query.
        """
        raise NotImplementedError("This vector backend does not support authorized search")
    
    @abstractmethod
    def __init__(self, collection_name: str, embedding_function: Embeddings, **kwargs):
        """Initialize the vector store"""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store"""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete documents from the vector store"""
        pass
    
    @abstractmethod
    def as_retriever(self, **kwargs: Any):
        """Return a retriever interface for the vector store"""
        pass
    
    @abstractmethod
    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """Search for similar documents with score"""
        pass

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete the entire collection"""
        pass
