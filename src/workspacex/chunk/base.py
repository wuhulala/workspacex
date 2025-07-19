from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field

from workspacex.artifact import Artifact, Chunk, ChunkMetadata


class ChunkConfig(BaseModel):
    enabled: bool = Field(default=False, description=" ") 
    provider: str = Field(default="character", description="Text splitter")
    chunk_size: int = Field(default=1000, description="Chunk size")
    chunk_overlap: int = Field(default=100, description="Chunk overlap")
    chunk_separator: str = Field(default="\n", description="Chunk separator")
    chunk_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Chunk model")
    tokens_per_chunk: int = Field(default=256, description="Tokens per chunk")
    
    @classmethod
    def from_config(cls, config: dict):
        if not config:
            return None
        return cls(
            enabled=config.get("enabled", False),
            provider=config.get("provider", "character"),
            chunk_size=config.get("chunk_size", 1000),
            chunk_overlap=config.get("chunk_overlap", 100),
            chunk_separator=config.get("chunk_separator", "\n"),
            chunk_model=config.get("chunk_model", "sentence-transformers/all-MiniLM-L6-v2"),
            tokens_per_chunk=config.get("tokens_per_chunk", 256)
        )

class Chunker(ABC):
    """Chunk service interface"""

    @abstractmethod
    def chunk(self, artifact: Artifact) -> list[Chunk]:
        pass

class ChunkerBase(Chunker, BaseModel):
    
    config: ChunkConfig = Field(default=ChunkConfig(), description="Chunk config")
    
    """Chunker base class"""

    async def chunk(self, artifact: Artifact) -> list[Chunk]:
        pass

    def _create_chunks(self, texts: List[str], artifact: Artifact) -> List[Chunk]:
        chunks: List[Chunk] = []
        for i, text in enumerate(texts):
            chunk = Chunk(
                chunk_id=f"{artifact.artifact_id}_chunk_{i}",
                content=text,
                chunk_metadata=ChunkMetadata(
                    chunk_index=i,
                    chunk_size=len(text),
                    artifact_id=artifact.artifact_id,
                    artifact_type=artifact.artifact_type.value,
                    parent_artifact_id=artifact.parent_id,
                )
            )
            chunks.append(chunk)
        return chunks


class ChunkerFactory:
    """Chunker factory"""

    @staticmethod
    def get_chunker(config: ChunkConfig) -> Chunker:
        if config.provider == "character":
            from .character import CharacterChunker
            return CharacterChunker(config)
        elif config.provider == "sentence_token":
            from .sentence import SentenceTokenChunker
            return SentenceTokenChunker(config)
        else:
            raise ValueError(f"Unsupported text splitter: {config.provider}")