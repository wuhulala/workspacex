from abc import ABC, abstractmethod

from workspacex.artifact import Artifact


class Embeddings(ABC):
    """Interface for embedding models.
    Embeddings are used to convert artifacts and queries into a vector space.
    """

    @abstractmethod
    def embed_artifacts(self, artifacts: list[Artifact]) -> list[list[float]]:
        """Embed artifacts."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed query text."""
        raise NotImplementedError

    async def async_embed_artifacts(self, artifacts: list[Artifact]) -> list[list[float]]:
        """Asynchronous Embed artifacts."""
        raise NotImplementedError

    async def async_embed_query(self, text: str) -> list[float]:
        """Asynchronous Embed query text."""
        raise NotImplementedError