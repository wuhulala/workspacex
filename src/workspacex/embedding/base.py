import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from workspacex.artifact import Artifact, Chunk
from workspacex.utils.logger import logger


class EmbeddingsConfig(BaseModel):
    enabled: bool = False
    provider: str = "openai"
    api_key: str
    model_name: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    context_length: int = 8191
    dimensions: int = 1536
    batch_size: int = 100
    timeout: int = 60
    
    @classmethod
    def from_config(cls, config: dict):
        if not config:
            return None
        return cls(
            enabled=config.get("enabled", False),
            provider=config.get("provider", "openai"),
            api_key=config.get("api_key", ""),
            model_name=config.get("model_name", "text-embedding-3-small"),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            context_length=config.get("context_length", 8191),
            dimensions=config.get("dimensions", 1536),
            batch_size=config.get("batch_size", 100),
            timeout=config.get("timeout", 60)
        )

class EmbeddingsMetadata(BaseModel):
    artifact_id: str = Field(..., description="Artifact ID")
    embedding_model: str = Field(..., description="Embedding model")
    created_at: int = Field(..., description="Created at")
    updated_at: int = Field(..., description="Updated at")
    artifact_type: str = Field(..., description="Artifact type")
    parent_id: str = Field(default="", description="Parent ID")
    chunk_id: Optional[str] = Field(default=None, description="Chunk ID")
    chunk_index: Optional[int] = Field(default=None, description="Chunk index")
    chunk_size: Optional[int] = Field(default=None, description="Chunk size")
    chunk_overlap: Optional[int] = Field(default=None, description="Chunk overlap")
    
    model_config = ConfigDict(extra="allow")

class EmbeddingsResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID")
    embedding: Optional[list[float]] = Field(default=None, description="Embedding")
    content: str = Field(..., description="Content")
    metadata: Optional[EmbeddingsMetadata] = Field(..., description="Metadata")
    score: Optional[float] = Field(default=None, description="Retrieved relevance score")

class EmbeddingsResults(BaseModel):
    docs: Optional[List[EmbeddingsResult]]
    retrieved_at: int = Field(..., description="Retrieved at")

class Embeddings(ABC):
    """Interface for embedding models.
    Embeddings are used to convert artifacts and queries into a vector space.
    """

    @abstractmethod
    def embed_artifacts(self, artifacts: list[Artifact]) -> list[EmbeddingsResult]:
        """Embed artifacts."""
        raise NotImplementedError
    
    @abstractmethod
    def embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """Embed artifact."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed query text."""
        raise NotImplementedError

    async def async_embed_artifacts(self, artifacts: list[Artifact]) -> list[EmbeddingsResult]:
        """Asynchronous Embed artifacts."""
        raise NotImplementedError
    
    @abstractmethod
    def async_embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """Asynchronous Embed artifact."""
        raise NotImplementedError

    async def async_embed_query(self, text: str) -> list[float]:
        """Asynchronous Embed query text."""
        raise NotImplementedError

    @abstractmethod
    def embed_chunks(self, chunks: list[Chunk]) -> list[EmbeddingsResult]:
        """
        Embed all chunks of the given artifact.
        Args:
            artifact (Artifact): The artifact whose chunk_list will be embedded.
        Returns:
            list[EmbeddingsResult]: List of embedding results for each chunk.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def async_embed_chunks(self, chunks: list[Chunk]) -> list[EmbeddingsResult]:
        """
        Asynchronously embed all chunks of the given artifact.
        Args:
            artifact (Artifact): The artifact whose chunk_list will be embedded.
        Returns:
            list[EmbeddingsResult]: List of embedding results for each chunk.
        """
        raise NotImplementedError

class EmbeddingsBase(Embeddings):
    """
    Base class for embedding implementations that contains common functionality.
    """
    def __init__(self, config: EmbeddingsConfig):
        """
        Initialize EmbeddingsBase with configuration.
        Args:
            config (EmbeddingsConfig): Configuration for embedding model and API.
        """
        self.config = config

    def embed_artifacts(self, artifacts: List[Artifact]) -> List[EmbeddingsResult]:
        """
        Embed a list of artifacts.
        Args:
            artifacts (List[Artifact]): List of artifacts to embed.
        Returns:
            List[EmbeddingsResult]: List of embedding results.
        """
        results = []
        for artifact in artifacts:
            result = self._embed_artifact(artifact)
            results.append(result)
        return results
    
    def embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """
        Embed a single artifact.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        return self._embed_artifact(artifact)

    def _embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """
        Internal method to embed a single artifact.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        embedding = self.embed_query(artifact.get_embedding_text())
        now = int(time.time())
        metadata = EmbeddingsMetadata(
            artifact_id=artifact.artifact_id,
            embedding_model=self.config.model_name,
            created_at=now,
            updated_at=now,
            artifact_type=artifact.artifact_type.name,
            parent_id=artifact.parent_id
        )
        return EmbeddingsResult(
            id=artifact.artifact_id,
            embedding=embedding,
            content=artifact.get_embedding_text(),
            metadata=metadata
        )

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Abstract method to embed a query string.
        Args:
            text (str): Text to embed.
        Returns:
            List[float]: Embedding vector.
        """
        pass

    async def async_embed_artifacts(self, artifacts: List[Artifact]) -> List[EmbeddingsResult]:
        """
        Asynchronously embed a list of artifacts.
        Args:
            artifacts (List[Artifact]): List of artifacts to embed.
        Returns:
            List[EmbeddingsResult]: List of embedding results.
        """
        return await asyncio.gather(*[self._async_embed_artifact(artifact) for artifact in artifacts])
    
    async def async_embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """
        Asynchronously embed a single artifact.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        return await self._async_embed_artifact(artifact)

    async def _async_embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """
        Internal method to asynchronously embed a single artifact.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        embedding = await self.async_embed_query(artifact.get_embedding_text())
        now = int(time.time())
        metadata = EmbeddingsMetadata(
            artifact_id=artifact.artifact_id,
            embedding_model=self.config.model_name,
            created_at=now,
            updated_at=now,
            artifact_type=artifact.artifact_type.name,
            parent_id=artifact.parent_id
        )
        return EmbeddingsResult(
            id=artifact.artifact_id,
            embedding=embedding,
            content=artifact.get_embedding_text(),
            metadata=metadata
        )

    @abstractmethod
    async def async_embed_query(self, text: str) -> List[float]:
        """
        Abstract method to asynchronously embed a query string.
        Args:
            text (str): Text to embed.
        Returns:
            List[float]: Embedding vector.
        """
        pass

    def embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddingsResult]:
        """
        Embed a list of chunks.
        Args:
            chunks (List[Chunk]): List of chunks to embed.
        Returns:
            List[EmbeddingsResult]: List of embedding results.
        """
        results = []
        for chunk in chunks:
            result = self._embed_chunk(chunk)
            results.append(result)
        return results
    
    def _embed_chunk(self, chunk: Chunk) -> EmbeddingsResult:
        """
        Internal method to embed a single chunk.
        Args:
            chunk (Chunk): Chunk to embed.
        Returns:
            EmbeddingsResult: Embedding result for the chunk.
        """
        embedding = self.embed_query(chunk.text)
        now = int(time.time())
        metadata = EmbeddingsMetadata(
            artifact_id=chunk.artifact_id,
            embedding_model=self.config.model_name,
            created_at=now,
            updated_at=now,
            artifact_type=chunk.artifact_type,
            parent_id=chunk.parent_artifact_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_metadata.chunk_index,
            chunk_size=chunk.chunk_metadata.chunk_size,
            chunk_overlap=chunk.chunk_metadata.chunk_overlap,
        )   
        return EmbeddingsResult(
            id=chunk.chunk_id,
            embedding=embedding,
            content=chunk.content,
            metadata=metadata
        )

    async def async_embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddingsResult]:
        """
        Asynchronously embed a list of chunks.
        Args:
            chunks (List[Chunk]): List of chunks to embed.
        Returns:
            List[EmbeddingsResult]: List of embedding results.
        """
        # 🚀 Start embedding chunks
        logger.info("[async_embed_chunks]  Start embedding {} chunks...".format(len(chunks)))
        start_time = time.time()
        results = await asyncio.gather(*[self._async_embed_chunk(chunk) for chunk in chunks])
        elapsed = time.time() - start_time
        # ✅ Embedding finished
        logger.info(f"[async_embed_chunks] ✅ Finished embedding {len(chunks)} chunks in {elapsed:.2f} seconds.")
        return results
    
    async def _async_embed_chunk(self, chunk: Chunk) -> EmbeddingsResult:
        """
        Internal method to asynchronously embed a single chunk.
        Args:
            chunk (Chunk): Chunk to embed.
        Returns:
            EmbeddingsResult: Embedding result for the chunk.
        """
        embedding = await self.async_embed_query(chunk.content)
        now = int(time.time())
        metadata = EmbeddingsMetadata(
            artifact_id=chunk.artifact_id,
            embedding_model=self.config.model_name,
            created_at=now,
            updated_at=now,
            artifact_type=chunk.artifact_type,
            parent_id=chunk.parent_artifact_id, 
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_metadata.chunk_index,
            chunk_size=chunk.chunk_metadata.chunk_size,
            chunk_overlap=chunk.chunk_metadata.chunk_overlap,
        )
        return EmbeddingsResult(
            id=chunk.chunk_id,
            embedding=embedding,
            content=chunk.content,
            metadata=metadata   
        )   
    

class EmbeddingFactory:

    @staticmethod
    def get_embedder(config: EmbeddingsConfig) -> Embeddings:
        if config.provider == "openai":
            from workspacex.embedding.openai_compatible import OpenAICompatibleEmbeddings
            return OpenAICompatibleEmbeddings(config)
        elif config.provider == "ollama":
            from workspacex.embedding.ollama import OllamaEmbeddings
            return OllamaEmbeddings(config)
        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")