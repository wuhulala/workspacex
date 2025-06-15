import hashlib
import json
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal

from pydantic import BaseModel

from workspacex.artifact import Artifact, ArtifactType
from .base import BaseRepository


class LocalPathRepository(BaseRepository):
    """
    Repository for managing artifacts and their metadata in the local file system.
    Implements the abstract methods from BaseRepository.
    """
    def __init__(self, storage_path: str):
        """
        Initialize the artifact repository
        Args:
            storage_path: Directory path for storing data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.json"
        self.versions_dir = self.storage_path / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

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
        return self.storage_path / "artifacts" / artifact_id

    def _sub_dir(self, artifact_id: str) -> Path:
        """
        Get the directory path for a sub-artifact.
        """
        return self._artifact_dir(artifact_id) / "sublist"

    def _sub_data_path(self, artifact_id: str, sub_id: str, ext: str = "txt") -> Path:
        """
        Get the path for a sub-artifact's data file.
        """
        return self._sub_dir(artifact_id) / f"{sub_id}.{ext}"

    def _artifact_index_path(self, artifact_id: str) -> Path:
        """
        Get the path for the main artifact's index file.
        """
        return self._artifact_dir(artifact_id) / "index.json"

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

    def store_workspace(self, workspace_meta: dict) -> None:
        """
        Store the workspace information in index.json, versioning the previous index.
        Args:
            workspace_meta: Metadata dictionary for the workspace
        Returns:
            None
        """
        index = self._load_index()
        index["workspace"] = workspace_meta
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
        sub_artifacts = getattr(artifact, "sub_artifacts", [])
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

