import json
import logging
from builtins import anext
from datetime import datetime
from typing import Any, Dict, Generator, AsyncGenerator, Optional

from pydantic import Field, BaseModel, model_validator

from workspacex.config import WORKSPACEX_EMBEDDING_API_BASE_URL, WORKSPACEX_EMBEDDING_API_KEY, WORKSPACEX_EMBEDDING_BATCH_SIZE, WORKSPACEX_EMBEDDING_CONTEXT_LENGTH, WORKSPACEX_EMBEDDING_DIMENSIONS, WORKSPACEX_EMBEDDING_MODEL, WORKSPACEX_EMBEDDING_PROVIDER, WORKSPACEX_EMBEDDING_TIMEOUT, WORKSPACEX_ENABLE_HYBRID_SEARCH, WORKSPACEX_HYBRID_SEARCH_THRESHOLD, WORKSPACEX_HYBRID_SEARCH_TOP_K, WORKSPACEX_VECTOR_DB_PROVIDER
from workspacex.embedding.base import EmbeddingsConfig
from workspacex.vector.factory import VectorDBConfig



class OutputPart(BaseModel):
    content: Any
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="metadata")

    @model_validator(mode='after')
    def setup_metadata(self):
        # Ensure metadata is initialized
        if self.metadata is None:
            self.metadata = {}
        return self
    

class Output(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="metadata")
    parts: Any = Field(default_factory=list, exclude=True, description="parts of Output")
    data: Any = Field(default=None, exclude=True, description="Output Data")

    @model_validator(mode='after')
    def setup_defaults(self):
        # Ensure metadata and parts are initialized
        if self.metadata is None:
            self.metadata = {}
        if self.parts is None:
            self.parts = []
        return self

    def add_part(self, content: Any):
        if self.parts is None:
            self.parts = []
        self.parts.append(OutputPart(content=content))

    def output_type(self):
        return "default"

class HybridSearchConfig(BaseModel):
    top_k: int = Field(default=10, description="Top K results")
    threshold: float = Field(default=0.5, description="Threshold for similarity search")

class WorkspaceConfig(BaseModel):
    enable_hybrid_search: bool = Field(default=False, description="Enable hybrid search")
    embedding_config: EmbeddingsConfig = Field(default=None, description="Embedding configuration")
    vector_db_config: VectorDBConfig = Field(default=None, description="Vector database configuration")

    def __init__(self):
        self.embedding_config = EmbeddingsConfig(
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