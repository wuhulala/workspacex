import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel

from workspacex.artifact import Chunk


class BaseRepository(ABC):
    """
    Abstract base class for repositories.
    Defines the interface for storing and retrieving workspace and artifact data.
    """
    @abstractmethod
    def get_index_data(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the workspace index data as a dictionary.
        Returns:
            The index data as a dictionary, or None if not found.
        """
        pass
    
    @abstractmethod
    def store_index(self, index_data: Dict[str, Any]) -> None:
        """
        Store the workspace metadata.
        Args:
            index_data: Index data dictionary for the workspace
        Returns:
            None
        """
        pass

    @abstractmethod
    def store_artifact(self, artifact: Any, save_sub_list_content: bool = True) -> None:
        """
        Store an artifact and its sub-artifacts.
        Args:
            artifact: Artifact object (may include sub-artifacts)
        Returns:
            None
        """
        pass

    @abstractmethod
    def get_chunk_window(self, artifact_id: str, parent_id: str, chunk_index: int, pre_n: int, next_n: int) -> Optional[Tuple[Optional[list[Chunk]], Optional[Chunk], Optional[list[Chunk]]]]:
        """
        Get a window of chunks by artifact ID, parent ID, chunk ID, pre n, next n
        Args:
            artifact_id: Artifact ID
            parent_id: Parent ID
            chunk_id: Chunk ID
            pre_n: Pre n
            next_n: Next n
        Returns:
            List of chunks
        """
        pass

    @abstractmethod
    def get_chunks(self, artifact_id: str, parent_id: str) -> Optional[list[Chunk]]:
        """
        Get a window of chunks by artifact ID, parent ID, chunk ID, pre n, next n
        Args:
            artifact_id: Artifact ID
            parent_id: Parent ID
        Returns:
            List of chunks
        """
        pass

    @abstractmethod
    def store_artifact_chunks(self, artifact: Any, chunks: list[Chunk]):
        """
        store chunks in the repository, each chunk will be stored in a separate file

        file name is the chunk.chunk_file_name
        file directory is the _chunk_dir(artifact.artifact_id)
        file content is the chunk.content
        Args:
            artifact: Artifact object
            chunks: list of chunks
        Returns:
            None
        """
        pass

    @abstractmethod
    def retrieve_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the artifact data by artifact ID.
        Args:
            artifact_id: The ID of the artifact to retrieve
        Returns:
            The artifact data as a dictionary, or None if not found
        """
        pass

    @abstractmethod
    def get_subaritfact_content(self, artifact_id: str, parent_id: str) -> Optional[str]:
        """
        Retrieve the content of a sub-artifact by artifact ID and parent ID.
        Args:
            artifact_id: The ID of the artifact
            parent_id: The ID of the parent artifact
        Returns:
            The content of the sub-artifact as a string, or None if not found
        """
        pass
    
    @abstractmethod
    def get_attachment_file(self, artifact_id: str, file_name: str) -> Optional[str]:
        """
        Get the content of an attachment file by artifact ID and file name.
        Args:
            artifact_id: The ID of the artifact
            file_name: The name of the file
        Returns:
            The content of the attachment file as a string, or None if not found
        """
        pass

    def _artifact_dir(self, artifact_id: str) -> str:
        """
        Get the directory path for an artifact.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the artifact directory (as string)
        """
        return f"artifacts/{artifact_id}"

    def _sub_dir(self, artifact_id: str, sub_id: str) -> str:
        """
        Get the directory path for a sub-artifact.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the sub-artifact directory (as string)
        """
        return f"{self._artifact_dir(artifact_id)}/sublist/{sub_id}"
    
    def _chunk_dir(self, artifact_id: str, parent_id: str = None) -> str:
        """
        Get the directory path for a chunk.
        Args:
            artifact_id: Artifact ID
            parent_id: Parent ID
        Returns:
            Path to the chunk directory (as string)
        """
        if parent_id:
            return f"{self._artifact_dir(parent_id)}/sublist/{artifact_id}/chunks"
        else:
            return f"{self._artifact_dir(artifact_id)}/chunks"

    def _sub_data_path(self,
                       artifact_id: str,
                       sub_id: str,
                       ext: str = "txt") -> str:
        """
        Get the path for a sub-artifact's data file.
        Args:
            artifact_id: Artifact ID
            sub_id: Sub-artifact ID
            ext: File extension
        Returns:
            Path to the sub-artifact data file (as string)
        """
        return f"{self._sub_dir(artifact_id, sub_id)}/origin.{ext}"

    def _artifact_index_path(self, artifact_id: str) -> str:
        """
        Get the path for the main artifact's index file.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the artifact index file (as string)
        """
        return f"{self._artifact_dir(artifact_id)}/index.json"
    
    def _attachment_file_path(self, artifact_id: str, file_name: str) -> str:
        """
        Get the path for an attachment file.
        Args:
            artifact_id: Artifact ID
            file_name: File name
        Returns:	
            Path to the attachment file (as string)
        """
        return f"{self._artifact_dir(artifact_id)}/attachment_files/{file_name}"


class CommonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return json.JSONEncoder.default(self, obj)

class EnumDecoder(json.JSONDecoder):
    def decode(self, s, **kwargs):
        parsed_json = super().decode(s, **kwargs)
        for key, value in parsed_json.items():
            if isinstance(value, dict) and value.get("__enum__"):
                enum_type = globals()[value["__enum_type__"]]
                enum_value = enum_type[value["__enum_value__"]]
                parsed_json[key] = enum_value
        return parsed_json
