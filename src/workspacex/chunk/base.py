from abc import ABC, abstractmethod
import uuid
from pydantic import BaseModel, Field

from workspacex.artifact import Artifact, ArtifactType

class ChunkConfig(BaseModel):
    enabled: bool = Field(default=False, description=" ") 
    text_splitter: str = Field(default="character", description="Text splitter")
    chunk_size: int = Field(default=1000, description="Chunk size")
    chunk_overlap: int = Field(default=100, description="Chunk overlap")

class ChunkMetadata(BaseModel):
    chunk_index: int = Field(default=0, description="Chunk index")
    chunk_size: int = Field(default=0, description="Chunk size")
    chunk_overlap: int = Field(default=0, description="Chunk overlap")
    origin_artifact_id: str = Field(default="", description="Origin artifact ID")

class Chunk(Artifact):
    chunk_metadata: ChunkMetadata = Field(default=ChunkMetadata(), description="Chunk metadata")

    def __init__(self, content: str, chunk_metadata: ChunkMetadata):
        super().__init__(
            artifact_type=ArtifactType.CHUNK,
            artifact_id=str(uuid.uuid4()),
            content=content,
            metadata=chunk_metadata.model_dump()
        )

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
    
class ChunkerFactory:
    """Chunker factory"""

    @staticmethod
    def get_chunker(config: ChunkConfig) -> Chunker:
        if config.text_splitter == "character":
            from .character import CharacterChunker
            return CharacterChunker(config)
        else:
            raise ValueError(f"Unsupported text splitter: {config.text_splitter}")