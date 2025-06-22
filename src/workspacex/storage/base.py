from abc import ABC, abstractmethod
from enum import Enum
import json
from typing import Any, Dict, Optional

from pydantic import BaseModel


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
    def store_artifact(self, artifact: Any) -> None:
        """
        Store an artifact and its sub-artifacts.
        Args:
            artifact: Artifact object (may include sub-artifacts)
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

   

    def _artifact_dir(self, artifact_id: str) -> str:
        """
        Get the directory path for an artifact.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the artifact directory (as string)
        """
        return f"artifacts/{artifact_id}"

    def _sub_dir(self, artifact_id: str) -> str:
        """
        Get the directory path for a sub-artifact.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the sub-artifact directory (as string)
        """
        return f"{self._artifact_dir(artifact_id)}/sublist"

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
        return f"{self._sub_dir(artifact_id)}/{sub_id}.{ext}"

    def _artifact_index_path(self, artifact_id: str) -> str:
        """
        Get the path for the main artifact's index file.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the artifact index file (as string)
        """
        return f"{self._artifact_dir(artifact_id)}/index.json"


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
