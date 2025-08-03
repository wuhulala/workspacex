import json
import mimetypes
import time
from typing import Dict, Any, Optional, Tuple

import s3fs
from tqdm import tqdm

from workspacex.artifact import Artifact, ArtifactType, Chunk
from workspacex.utils.logger import logger
from workspacex.utils.timeit import timeit
from .base import BaseRepository, CommonEncoder


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

    def guess_content_type(self, filename: str) -> str:
        """
        Guess the MIME type based on the file extension.
        Args:
            filename: The file name or path
        Returns:
            MIME type string, defaults to application/octet-stream
        """
        mime, _ = mimetypes.guess_type(filename)
        return mime or "application/octet-stream"

    @timeit(logger.info,
            "S3Repository._save_index took {elapsed_time:.3f} seconds")
    def _save_index(self, index: Dict[str, Any]) -> None:
        if self.fs.exists(self.index_path):
            version_name = f"index_his_{int(time.time())}.json"
            version_path = f"{self.versions_dir}/{version_name}"
            self.fs.move(self.index_path, version_path)
        content_type = self.guess_content_type(self.index_path)
        with self.fs.open(self.index_path, 'w', ContentType=content_type) as f:
            json.dump(index, f, indent=2, ensure_ascii=False, cls=CommonEncoder)

    @timeit(logger.info,
            "S3Repository._load_index took {elapsed_time:.3f} seconds")
    def _load_index(self) -> Dict[str, Any]:
        if self.fs.exists(self.index_path):
            with self.fs.open(self.index_path, 'r') as f:
                return json.load(f)
        else:
            index = {}
            self._save_index(index)
            return index

    @timeit(logger.info,
            "S3Repository.retrieve_artifact took {elapsed_time:.3f} seconds")
    def retrieve_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        index_path = self._full_path(self._artifact_index_path(artifact_id))
        if self.fs.exists(index_path):
            with self.fs.open(index_path, 'r') as f:
                return json.load(f)
        return None

    @timeit(logger.info,
            "S3Repository.store_index took {elapsed_time:.3f} seconds")
    def store_index(self, index_data: dict) -> None:
        index = self._load_index()
        index["workspace"] = index_data
        self._save_index(index)

    @timeit(logger.info,
            "S3Repository.store_artifact took {elapsed_time:.3f} seconds")
    def store_artifact(self, artifact: "Artifact", save_sub_list_content: bool = True, save_attachment_files: bool = True) -> None:
        artifact_id = artifact.artifact_id
        artifact_dir = self._full_path(self._artifact_dir(artifact_id))
        if not self.fs.exists(artifact_dir):
            self.fs.mkdirs(artifact_dir, exist_ok=True)
        sub_artifacts_meta = []
        logger.info(
            f"📦 Storing artifact {artifact_id} with {len(artifact.sublist)} sub-artifacts"
        )
        artifact_meta = artifact.to_dict()
        if save_sub_list_content:
            self.save_sub_artifact_content(artifact, artifact_id, artifact_meta, sub_artifacts_meta, save_sub_list_content)
        if save_attachment_files:
            self.save_attachment_files(artifact)
        index_path = self._full_path(self._artifact_index_path(artifact_id))
        from workspacex.storage.local import CommonEncoder
        logger.info(f"📦 Storing artifact {artifact_id} with {len(artifact.sublist)} sub-artifacts")
        content_type = self.guess_content_type(index_path)
        with self.fs.open(index_path, "w", ContentType=content_type) as f:
            json.dump(artifact_meta,
                      f,
                      indent=2,
                      ensure_ascii=False,
                      cls=CommonEncoder)
            
    def save_attachment_files(self, artifact: "Artifact") -> None:
        """
        Save attachment files to the S3 bucket.
        """
        if not artifact.attachment_files:
            return
        for file in tqdm(artifact.attachment_files.values(), desc="save_attachment_files"):
            file_path = self._full_path(self._attachment_file_path(artifact.artifact_id, file.file_name))
            content_type = self.guess_content_type(file_path)
            with self.fs.open(file_path, "wb", ContentType=content_type) as f:
                with open(file.file_path, "rb") as src:
                    f.write(src.read())
                logger.info(f"Artifact {artifact.artifact_id} saved attachment file {file_path}")
        logger.info(f"Artifact {artifact.artifact_id} saved {len(artifact.attachment_files)} attachment files")

    def save_sub_artifact_content(self, artifact, artifact_id, artifact_meta, sub_artifacts_meta, save_sub_list_content):
        for sub in tqdm(artifact.sublist, desc="Uploading sub-artifacts"):
            sub_id = sub.artifact_id
            sub_type = sub.artifact_type
            sub_dir = self._full_path(self._sub_dir(artifact_id, sub_id))
            if not self.fs.exists(sub_dir):
                self.fs.mkdirs(sub_dir, exist_ok=True)
            sub_meta = sub.to_dict()
            if save_sub_list_content:
                if sub_type == ArtifactType.TEXT:
                    content = sub.content
                    data_path = self._full_path(
                        self._sub_data_path(artifact_id, sub_id, ext="txt"))
                    content_type = self.guess_content_type(data_path)
                    with self.fs.open(data_path, "w", ContentType=content_type) as f:
                        f.write(content)
                    sub_meta["content"] = ""
            sub_artifacts_meta.append(sub_meta)
            artifact_meta["sublist"] = sub_artifacts_meta

    @timeit(logger.info,
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
        
    def get_subaritfact_content(self, artifact_id: str, parent_id: str) -> Optional[str]:
        """
        Retrieve the content of a sub-artifact by artifact ID and parent ID.
        """
        data_path = self._full_path(self._sub_data_path(artifact_id=parent_id, sub_id=artifact_id, ext="txt"))
        if self.fs.exists(data_path):
            with self.fs.open(data_path, "r") as f:
                return f.read()
        return None
    
    def get_chunk_window(self, artifact_id: str, parent_id: str, chunk_index: int, pre_n: int, next_n: int) \
            -> Optional[Tuple[Optional[list[Chunk]], Optional[Chunk], Optional[list[Chunk]]]]:
        """
        Get a window of chunks by artifact ID, parent ID, chunk index, pre n, next n
        """
        chunk_dir = self._full_path(self._chunk_dir(artifact_id, parent_id))
        logger.info(f"🔍 get_chunk_window chunk_dir: {chunk_dir}")
        if not self.fs.exists(chunk_dir):
            return None, None, None
        chunk_file_name = f"{artifact_id}_chunk_{chunk_index}.json"
        chunk_file_path = f"{chunk_dir}/{chunk_file_name}"
        logger.debug(f"🔍 get_chunk_window chunk_file_path: {chunk_file_path}")
        if not self.fs.exists(chunk_file_path):
            return None, None, None
        with self.fs.open(chunk_file_path, "r") as f:
            chunk_content = f.read()
        chunk = Chunk.model_validate_json(chunk_content)
        pre_n_chunks = []
        next_n_chunks = []
        if pre_n > 0:
            for i in range(pre_n):
                if chunk_index - i - 1 < 0:
                    break
                pre_n_chunk_file_name = chunk.pre_n_chunk_file_name(i + 1)
                pre_n_chunk_file_path = f"{chunk_dir}/{pre_n_chunk_file_name}"
                if self.fs.exists(pre_n_chunk_file_path):
                    with self.fs.open(pre_n_chunk_file_path, "r") as f:
                        pre_n_chunk_content = f.read()
                        pre_n_chunk = Chunk.model_validate_json(pre_n_chunk_content)
                        pre_n_chunks.append(pre_n_chunk)
        if next_n >0:
            for i in range(next_n):
                next_n_chunk_file_name = chunk.next_n_chunk_file_name(i + 1)
                next_n_chunk_file_path = f"{chunk_dir}/{next_n_chunk_file_name}"
                if self.fs.exists(next_n_chunk_file_path):
                    with self.fs.open(next_n_chunk_file_path, "r") as f:
                        next_n_chunk_content = f.read()
                        next_n_chunk = Chunk.model_validate_json(next_n_chunk_content)
                        next_n_chunks.append(next_n_chunk)
        return pre_n_chunks, chunk, next_n_chunks

    def get_chunks(self, artifact_id: str, parent_id: str) -> Optional[list[Chunk]]:
        chunk_dir = self._full_path(self._chunk_dir(artifact_id, parent_id))
        if not self.fs.exists(chunk_dir):
            return None
        chunks = []
        for chunk_file in self.fs.glob(f"{chunk_dir}/*.json"):
            try:
                with self.fs.open(chunk_file, "r") as f:
                    chunk_content = f.read()
                    logger.debug(f"{chunk_content}")
                    chunk = Chunk.model_validate_json(chunk_content)
                    chunks.append(chunk)
            except Exception as e:
                logger.error(f"🔍 get_chunks error: {e}")
                continue
        return chunks

    def store_artifact_chunks(self, artifact: "Artifact", chunks: list["Chunk"]) -> None:
        """
        Store chunks in the S3 bucket.
        """
        chunk_dir = self._full_path(self._chunk_dir(artifact.artifact_id, artifact.parent_id))
        if self.fs.exists(chunk_dir):
            # 删除 S3 目录下所有内容
            files = self.fs.glob(f"{chunk_dir}/*.json")
            for file in files:
                try:
                    self.fs.rm(file, recursive=True)
                except FileNotFoundError:
                    logger.debug(f"🔍 store_artifact_chunks skip missing file: {file}")
                    pass
        if not self.fs.exists(chunk_dir):
            self.fs.mkdirs(chunk_dir, exist_ok=True)
        for chunk in tqdm(chunks, desc="Uploading chunks"):
            try:
                file_path = f"{chunk_dir}/{chunk.chunk_file_name}"
                logger.debug(f"🔍 store_artifact_chunks file_path: {file_path}")
                content_type = self.guess_content_type(file_path)
                with self.fs.open(file_path, "w", ContentType=content_type) as f:
                    f.write(chunk.model_dump_json(indent=2))
            except Exception as e:
                logger.error(f"🔍 store_artifact_chunks error: {e}")
                raise e
            
    def get_attachment_file(self, artifact_id: str, file_name: str) -> Optional[str]:
        """
        Get the content of an attachment file by artifact ID and file name.
        """
        file_path = self._full_path(self._attachment_file_path(artifact_id, file_name))
        if self.fs.exists(file_path):
            with self.fs.open(file_path, "rb") as f:
                return f.read()
        return None