import asyncio
import time
import logging
from typing import Any, List
from workspacex.artifact import Artifact
from workspacex.embedding.base import Embeddings, EmbeddingsConfig, EmbeddingsResult
from workspacex.utils.timeit import timeit
from openai import OpenAI


class OpenAICompatibleEmbeddings(Embeddings):
    """
    OpenAI compatible embeddings using OpenAI-compatible HTTP API.

    - text-embedding-v4: [2048、1536、1024（默认）、768、512、256、128、64]
    - text-embedding-v3: [1024(默认)、512、256、128、64]
    - text-embedding-v2: [1536]
    - text-embedding-v1: [1536]
    """

    def __init__(self, config: EmbeddingsConfig):
        """
        Initialize OpenAICompatibleEmbeddings with configuration.
        Args:
            config (EmbeddingsConfig): Configuration for embedding model and API.
        """
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def embed_artifacts(self,
                        artifacts: List[Artifact]) -> List[EmbeddingsResult]:
        """
        Embed a list of artifacts using OpenAI-compatible HTTP API.
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

    def _embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """
        Embed a single artifact using OpenAI-compatible HTTP API.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        embedding = self.embed_query(artifact.get_embedding_text())
        return EmbeddingsResult(artifact=artifact,
                                embedding=embedding,
                                embedding_model=self.config.model_name,
                                created_at=int(time.time()))

    @timeit(logging.info,
            "OpenAI embedding query completed in {elapsed_time:.3f} seconds")
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a query string using OpenAI-compatible HTTP API.
        Args:
            text (str): Text to embed.
        Returns:
            List[float]: Embedding vector.
        """
        try:
            response = self.client.embeddings.create(
                model=self.config.model_name,
                input=text,
                dimensions=self.config.dimensions)
            data = response.data
            logging.info(f"OpenAI embedding response: {data}")
            return self.resolve_embedding(data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"OpenAI embedding API error: {e}")

    async def async_embed_artifacts(
            self, artifacts: List[Artifact]) -> List[EmbeddingsResult]:
        """
        Asynchronously embed a list of artifacts using OpenAI-compatible HTTP API.
        Args:
            artifacts (List[Artifact]): List of artifacts to embed.
        Returns:
            List[EmbeddingsResult]: List of embedding results.
        """
        return await asyncio.gather(
            *[self._async_embed_artifact(artifact) for artifact in artifacts])

    async def _async_embed_artifact(self,
                                    artifact: Artifact) -> EmbeddingsResult:
        """
        Asynchronously embed a single artifact using OpenAI-compatible HTTP API.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        embedding = await self.async_embed_query(artifact.get_embedding_text())
        return EmbeddingsResult(artifact=artifact,
                                embedding=embedding,
                                embedding_model=self.config.model_name,
                                created_at=int(time.time()))

    @timeit(
        logging.info,
        "OpenAI async embedding query completed in {elapsed_time:.3f} seconds")
    async def async_embed_query(self, text: str) -> List[float]:
        """
        Asynchronously embed a query string using OpenAI-compatible HTTP API.
        Args:
            text (str): Text to embed.
        Returns:
            List[float]: Embedding vector.
        """
        try:
            response = self.client.embeddings.create(
                model=self.config.model_name,
                input=text,
                dimensions=self.config.dimensions)
            data = response.data
            logging.info(f"OpenAI embedding response: {data}")
            return self.resolve_embedding(data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"OpenAI async embedding API error: {e}")

    @staticmethod
    def resolve_embedding(data: list[Any]) -> List[float]:
        """
        Resolve the embedding from the response data (OpenAI format).
        Args:
            data (dict): Response data from OpenAI API.
        Returns:
            List[float]: Embedding vector.
        """
        return data[0].embedding
