import json
import time
import logging
from typing import Dict, Any, Optional
import s3fs
from workspacex.artifact import Artifact, ArtifactType
from .base import BaseRepository
from workspacex.utils.timeit import timeit


class S3Repository(BaseRepository):
    """
    Repository for managing artifacts and their metadata in S3.
    Implements the abstract methods from BaseRepository using s3fs.
    """

    def __init__(self,
                 storage_path: str,
                 bucket: str,
                 s3_kwargs: Optional[dict] = None):
        """
        Initialize the S3 artifact repository.
        Args:
            storage_path: Path prefix inside the S3 bucket
            bucket: S3 bucket name
            s3_kwargs: Optional dict for s3fs.S3FileSystem
        """
        self.bucket = bucket
        self.s3_path = f"{bucket}/{storage_path.strip('/')}"
        self.fs = s3fs.S3FileSystem(**(s3_kwargs or {}))
        self.index_path = f"{self.s3_path}/index.json"
        self.versions_dir = f"{self.s3_path}/versions"
        # Ensure versions dir exists (noop for S3, but can check)
        if not self.fs.exists(self.versions_dir):
            self.fs.mkdirs(self.versions_dir, exist_ok=True)

    def _full_path(self, relative_path: str) -> str:
        """
        Convert a relative artifact path to an absolute S3 path under s3_path.
        """
        return f"{self.s3_path}/{relative_path}" if relative_path else self.s3_path

    @timeit(logging.info,
            "S3Repository._save_index took {elapsed_time:.3f} seconds")
    def _save_index(self, index: Dict[str, Any]) -> None:
        if self.fs.exists(self.index_path):
            version_name = f"index_his_{int(time.time())}.json"
            version_path = f"{self.versions_dir}/{version_name}"
            self.fs.move(self.index_path, version_path)
        with self.fs.open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    @timeit(logging.info,
            "S3Repository._load_index took {elapsed_time:.3f} seconds")
    def _load_index(self) -> Dict[str, Any]:
        if self.fs.exists(self.index_path):
            with self.fs.open(self.index_path, 'r') as f:
                return json.load(f)
        else:
            index = {}
            self._save_index(index)
            return index

    @timeit(logging.info,
            "S3Repository.retrieve_artifact took {elapsed_time:.3f} seconds")
    def retrieve_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        index_path = self._full_path(self._artifact_index_path(artifact_id))
        if self.fs.exists(index_path):
            with self.fs.open(index_path, 'r') as f:
                return json.load(f)
        return None

    @timeit(logging.info,
            "S3Repository.store_index took {elapsed_time:.3f} seconds")
    def store_index(self, index_data: dict) -> None:
        index = self._load_index()
        index["workspace"] = index_data
        self._save_index(index)

    @timeit(logging.info,
            "S3Repository.store_artifact took {elapsed_time:.3f} seconds")
    def store_artifact(self, artifact: "Artifact") -> None:
        artifact_id = artifact.artifact_id
        artifact_dir = self._full_path(self._artifact_dir(artifact_id))
        if not self.fs.exists(artifact_dir):
            self.fs.mkdirs(artifact_dir, exist_ok=True)
        sub_artifacts_meta = []
        logging.info(
            f"📦 Storing artifact {artifact_id} with {len(artifact.sublist)} sub-artifacts"
        )
        for sub in artifact.sublist:
            sub_id = sub.artifact_id
            sub_type = sub.artifact_type
            sub_dir = self._full_path(self._sub_dir(artifact_id))
            if not self.fs.exists(sub_dir):
                self.fs.mkdirs(sub_dir, exist_ok=True)
            sub_meta = sub.to_dict()
            if sub_type == ArtifactType.TEXT:
                content = sub.content
                data_path = self._full_path(
                    self._sub_data_path(artifact_id, sub_id, ext="txt"))
                with self.fs.open(data_path, "w") as f:
                    f.write(content)
                sub_meta["content"] = ""
            sub_artifacts_meta.append(sub_meta)
        artifact_meta = artifact.to_dict()
        artifact_meta["sublist"] = sub_artifacts_meta
        index_path = self._full_path(self._artifact_index_path(artifact_id))
        from workspacex.storage.local import CommonEncoder
        logging.info(f"📦 Storing artifact {artifact_id} with {len(artifact.sublist)} sub-artifacts")
        with self.fs.open(index_path, "w") as f:
            json.dump(artifact_meta,
                      f,
                      indent=2,
                      ensure_ascii=False,
                      cls=CommonEncoder)

    @timeit(logging.info,
            "S3Repository.get_index_data took {elapsed_time:.3f} seconds")
    def get_index_data(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the workspace index data as a dictionary from S3.
        Returns:
            The index data as a dictionary, or None if not found.
        """
        if not self.fs.exists(self.index_path):
            return None
        with self.fs.open(self.index_path, "r") as f:
            return json.load(f)
