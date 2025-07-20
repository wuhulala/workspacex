import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from tqdm import tqdm

from workspacex.artifact import Artifact, ArtifactType, Chunk
from workspacex.utils.logger import logger
from .base import BaseRepository, CommonEncoder


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
            
        self.index_path = self._full_path("index.json")
        self.versions_dir = self._full_path("versions")
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

    def full_artifact_dir(self, artifact_id: str) -> Path:
        """
        Get the directory path for an artifact.
        Args:
            artifact_id: Artifact ID
        Returns:
            Path to the artifact directory
        """
        return self._full_path(super()._artifact_dir(artifact_id))


    def retrieve_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the artifact data from artifacts/{artifact_id}/index.json.
        Args:
            artifact_id: The ID of the artifact to retrieve.
        Returns:
            The artifact data as a dictionary, or None if not found.
        """
        artifact_index_path = self._full_path(self._artifact_index_path(artifact_id))
        if artifact_index_path.exists():
            with open(artifact_index_path, 'r', encoding='utf-8') as f:
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

    def store_artifact(self, artifact: "Artifact", save_sub_list_content: bool = True) -> None:
        """
        Store an artifact and its sub-artifacts in the file system.
        Args:
            artifact: Artifact object (may include sub-artifacts)
        Returns:
            None
        """
        artifact_id = artifact.artifact_id
        artifact_dir = self.full_artifact_dir(artifact_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_meta = artifact.to_dict()
        if save_sub_list_content:
            self.save_sub_artifact_content(artifact, artifact_id, artifact_meta, save_sub_list_content)
        index_path = self._full_path(self._artifact_index_path(artifact_id))
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(artifact_meta, f, indent=2, ensure_ascii=False, cls=CommonEncoder)

    def save_sub_artifact_content(self, artifact, artifact_id, artifact_meta,save_sub_list_content ):
        sub_artifacts_meta = []
        for sub in tqdm(artifact.sublist, desc="save_sub_artifact_content"):
            sub_id = sub.artifact_id
            sub_type = sub.artifact_type
            sub_dir = self._full_path(self._sub_dir(artifact_id, sub_id))
            sub_dir.mkdir(parents=True, exist_ok=True)
            sub_meta = sub.to_dict()
            # TODO add ext
            if save_sub_list_content:
                if sub_type == ArtifactType.TEXT:
                    content = sub.content
                    data_path = self._full_path(self._sub_data_path(artifact_id, sub_id, ext="txt"))
                    with open(data_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    sub_meta["content"] = ""
            sub_artifacts_meta.append(sub_meta)
        artifact_meta["sublist"] = sub_artifacts_meta

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

    def get_subaritfact_content(self, artifact_id: str, parent_id: str) -> Optional[str]:
        """
        Retrieve the content of a sub-artifact by artifact ID and parent ID.
        
        Args:
            artifact_id: The ID of the parent artifact
            parent_id: The ID of the sub-artifact (this parameter name seems incorrect, should be sub_id)
            
        Returns:
            The content of the sub-artifact as a string, or None if not found
        """
        data_path = self._full_path(self._sub_data_path(artifact_id=parent_id, sub_id=artifact_id, ext="txt"))
        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    return f.read()
            except (IOError, OSError) as e:
                # Log error or handle file reading issues
                return None
        
        return None
    
    def get_chunk_window(self, artifact_id: str, parent_id: str, chunk_index: int, pre_n: int, next_n: int) -> Optional[Tuple[Optional[list[Chunk]], Optional[Chunk], Optional[list[Chunk]]]]:
        """
        Get a window of chunks by artifact ID, parent ID, chunk index, pre n, next n
        Args:
            artifact_id: Artifact ID
            parent_id: Parent ID
            chunk_index: Chunk index
            pre_n: Pre n
            next_n: Next n
        Returns:
            List of chunks
        """
        chunk_dir = self._full_path(self._chunk_dir(artifact_id, parent_id))
        
        if not chunk_dir.exists():
            return None, None, None
        
        chunk_file_name = f"{artifact_id}_chunk_{chunk_index}.json"
        chunk_file_path = chunk_dir / chunk_file_name
        if not chunk_file_path.exists():
            return None, None, None
        
        with open(chunk_file_path, "r", encoding="utf-8") as f:
            chunk_content = f.read()
        
        chunk = Chunk.model_validate_json(chunk_content)
        pre_n_chunks = []
        next_n_chunks = []
        for i in range(pre_n):
            if chunk_index - i - 1 < 0:
                break
            pre_n_chunk_file_name = chunk.pre_n_chunk_file_name(i + 1)
            pre_n_chunk_file_path = chunk_dir / pre_n_chunk_file_name
            if pre_n_chunk_file_path.exists():
                with open(pre_n_chunk_file_path, "r", encoding="utf-8") as f:
                    pre_n_chunk_content = f.read()
                    pre_n_chunk = Chunk.model_validate_json(pre_n_chunk_content)
                    pre_n_chunks.append(pre_n_chunk)
        for i in range(next_n):
            next_n_chunk_file_name = chunk.next_n_chunk_file_name(i + 1)
            next_n_chunk_file_path = chunk_dir / next_n_chunk_file_name
            if next_n_chunk_file_path.exists():
                with open(next_n_chunk_file_path, "r", encoding="utf-8") as f:
                    next_n_chunk_content = f.read()
                    next_n_chunk = Chunk.model_validate_json(next_n_chunk_content)
                    next_n_chunks.append(next_n_chunk)
        return pre_n_chunks, chunk, next_n_chunks

    def get_chunks(self, artifact_id: str, parent_id: str) -> Optional[list[Chunk]]:
        chunk_dir = self._full_path(self._chunk_dir(artifact_id, parent_id))
        if not chunk_dir.exists():
            return None
        chunks = []
        for chunk_file in chunk_dir.glob("*.json"):
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    chunk = Chunk.model_validate_json(f.read())	
                    chunks.append(chunk)
            except Exception as e:
                logger.error(f"🔍 get_chunks error: {e}")
                continue
        return chunks

    def store_artifact_chunks(self, artifact: "Artifact", chunks: list["Chunk"]) -> None:
        """
        Store chunks in the local file system.
        """
        chunk_dir = self._full_path(self._chunk_dir(artifact.artifact_id, artifact.parent_id))
        if chunk_dir.exists():
            shutil.rmtree(chunk_dir)
        chunk_dir.mkdir(parents=True, exist_ok=True)
        for chunk in tqdm(chunks, desc="store_artifact_chunks"):
            file_path = chunk_dir / chunk.chunk_file_name
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(chunk.model_dump_json(indent=2))
        