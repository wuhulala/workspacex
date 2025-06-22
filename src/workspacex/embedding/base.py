from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from workspacex.artifact import Artifact


class EmbeddingsConfig(BaseModel):
    provider: str = "openai"
    api_key: str
    model_name: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    context_length: int = 8191
    dimensions: int = 1536
    batch_size: int = 100
    timeout: int = 60

class EmbeddingsMetadata(BaseModel):
    artifact_id: str = Field(..., description="Artifact ID")
    embedding_model: str = Field(..., description="Embedding model")
    created_at: int = Field(..., description="Created at")
    updated_at: int = Field(..., description="Updated at")
    artifact_type: str = Field(..., description="Artifact type")
    parent_id: str = Field(default="", description="Parent ID")
    
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