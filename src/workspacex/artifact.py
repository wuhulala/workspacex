import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field, model_validator


class ArtifactType(Enum):
    """Defines supported artifact types"""
    TEXT = "TEXT"
    CODE = "CODE"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    SVG = "SVG"
    JSON = "JSON"
    CSV = "CSV"
    TABLE = "TABLE"
    CHART = "CHART"
    DIAGRAM = "DIAGRAM"
    MCP_CALL = "MCP_CALL"
    TOOL_CALL = "TOOL_CALL"
    LLM_OUTPUT = "LLM_OUTPUT"
    WEB_PAGES = "WEB_PAGES"
    DIR = "DIR"
    CUSTOM = "CUSTOM"
    NOVEL = "NOVEL"
    CHUNK = "CHUNK"


class ChunkMetadata(BaseModel):
    chunk_index: int = Field(default=0, description="Chunk index")
    chunk_size: int = Field(default=0, description="Chunk size")
    chunk_overlap: int = Field(default=0, description="Chunk overlap")
    artifact_id: str = Field(default="", description="Origin artifact ID")
    artifact_type: str = Field(default="", description="Origin artifact type")
    parent_artifact_id: str = Field(default=None, description="Parent artifact ID")

class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Chunk ID")
    chunk_metadata: ChunkMetadata = Field(default=ChunkMetadata(), description="Chunk metadata")
    content: str = Field(default="", description="Chunk content")

    @property
    def parent_artifact_id(self) -> str:
        return self.chunk_metadata.parent_artifact_id
    
    @property
    def artifact_id(self) -> str:
        return self.chunk_metadata.artifact_id
    
    @property
    def artifact_type(self) -> str:
        return self.chunk_metadata.artifact_type
    
    @property
    def chunk_file_name(self) -> str:
        return f"{self.artifact_id}_chunk_{self.chunk_metadata.chunk_index}.json"

    def pre_n_chunk_file_name(self, pre_n) -> str:
        return f"{self.artifact_id}_chunk_{self.chunk_metadata.chunk_index - pre_n}.json"


    def next_n_chunk_file_name(self, next_n) -> str:
        return f"{self.artifact_id}_chunk_{self.chunk_metadata.chunk_index + next_n}.json"

class ArtifactStatus(Enum):
    """Artifact status"""
    DRAFT = auto()      # Draft status
    COMPLETE = auto()   # Completed status
    EDITED = auto()     # Edited status
    ARCHIVED = auto()   # Archived status

class Artifact(BaseModel):
    """
    Represents a specific content generation result (artifact)
    
    Artifacts are the basic units of Artifacts technology, representing a structured content unit
    Can be code, markdown, charts, and various other formats
    """

    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the artifact")
    parent_id: str = Field(default="", description="Parent identifier for the artifact")
    artifact_type: ArtifactType = Field(..., description="Type of the artifact")
    content: Any = Field(..., description="Content of the artifact")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the artifact")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last updated timestamp")
    status: ArtifactStatus = Field(default=ArtifactStatus.ARCHIVED, description="Current status of the artifact")
    current_version: str = Field(default="", description="Current version of the artifact")
    version_history: list = Field(default_factory=list, description="History of versions for the artifact")
    create_file: bool = Field(default=False, description="Flag to indicate if a file should be created")
    sublist: List['Artifact'] = Field(default_factory=list, description="List of sub-artifacts (children)")
    chunk_list: List[Chunk] = Field(default_factory=list, description="List of chunks")

    # Use model_validator for initialization logic
    @model_validator(mode='after')
    def setup_artifact(self):
        """Initialize the artifact after validation"""
        # Ensure artifact_id is always a valid string
        if not self.artifact_id:
            self.artifact_id = str(uuid.uuid4())
            
        # Reset status to DRAFT for new artifacts
        if not self.version_history:
            self.status = ArtifactStatus.DRAFT
            # Record initial version
            self._record_version("Initial version")
        
        return self

    def _record_version(self, description: str) -> None:
        """Record current state as a new version"""
        version = {
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "content": self.content,
            "status": self.status
        }
        self.version_history.append(version)
        self.updated_at = version["timestamp"]

    def update_content(self, content: Any, description: str = "Content update") -> None:
        """
        Update artifact content and record version
        
        Args:
            content: New content
            description: Update description
        """
        self.content = content
        self.status = ArtifactStatus.EDITED
        self._record_version(description)

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update artifact metadata
        
        Args:
            metadata: New metadata (will be merged with existing metadata)
        """
        self.metadata.update(metadata)
        self.updated_at = datetime.now().isoformat()

    def mark_complete(self) -> None:
        """Mark the artifact as complete"""
        self.status = ArtifactStatus.COMPLETE
        self._record_version("Marked as complete")

    def mark_chunkable(self) -> None:
        self.metadata['chunkable'] = True

    def archive(self) -> None:
        """Archive the artifact"""
        self.status = ArtifactStatus.ARCHIVED
        self._record_version("Artifact archived")

    def get_version(self, index: int) -> Optional[Dict[str, Any]]:
        """Get version at the specified index"""
        if 0 <= index < len(self.version_history):
            return self.version_history[index]
        return None

    def revert_to_version(self, index: int) -> bool:
        """Revert to a specific version"""
        version = self.get_version(index)
        if version:
            self.content = version["content"]
            self.status = version["status"]
            self._record_version(f"Reverted to version {index}")
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert artifact to dictionary, including sublist.
        Returns:
            Dictionary representation of the artifact
        """
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.name,
            "parent_id": self.parent_id,
            # "version_count": len(self.version_history),
            # "version_history": self.version_history,
            "sublist": [sub.to_dict() for sub in self.sublist] if self.sublist else []
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Artifact"]:
        """
        Create an artifact instance from a dictionary, including sublist.
        Args:
            data: Dictionary data
        Returns:
            Artifact instance or None if artifact_id is not present
        """
        if not data.get("artifact_id"):
            return None
        artifact_type = ArtifactType(data.get("artifact_type"))
        artifact = cls(
            artifact_type=artifact_type,
            content=data.get("content"),
            metadata=data.get("metadata"),
            artifact_id=data.get("artifact_id")
        )
        artifact.parent_id = data.get("parent_id")
        artifact.created_at = data.get("created_at")
        artifact.updated_at = data.get("updated_at")
        artifact.status = ArtifactStatus[data.get("status")]
        # If version history exists, restore it as well
        if "version_history" in data:
            artifact.version_history = data.get("version_history")
        # Restore sublist if present
        if "sublist" in data and data.get("sublist"):
            artifact.sublist = [cls.from_dict(sub) for sub in data.get("sublist")]
        return artifact

    def add_subartifact(self, subartifact: 'Artifact') -> None:
        """
        Add a subartifact (child artifact) to this artifact.
        Args:
            subartifact: The subartifact to add
        """
        self.sublist.append(subartifact)

    def get_embedding_text(self) -> Optional[str]:
        """
        Get the embedding text for the artifact.
        """
        if not self.content:
            return None
        return str(self.content)

    def get_reranked_text(self) -> Optional[str]:
        """
        Get the reranked text for the artifact.
        """
        if not self.content:
            return None
        return str(self.content)

    def get_chunk_list(self) -> list[Chunk]:
        return self.chunk_list

    def get_metadata_value(self, key: str) -> Any:
        """
        Get the value of a metadata field by key.
        Args:
            key (str): The metadata key to retrieve
        Returns:
            Any: The value associated with the key, or None if not found
        """
        return self.metadata.get(key)

    @property
    def support_chunking(self):
        return True

class HybridSearchQuery(BaseModel):
    query: str = Field(..., description="Query string")
    filter_types: Optional[List[ArtifactType]] = Field(default=None, description="Filter types")
    limit: int = Field(default=10, description="Limit")
    threshold: float = Field(default=0.8, description="Threshold")

class HybridSearchResult(BaseModel):
    """
    Search result for an artifact
    """
    artifact: Artifact = Field(..., description="Artifact")
    score: float = Field(..., description="Score")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")

class ChunkSearchQuery(BaseModel):
    query: str = Field(..., description="Query string")
    limit: int = Field(default=10, description="Limit")
    threshold: float = Field(default=0.8, description="Threshold")
    pre_n: int = Field(default=3, description="Pre n")
    next_n: int = Field(default=3, description="Next n")

class ChunkSearchResult(BaseModel):
    """
    Search result for a chunk
    """
    chunk: Chunk = Field(..., description="Chunk")
    pre_n_chunks: Optional[List[Chunk]] = Field(default_factory=list, description="Pre n chunk")
    next_n_chunks: Optional[List[Chunk]] = Field(default_factory=list, description="Next n chunk")
    score: float = Field(..., description="Score")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")