from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class FulltextSearchResult(BaseModel):
    """Result of a full-text search operation."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any] = {}
    artifact_id: str
    chunk_id: Optional[str] = None


class FulltextSearchResults(BaseModel):
    """Collection of full-text search results."""
    results: List[FulltextSearchResult] = []
    total: int = 0
    took: float = 0.0


class FulltextDB(ABC):
    """Abstract base class for full-text search databases.
    
    This class defines the standard interface that all full-text search database implementations
    must follow. It provides methods for storing, retrieving, and searching text content.
    """
    
    @abstractmethod
    def has_index(self, index_name: str) -> bool:
        """Check if an index exists.
        
        Args:
            index_name (str): Name of the index
            
        Returns:
            bool: True if index exists, False otherwise
        """
        pass
        
    @abstractmethod
    def delete_index(self, index_name: str):
        """Delete an index.
        
        Args:
            index_name (str): Name of the index to delete
        """
        pass
        
    @abstractmethod
    def search(
        self, 
        index_name: str, 
        query: str, 
        filter: Optional[Dict[str, Any]] = None, 
        limit: int = 10,
        offset: int = 0
    ) -> Optional[FulltextSearchResults]:
        """Search for text content based on query.
        
        Args:
            index_name (str): Name of the index
            query (str): Search query
            filter (Optional[Dict[str, Any]]): Filter conditions
            limit (int): Maximum number of results to return
            offset (int): Number of results to skip
            
        Returns:
            Optional[FulltextSearchResults]: Search results or None if index doesn't exist
        """
        pass
        
    @abstractmethod
    def query(
        self, 
        index_name: str, 
        filter: Dict[str, Any], 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Optional[FulltextSearchResults]:
        """Query items from the index based on filter.
        
        Args:
            index_name (str): Name of the index
            filter (Dict[str, Any]): Filter conditions
            limit (Optional[int]): Maximum number of results to return
            offset (int): Number of results to skip
            
        Returns:
            Optional[FulltextSearchResults]: Query results or None if index doesn't exist
        """
        pass
        
    @abstractmethod
    def get(self, index_name: str, limit: Optional[int] = None) -> Optional[FulltextSearchResults]:
        """Get all items in the index.
        
        Args:
            index_name (str): Name of the index
            limit (Optional[int]): Maximum number of results to return
            
        Returns:
            Optional[FulltextSearchResults]: All items in the index or None if index doesn't exist
        """
        pass
        
    @abstractmethod
    def insert(self, index_name: str, documents: List[Dict[str, Any]]):
        """Insert documents into the index.
        
        Args:
            index_name (str): Name of the index
            documents (List[Dict[str, Any]]): List of documents to insert
        """
        pass
        
    @abstractmethod
    def upsert(self, index_name: str, documents: List[Dict[str, Any]]):
        """Update or insert documents in the index.
        
        Args:
            index_name (str): Name of the index
            documents (List[Dict[str, Any]]): List of documents to upsert
        """
        pass
        
    @abstractmethod
    def delete(
        self,
        index_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ):
        """Delete documents from the index.
        
        Args:
            index_name (str): Name of the index
            ids (Optional[List[str]]): List of document IDs to delete
            filter (Optional[Dict[str, Any]]): Filter conditions for documents to delete
        """
        pass
        
    @abstractmethod
    def reset(self):
        """Reset the database.
        
        This will delete all indices and document entries.
        """
        pass 