import asyncio
import logging
import time
from workspacex.utils.timeit import timeit
from typing import List
import requests
import aiohttp
from workspacex.embedding.base import Embeddings, EmbeddingsConfig, EmbeddingsResult
from workspacex.artifact import Artifact


class OllamaEmbeddings(Embeddings):
    """
    Embedding implementation using Ollama HTTP API.
    """
    def __init__(self, config: EmbeddingsConfig):
        """
        Initialize OllamaEmbeddings with configuration.
        Args:
            config (EmbeddingsConfig): Configuration for embedding model and API.
        """
        self.config = config

    def embed_artifacts(self, artifacts: List[Artifact]) -> List[EmbeddingsResult]:
        """
        Embed a list of artifacts using Ollama HTTP API.
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
        Embed a single artifact using Ollama HTTP API.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        embedding = self.embed_query(artifact.get_embedding_text())
        return EmbeddingsResult(
            artifact=artifact,
            embedding=embedding,
            embedding_model=self.config.model_name,
            created_at=int(time.time())
        )
    
    @timeit(logging.info, "Ollama embedding query completed in {elapsed_time:.2f} seconds")
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a query string using Ollama HTTP API.
        Args:
            text (str): Text to embed.
        Returns:
            List[float]: Embedding vector.
        """
        url = self.config.base_url.rstrip('/') + "/api/embed"
        payload = {
            "model": self.config.model_name,
            "input": text
        }
        try:
            response = requests.post(url, json=payload, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
            # Ollama returns {"embedding": [...], ...}
            logging.info(f"Ollama embedding response: {data}")
            return self.resolve_embedding(data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Ollama embedding API error: {e}")

    async def async_embed_artifacts(self, artifacts: List[Artifact]) -> List[EmbeddingsResult]:
        """
        Asynchronously embed a list of artifacts using Ollama HTTP API.
        Args:
            artifacts (List[Artifact]): List of artifacts to embed.
        Returns:
            List[EmbeddingsResult]: List of embedding results.
        """
        return await asyncio.gather(*[self._async_embed_artifact(artifact) for artifact in artifacts])

    async def _async_embed_artifact(self, artifact: Artifact) -> EmbeddingsResult:
        """
        Asynchronously embed a single artifact using Ollama HTTP API.
        Args:
            artifact (Artifact): Artifact to embed.
        Returns:
            EmbeddingsResult: Embedding result for the artifact.
        """
        embedding = await self.async_embed_query(str(artifact.content))
        return EmbeddingsResult(
            artifact=artifact,
            embedding=embedding,
            embedding_model=self.config.model_name,
            created_at=int(time.time())
        )

    @timeit(logging.info, "Ollama async embedding query completed in {elapsed_time:.2f} seconds")
    async def async_embed_query(self, text: str) -> List[float]:
        """
        Asynchronously embed a query string using Ollama HTTP API.
        Args:
            text (str): Text to embed.
        Returns:
            List[float]: Embedding vector.
        """
        url = self.config.base_url.rstrip('/') + "/api/embed"
        payload = {
            "model": self.config.model_name,
            "input": text
        }
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return self.resolve_embedding(data)
        except Exception as e:
            raise RuntimeError(f"Ollama async embedding API error: {e}")
      
    @staticmethod
    def resolve_embedding(data: dict) -> List[float]:
        """
        Resolve the embedding from the response data.
        """
        if "embeddings" in data and len(data["embeddings"]) > 0:
            return data["embeddings"][0]
        else:
            return None