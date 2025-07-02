from abc import ABC, abstractmethod
import uuid
from typing import List

from pydantic import BaseModel, Field

from workspacex.artifact import Artifact, ArtifactType

class ChunkConfig(BaseModel):
    enabled: bool = Field(default=False, description=" ") 
    text_splitter: str = Field(default="character", description="Text splitter")
    chunk_size: int = Field(default=1000, description="Chunk size")
    chunk_overlap: int = Field(default=100, description="Chunk overlap")
    chunk_separator: str = Field(default="\n", description="Chunk separator")
    chunk_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Chunk model")
    tokens_per_chunk: int = Field(default=256, description="Tokens per chunk")

class ChunkMetadata(BaseModel):
    chunk_index: int = Field(default=0, description="Chunk index")
    chunk_size: int = Field(default=0, description="Chunk size")
    chunk_overlap: int = Field(default=0, description="Chunk overlap")
    artifact_id: str = Field(default="", description="Origin artifact ID")
    artifact_type: str = Field(default="", description="Origin artifact type")
    parent_artifact_id: str = Field(default=None, description="Parent artifact ID")

class Chunk(Artifact):
    chunk_metadata: ChunkMetadata = Field(default=ChunkMetadata(), description="Chunk metadata")

    def __init__(self, content: str, chunk_metadata: ChunkMetadata):
        super().__init__(
            artifact_type=ArtifactType.CHUNK,
            artifact_id=str(uuid.uuid4()),
            content=content,
            metadata=chunk_metadata.model_dump()
        )
        self.chunk_metadata = chunk_metadata

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