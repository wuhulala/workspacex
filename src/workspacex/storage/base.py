from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseRepository(ABC):
    """
    Abstract base class for repositories.
    Defines the interface for storing and retrieving workspace and artifact data.
    """
    @abstractmethod
    def store_workspace(self, workspace_meta: Dict[str, Any]) -> None:
        """
        Store the workspace metadata.
        Args:
            workspace_meta: Metadata dictionary for the workspace
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