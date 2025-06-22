import hashlib
import json
import shutil
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal

from pydantic import BaseModel

from workspacex.artifact import Artifact, ArtifactType
from .base import BaseRepository, CommonEncoder, EnumDecoder


class LocalPathRepository(BaseRepository):
    """
    Repository for managing artifacts and their metadata in the local file system.
    Implements the abstract methods from BaseRepository.
    """
    def __init__(self, storage_path: str, clear_existing: bool = False):
        """
        Initialize the artifact repository
        Args:
            storage_path: Directory path for storing data
            clear_existing: Clear existing data if True
        """
        self.storage_path = Path(storage_path)
        if clear_existing and self.storage_path.exists():
            shutil.rmtree(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
            
        self.index_path = self.storage_path / "index.json"
        self.versions_dir = self.storage_path / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, relative_path: str) -> Path:
        """
        Convert a relative artifact path to an absolute Path under storage_path.
        """
        return self.storage_path / relative_path

    def _save_index(self, index: Dict[str, Any]) -> None:
        """
        Save index to file and version it.
        Args:
            index: Index dictionary
        """
        if self.index_path.exists():
            version_name = f"index_his_{int(time.time())}.json"
            version_path = self.versions_dir / version_name
            self.index_path.replace(version_path)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _load_index(self) -> Dict[str, Any]:
        """
        Load or create index file
        Returns:
            Index dictionary
        """
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            index = {}
            self._save_index(index)
            return index

    def _artifact_dir(self, artifact_id: str) -> Path:
        """
        Get the directory path for an artifact.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the artifact directory
        """
        return self._full_path(f"artifacts/{artifact_id}")

    def _sub_dir(self, artifact_id: str) -> Path:
        """
        Get the directory path for a sub-artifact.
        """
        return self._full_path(f"artifacts/{artifact_id}/sublist")

    def _sub_data_path(self, artifact_id: str, sub_id: str, ext: str = "txt") -> Path:
        """
        Get the path for a sub-artifact's data file.
        """
        return self._full_path(f"artifacts/{artifact_id}/sublist/{sub_id}.{ext}")

    def _artifact_index_path(self, artifact_id: str) -> Path:
        """
        Get the path for the main artifact's index file.
        """
        return self._full_path(f"artifacts/{artifact_id}/index.json")

    def retrieve_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the artifact data from artifacts/{artifact_id}/index.json.
        Args:
            artifact_id: The ID of the artifact to retrieve.
        Returns:
            The artifact data as a dictionary, or None if not found.
        """
        index_path = self._artifact_index_path(artifact_id)
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def store_index(self, index_data: dict) -> None:
        """
        Store the workspace information in index.json, versioning the previous index.
        Args:
            index_data: Index data dictionary for the workspace
        Returns:
            None
        """
        index = self._load_index()
        index["workspace"] = index_data
        self._save_index(index)

    def store_artifact(self, artifact: "Artifact") -> None:
        """
        Store an artifact and its sub-artifacts in the file system.
        Args:
            artifact: Artifact object (may include sub-artifacts)
        Returns:
            None
        """
        artifact_id = artifact.artifact_id
        artifact_dir = self._artifact_dir(artifact_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        sub_artifacts_meta = []
        for sub in artifact.sublist:
            sub_id = sub.artifact_id
            sub_type = sub.artifact_type
            sub_dir = self._sub_dir(artifact_id)
            sub_dir.mkdir(parents=True, exist_ok=True)
            sub_meta = sub.to_dict()
            if sub_type == ArtifactType.TEXT:
                content = sub.content
                data_path = self._sub_data_path(artifact_id, sub_id, ext="txt")
                with open(data_path, "w", encoding="utf-8") as f:
                    f.write(content)
                sub_meta["content"] = ""
            sub_artifacts_meta.append(sub_meta)
        artifact_meta = artifact.to_dict()
        artifact_meta["sublist"] = sub_artifacts_meta
        index_path = self._artifact_index_path(artifact_id)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(artifact_meta, f, indent=2, ensure_ascii=False, cls=CommonEncoder)

    def get_index_data(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the workspace index data as a dictionary from local file system.
        Returns:
            The index data as a dictionary, or None if not found.
        """
        if not self.index_path.exists():
            return None
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)


