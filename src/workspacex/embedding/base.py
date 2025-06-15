from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from workspacex.artifact import Artifact

class EmbeddingsConfig(BaseModel):
    api_key: str
    model_name: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    context_length: int = 8191
    dimensions: int = 1536
    batch_size: int = 100
    timeout: int = 60

class EmbeddingsResult(BaseModel):
    artifact: Artifact = Field(..., description="Artifact")
    embedding: list[float] = Field(..., description="Embedding")
    embedding_model: str = Field(..., description="Embedding model")
    created_at: int = Field(..., description="Created at")

class Embeddings(ABC):
    """Interface for embedding models.
    Embeddings are used to convert artifacts and queries into a vector space.
    """

    @abstractmethod
    def embed_artifacts(self, artifacts: list[Artifact]) -> list[EmbeddingsResult]:
        """Embed artifacts."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed query text."""
        raise NotImplementedError

    async def async_embed_artifacts(self, artifacts: list[Artifact]) -> list[EmbeddingsResult]:
        """Asynchronous Embed artifacts."""
        raise NotImplementedError

    async def async_embed_query(self, text: str) -> list[float]:
        """Asynchronous Embed query text."""
        raise NotImplementedError
    