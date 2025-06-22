import time
import traceback

import chromadb
import logging
from chromadb import Settings
from chromadb.utils.batch_utils import create_batches

from typing import Optional

from workspacex.embedding.base import EmbeddingsResult, EmbeddingsResults
from workspacex.vector.dbs.base import VectorDB
from workspacex.config import (
    CHROMA_DATA_PATH,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_HTTP_HEADERS,
    CHROMA_HTTP_SSL,
    CHROMA_TENANT,
    CHROMA_DATABASE,
    CHROMA_CLIENT_AUTH_PROVIDER,
    CHROMA_CLIENT_AUTH_CREDENTIALS,
)


class ChromaVectorDB(VectorDB):
    """ChromaDB implementation of the VectorDB interface."""
    def __init__(self):
        settings_dict = {
            "allow_reset": True,
            "anonymized_telemetry": False,
        }
        if CHROMA_CLIENT_AUTH_PROVIDER is not None:
            settings_dict["chroma_client_auth_provider"] = CHROMA_CLIENT_AUTH_PROVIDER
        if CHROMA_CLIENT_AUTH_CREDENTIALS is not None:
            settings_dict["chroma_client_auth_credentials"] = (
                CHROMA_CLIENT_AUTH_CREDENTIALS
            )

        if CHROMA_HTTP_HOST != "":
            self.client = chromadb.HttpClient(
                host=CHROMA_HTTP_HOST,
                port=CHROMA_HTTP_PORT,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
                settings=Settings(**settings_dict),
            )
        else:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DATA_PATH,
                settings=Settings(**settings_dict),
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collection_names = [collection.name for collection in self.client.list_collections()]
        return collection_name in collection_names

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(name=collection_name)

    def search(
        self, collection_name: str, vectors: list[list[float | int]], filter: dict, threshold: float, limit: int
    ) -> Optional[EmbeddingsResults]:
        """Search for nearest neighbors based on vector similarity.
        
        Args:
            collection_name (str): Name of the collection
            vectors (list[list[float | int]]): Query vectors
            limit (int): Maximum number of results to return
            
        Returns:
            Optional[EmbeddingsResults]: Search results or None if collection doesn't exist
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection:
                result = collection.query(
                    query_embeddings=vectors,
                    # where=filter,
                    n_results=limit,
                )

                # chromadb has cosine distance, 2 (worst) -> 0 (best). Re-ordering to 0 -> 1
                # https://docs.trychroma.com/docs/collections/configure cosine equation
                distances: list = result["distances"][0]
                distances = [2 - dist for dist in distances]
                distances = [[dist / 2 for dist in distances]]

                docs = self._convert2_embedding_result_with_score(result= result, distances=distances, threshold=threshold)

                return EmbeddingsResults(
                    **{
                        "docs": docs,
                        "retrieved_at": int(time.time()),
                    }
                )
            return None
        except Exception as e:
            traceback.print_exc()
            logging.error(f"Error in search: {e}")
            return None

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[EmbeddingsResults]:
        """Query items from the collection based on filter.
        
        Args:
            collection_name (str): Name of the collection
            filter (dict): Filter conditions
            limit (Optional[int]): Maximum number of results to return
            
        Returns:
            Optional[EmbeddingsResults]: Query results or None if collection doesn't exist
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection:
                result = collection.get(
                    where=filter,
                    limit=limit,
                )

                docs = self._convert2EmbeddingResult(result)

                return EmbeddingsResults(
                    **{
                        "docs": docs,
                        "retrieved_at": int(time.time()),
                    }
                )
            return None
        except:
            return None

    def get(self, collection_name: str) -> Optional[EmbeddingsResults]:
        """Get all items in the collection.
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Optional[EmbeddingsResults]: All items in the collection or None if collection doesn't exist
        """
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.get()
            docs = self._convert2EmbeddingResult(result)
            return EmbeddingsResults(
                **{
                    "docs": docs,
                    "retrieved_at": int(time.time()),
                }
            )
        return None
    
    def _convert2_embedding_result_with_score(self, result, distances=None, threshold=None):
        """Convert ChromaDB result to list of EmbeddingsResult.
        
        Args:
            result (dict): ChromaDB query result containing documents, metadatas and ids
            distances (Optional[List[List[float]]]): Similarity scores from search results
            
        Returns:
            list[EmbeddingsResult]: List of embedding results with content and metadata
        """
        from workspacex.embedding.base import EmbeddingsMetadata
        
        docs = []
        # Flatten distances if provided (ChromaDB returns nested list)
        scores = distances[0] if distances else [None] * len(result.get("documents", []))
        
        # ChromaDB returns nested lists for all fields
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        ids = result.get("ids", [[]])[0]
        
        for document, metadata, id, score in zip(
            documents,
            metadatas,
            ids,
            scores
        ):
            # Metadata is already a dict since we stored it that way
            metadata_obj = EmbeddingsMetadata.model_validate(metadata)
            if threshold and score < threshold:
                continue
            
            docs.append(
                EmbeddingsResult(
                    id=id,
                    embedding=None,  # We don't need embeddings for retrieved results
                    content=document,
                    metadata=metadata_obj,
                    score=score
                )
            )
        return docs


    def _convert2EmbeddingResult(self, result):
        """Convert ChromaDB result to list of EmbeddingsResult.
        
        Args:
            result (dict): ChromaDB query result containing documents, metadatas and ids
            distances (Optional[List[List[float]]]): Similarity scores from search results
            
        Returns:
            list[EmbeddingsResult]: List of embedding results with content and metadata
        """
        from workspacex.embedding.base import EmbeddingsMetadata
        
        docs = []
        
        # ChromaDB returns nested lists for all fields
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        ids = result.get("ids", [])
        
        for document, metadata, id in zip(
            documents,
            metadatas,
            ids
        ):
            # Metadata is already a dict since we stored it that way
            metadata_obj = EmbeddingsMetadata.model_validate(metadata)
            
            docs.append(
                EmbeddingsResult(
                    id=id,
                    embedding=None,  # We don't need embeddings for retrieved results
                    content=document,
                    metadata=metadata_obj,
                    score=None
                )
            )
        return docs

    def insert(self, collection_name: str, items: list[EmbeddingsResult]):
        """Insert the items into the collection.
        
        Args:
            collection_name (str): Name of the collection
            items (list[EmbeddingsResult]): List of embedding results to insert
        """
        collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids = [item.id for item in items]
        documents = [item.content for item in items]
        embeddings = [item.embedding for item in items]
        # Convert metadata to dict instead of JSON string
        metadatas = [item.metadata.model_dump() for item in items]

        for batch in create_batches(
            api=self.client,
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        ):
            collection.add(*batch)

    def upsert(self, collection_name: str, items: list[EmbeddingsResult]):
        """Update or insert items in the collection.
        
        Args:
            collection_name (str): Name of the collection
            items (list[EmbeddingsResult]): List of embedding results to upsert
        """
        collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids = [item.id for item in items]
        documents = [item.content for item in items]
        embeddings = [item.embedding for item in items]
        # Convert metadata to dict instead of JSON string
        metadatas = [item.metadata.model_dump() for item in items]

        collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the collection based on the ids.
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection:
                if ids:
                    collection.delete(ids=ids)
                elif filter:
                    collection.delete(where=filter)
                else:
                    self.client.delete_collection(name=collection_name)
        except Exception as e:
            # If collection doesn't exist, that's fine - nothing to delete
            logging.debug(
                f"Attempted to delete from non-existent collection {collection_name}. Ignoring."
            )
            pass

    def reset(self):
        # Resets the database. This will delete all collections and item entries.
        return self.client.reset()
