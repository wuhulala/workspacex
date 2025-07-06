import json
from workspacex.utils.logger import logger
from builtins import anext
from datetime import datetime
from typing import Any, Dict, Generator, AsyncGenerator, Optional

from pydantic import Field, BaseModel, model_validator

from workspacex.chunk.base import ChunkConfig
from workspacex.config import WORKSPACEX_CHUNK_OVERLAP, WORKSPACEX_CHUNK_SIZE, WORKSPACEX_CHUNK_TEXT_SPLITTER, \
    WORKSPACEX_EMBEDDING_API_BASE_URL, WORKSPACEX_EMBEDDING_API_KEY, WORKSPACEX_EMBEDDING_BATCH_SIZE, \
    WORKSPACEX_EMBEDDING_CONTEXT_LENGTH, WORKSPACEX_EMBEDDING_DIMENSIONS, WORKSPACEX_EMBEDDING_MODEL, \
    WORKSPACEX_EMBEDDING_PROVIDER, WORKSPACEX_EMBEDDING_TIMEOUT, WORKSPACEX_ENABLE_HYBRID_SEARCH, \
    WORKSPACEX_HYBRID_SEARCH_THRESHOLD, WORKSPACEX_HYBRID_SEARCH_TOP_K, WORKSPACEX_VECTOR_DB_PROVIDER, \
    WORKSPACEX_ENABLE_CHUNKING, WORKSPACEX_ENABLE_EMBEDDING
from workspacex.embedding.base import EmbeddingsConfig
from workspacex.vector.factory import VectorDBConfig


class HybridSearchConfig(BaseModel):
    enabled: bool = Field(default=False, description="enabled flag")
    top_k: int = Field(default=10, description="Top K results")
    threshold: float = Field(default=0.8, description="Threshold for similarity search")

class WorkspaceConfig:
    enable_hybrid_search: bool = Field(default=False, description="Enable hybrid search")
    chunk_config: ChunkConfig = Field(default=None, description="Chunk configuration")
    embedding_config: EmbeddingsConfig = Field(default=None, description="Embedding configuration")
    vector_db_config: VectorDBConfig = Field(default=None, description="Vector database configuration")

    def __init__(self):
        
        self.chunk_config = ChunkConfig(
            enabled=WORKSPACEX_ENABLE_CHUNKING,
            text_splitter=WORKSPACEX_CHUNK_TEXT_SPLITTER,
            chunk_size=WORKSPACEX_CHUNK_SIZE,
            chunk_overlap=WORKSPACEX_CHUNK_OVERLAP
        )

        self.embedding_config = EmbeddingsConfig(
            enabled=WORKSPACEX_ENABLE_EMBEDDING,
            model_name=WORKSPACEX_EMBEDDING_MODEL,
            provider=WORKSPACEX_EMBEDDING_PROVIDER,
            api_key=WORKSPACEX_EMBEDDING_API_KEY,
            base_url=WORKSPACEX_EMBEDDING_API_BASE_URL,
            context_length=WORKSPACEX_EMBEDDING_CONTEXT_LENGTH,
            dimensions=WORKSPACEX_EMBEDDING_DIMENSIONS,
            batch_size=WORKSPACEX_EMBEDDING_BATCH_SIZE,
            timeout=WORKSPACEX_EMBEDDING_TIMEOUT
        )

        self.vector_db_config = VectorDBConfig(
            provider=WORKSPACEX_VECTOR_DB_PROVIDER
        )

        self.hybrid_search_config = HybridSearchConfig(
            enabled=WORKSPACEX_ENABLE_HYBRID_SEARCH,
            top_k=WORKSPACEX_HYBRID_SEARCH_TOP_K,
            threshold=WORKSPACEX_HYBRID_SEARCH_THRESHOLD
        )