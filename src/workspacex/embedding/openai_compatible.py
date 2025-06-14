from workspacex.artifact import Artifact
from workspacex.embedding.base import Embeddings, EmbeddingsResult
from pydantic import BaseModel, ConfigDict, Field

class OpenAICompatibleEmbeddingsConfig(BaseModel):
    api_key: str
    model_name: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    context_length: int = 8191
    dimension: int = 1536
    batch_size: int = 100
    timeout: int = 60


class OpenAICompatibleEmbeddings(Embeddings, BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    """
    OpenAI compatible embeddings.
    """
    config: OpenAICompatibleEmbeddingsConfig = Field(default_factory=OpenAICompatibleEmbeddingsConfig, description="Configuration for the OpenAI compatible embeddings")

    def embed_artifacts(self, artifacts: list[Artifact]) -> list[EmbeddingsResult]:
        """Embed artifacts."""
        raise NotImplementedError
    
    def _embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """Embed artifact."""
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        """Embed query text."""
        raise NotImplementedError
    
    def async_embed_artifacts(self, artifacts: list[Artifact]) -> list[EmbeddingsResult]:
        """Asynchronous Embed artifacts."""
        raise NotImplementedError
    
    def _async_embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """Asynchronous Embed artifact."""
        raise NotImplementedError

    def async_embed_query(self, text: str) -> list[float]:
        """Asynchronous Embed query text."""
        raise NotImplementedError

    
    