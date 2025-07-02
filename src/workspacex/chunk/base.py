from abc import ABC, abstractmethod
import uuid
from typing import List

from pydantic import BaseModel, Field

from workspacex.artifact import Artifact, Chunk, ChunkMetadata


class ChunkConfig(BaseModel):
    enabled: bool = Field(default=False, description=" ") 
    text_splitter: str = Field(default="character", description="Text splitter")
    chunk_size: int = Field(default=1000, description="Chunk size")
    chunk_overlap: int = Field(default=100, description="Chunk overlap")
    chunk_separator: str = Field(default="\n", description="Chunk separator")
    chunk_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Chunk model")
    tokens_per_chunk: int = Field(default=256, description="Tokens per chunk")

class Chunker(ABC):
    """Chunk service interface"""

    @abstractmethod
    def chunk(self, artifact: Artifact) -> list[Chunk]:
        pass

class ChunkerBase(Chunker, BaseModel):
    
    config: ChunkConfig = Field(default=ChunkConfig(), description="Chunk config")
    
    """Chunker base class"""

    def chunk(self, artifact: Artifact) -> list[Chunk]:
        pass

    def _create_chunks(self, texts: List[str], artifact: Artifact) -> List[Chunk]:
        chunks: List[Chunk] = []
        for i, text in enumerate(texts):
            chunk = Chunk(
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
        if config.text_splitter == "character":
            from .character import CharacterChunker
            return CharacterChunker(config)
        else:
            raise ValueError(f"Unsupported text splitter: {config.text_splitter}")