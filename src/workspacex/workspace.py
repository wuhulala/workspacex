import asyncio
import os
import threading
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict
from tqdm import tqdm


from workspacex.artifact import ArtifactType, Artifact, Chunk, ChunkSearchQuery, ChunkSearchResult, HybridSearchResult, \
    HybridSearchQuery
from workspacex.artifacts.arxiv import ArxivArtifact
from workspacex.base import WorkspaceConfig
from workspacex.chunk.base import ChunkerFactory
from workspacex.code_artifact import CodeArtifact
from workspacex.embedding.base import EmbeddingFactory
from workspacex.fulltext.dbs.base import FulltextDB, FulltextSearchResult
from workspacex.fulltext.factory import FulltextDBFactory
from workspacex.artifacts.novel_artifact import NovelArtifact
from workspacex.observer import WorkspaceObserver, get_observer
from workspacex.reranker.base import RerankResult
from workspacex.reranker.factory import RerankerFactory
from workspacex.storage.base import BaseRepository
from workspacex.storage.local import LocalPathRepository
from workspacex.utils.logger import logger
from workspacex.vector.dbs.base import VectorDB
from workspacex.vector.factory import VectorDBFactory
from workspacex.chunk.base import ChunkMetadata


class WorkSpace(BaseModel):
    """
    Artifact workspace, managing a group of related artifacts
    
    Provides collaborative editing features, supporting version management, update notifications, etc. for multiple Artifacts
    """

    workspace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="unique identifier for the workspace")
    name: str = Field(default="", description="name of the workspace")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default={}, description="metadata")
    artifacts: List[Artifact] = Field(default=[], description="list of artifacts")

    observers: Optional[List[WorkspaceObserver]] = Field(default=[], description="list of observers", exclude=True)
    repository: Optional[BaseRepository] = Field(default=None, description="local artifact repository", exclude=True)
    workspace_config: Optional[WorkspaceConfig] = Field(default=None, description="workspace config", exclude=True)
    
    vector_db: Optional[VectorDB] = Field(default=None, description="vector_db instance", exclude=True)
    fulltext_db: Optional[FulltextDB] = Field(default=None, description="fulltext_db instance", exclude=True)
    kv_db: Optional[dict[str, Any]] = Field(default_factory=dict, description="kv_db instance", exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    
    def __init__(
            self,
            workspace_id: Optional[str] = None,
            name: Optional[str] = None,
            storage_path: Optional[str] = None,
            observers: Optional[List[WorkspaceObserver]] = None,
            use_default_observer: bool = True,
            clear_existing: bool = False,
            repository: Optional[BaseRepository] = None,
            **kwargs
    ):
        super().__init__()
        self.workspace_id = workspace_id or str(uuid.uuid4())
        self.name = name or f"Workspace-{self.workspace_id[:8]}"
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        if not kwargs.get("config") and not isinstance(kwargs.get("config"), WorkspaceConfig):
            self.workspace_config = WorkspaceConfig()
        else:
            self.workspace_config = kwargs["config"]

        # Initialize repository first
        if repository:
            self.repository = repository
        else:
            storage_dir = storage_path or os.path.join("data", "workspaces", self.workspace_id)
            self.repository = LocalPathRepository(storage_dir, clear_existing=clear_existing)

        # Initialize artifacts and metadata
        if clear_existing:
            self.artifacts = []
            self.metadata = {}
        else:
            # Try to load existing workspace data
            workspace_data = self._load_workspace_data()
            if workspace_data:
                self.artifacts = workspace_data.get('artifacts', [])
                self.metadata = workspace_data.get('metadata', {})
                self.created_at = workspace_data.get('created_at', self.created_at)
                self.updated_at = workspace_data.get('updated_at', self.updated_at)
            else:
                self.artifacts = []
                self.metadata = {}

        # Initialize observers
        self.observers: List[WorkspaceObserver] = []
        if use_default_observer:
            self.observers.append(get_observer())

        if observers:
            for observer in observers:
                if observer not in self.observers:  # Avoid duplicates
                    self.add_observer(observer)


        
        # Initialize full-text search database if enabled
        if self.workspace_config.fulltext_db_config and self.workspace_config.fulltext_db_config.provider:
            self.fulltext_db = FulltextDBFactory.get_fulltext_db(self.workspace_config.fulltext_db_config)
        else:
            self.fulltext_db = None
            
        # Initialize vector database if enabled
        if self.workspace_config.vector_db_config and self.workspace_config.vector_db_config.provider:
            self.vector_db = VectorDBFactory.get_vector_db(self.workspace_config.vector_db_config)
        else:
            self.vector_db = None
        
        self._reranker = None
        self._chunker = None
        self._embedder = None
        
        # Initialize lock for thread-safe operations
        self._save_lock = asyncio.Lock()
        
        if clear_existing:
            if self.vector_db:
                self.vector_db.delete(self.default_vector_collection)
            if self.fulltext_db:
                self.fulltext_db.delete(self.workspace_id)

    @property
    def chunker(self):
        if not self._chunker:
            self._chunker = ChunkerFactory.get_chunker(self.workspace_config.chunk_config)
        return self._chunker

    @property
    def embedder(self):
        if not self._embedder:
            self._embedder = EmbeddingFactory.get_embedder(self.workspace_config.embedding_config)
        return self._embedder

    @property
    def reranker(self):
        if not self._reranker:
            self._reranker = RerankerFactory.getReranker(self.workspace_config.reranker_config)
        return self._reranker


    @property
    def default_vector_collection(self):
        return f"{self.workspace_id}"

    @property
    def summary_vector_collection(self):
        return f"summary_{self.workspace_id}"

    @property
    def full_text_index(self):
        return f"f_{self.workspace_id}"

    @classmethod
    def from_s3_storages(cls, workspace_id: Optional[str] = None,
                         name: Optional[str] = None,
                         storage_path: Optional[str] = None,
                         use_ssl=False,
                         **kwargs
                         ):
        from workspacex.storage.s3 import S3Repository

        # MinIO connection config
        s3_kwargs = {
            'key': os.getenv('MINIO_ACCESS_KEY'),
            'secret': os.getenv('MINIO_SECRET_KEY'),
            'client_kwargs': {
                'endpoint_url': os.getenv('MINIO_ENDPOINT_URL')
            },
            'use_ssl': False
        }
        bucket = os.getenv('MINIO_WORKSPACE_BUCKET')

        # Ensure bucket exists (create if not)
        import s3fs
        fs = s3fs.S3FileSystem(**s3_kwargs)
        if not fs.exists(bucket):
            fs.mkdir(bucket)

        # Create S3Repository
        repo = S3Repository(storage_path=storage_path,
                            bucket=bucket,
                            s3_kwargs=s3_kwargs)

        # Create a workspace using S3Repository
        return cls(workspace_id=workspace_id,
                   name=name,
                   repository=repo, **kwargs
                   )

    @classmethod
    def from_local_storages(cls, workspace_id: Optional[str] = None,
                            name: Optional[str] = None,
                            storage_path: Optional[str] = None,
                            observers: Optional[List[WorkspaceObserver]] = None,
                            use_default_observer: bool = True
                            , **kwargs

                            ) -> "WorkSpace":
        """
        Create a workspace instance from local storage
        
        Args:
            workspace_id: Optional workspace ID
            name: Optional workspace name
            storage_path: Optional storage path
            observers: Optional list of observers
            use_default_observer: Whether to use default observer
            
        Returns:
            WorkSpace instance
        """
        workspace = cls(
            workspace_id=workspace_id,
            name=name,
            storage_path=storage_path,
            observers=observers,
            use_default_observer=use_default_observer,
            clear_existing=False,  # Always try to load existing data
            **kwargs
        )
        return workspace

    #########################################################
    # Artifact Management
    #########################################################

    async def create_artifact(
            self,
            artifact_type: Union[ArtifactType, str],
            artifact_id: Optional[str] = None,
            content: Optional[Any] = None,
            metadata: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> List[Artifact]:
        """
        Create a new artifact
        Args:
            artifact_type: Artifact type (enum or string)
            artifact_id: Optional artifact ID (will be generated if not provided)
            content: Artifact content
            metadata: Metadata dictionary
            novel_file_path: Path to the novel file (for NOVEL type)
        Returns:
            List of created artifact objects
        """
        # If a string is passed, convert to enum type
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)

        # Create new artifacts
        artifacts = []
        artifact = None

        # Ensure metadata is a dictionary
        if metadata is None:
            metadata = {}
        
        # Ensure artifact_id is a valid string
        if artifact_id is None:
            artifact_id = str(uuid.uuid4())

        if artifact_type == ArtifactType.CODE:
            artifacts = CodeArtifact.from_code_content(artifact_type, content)
        elif artifact_type == ArtifactType.NOVEL:
            novel_file_path = kwargs.get('novel_file_path')
            if not novel_file_path:
                raise ValueError("novel_file_path must be provided for NOVEL artifact type")
            artifact = NovelArtifact.from_novel_file_path(
                artifact_type=artifact_type,
                novel_file_path=novel_file_path,
                metadata=metadata,
                artifact_id=artifact_id
            )
        elif artifact_type == ArtifactType.ARXIV:
            if 'arxiv_id' not in kwargs:
                raise ValueError("arxiv_id must be provided for ARXIV artifact type")
            artifact = ArxivArtifact.from_arxiv_id(
                arxiv_id_or_url=kwargs.get('arxiv_id'),
                page_count=kwargs.pop('page_count', -1),
                metadata=metadata,
                artifact_id=artifact_id,
                **kwargs
            )

        else:
            artifact = Artifact(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                content=content,
                metadata=metadata
            )


        if artifact:
            await self.add_artifact(artifact)

            # Create async task for post-processing
            await self.process_artifact(artifact)
            return [artifact]
        
        if artifacts:
            for artifact in artifacts:
                await self.add_artifact(artifact)
                # Create async task for post-processing
                await self.process_artifact(artifact)
            

        return artifacts

    async def process_artifact(self, artifact: Artifact) -> None:

        async def _process_artifact():
            """Process artifact and update workspace"""
            try:
                logger.info(f"📦[POST-PROCESSING]🔄 process_artifact[{artifact.artifact_type}]:{artifact.artifact_id} started")
                # Process the artifact
                await artifact.post_process()
                
                # Update workspace with processed artifact
                await self._store_artifact(artifact)
                
                logger.info(f"📦[POST-PROCESSING]✅ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} finished")
                
                # Update workspace timestamp
                self.updated_at = datetime.now().isoformat()
                
                # Notify observers about the update
                logger.info(f"📦[POST-PROCESSING]🔄 notify_observers[{artifact.artifact_type}]:{artifact.artifact_id} started")
                if hasattr(self, '_notify_observers'):
                    await self._notify_observers("update", artifact)
                                
                logger.info(
                    f"📦[POST-PROCESSING]✅ Successfully processed and updated workspace for artifact: {artifact.artifact_id}"
                )   
                
            except Exception as e:
                logger.error(f"📦[POST-PROCESSING]❌ process_artifact[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}, traceback is {traceback.format_exc()}")
                
                # Mark artifact as error state
                if hasattr(artifact, 'status'):
                    from workspacex.artifact import ArtifactStatus
                    artifact.status = ArtifactStatus.ERROR
                    artifact.update_metadata({'error_info': str(e)})
                    # Try to save error state
                    try:
                        await self._store_artifact(artifact)
                        logger.info(f"📦[POST-PROCESSING]✅ Saved error state for artifact: {artifact.artifact_id}")
                    except Exception as save_error:
                        logger.error(f"📦[POST-PROCESSING]❌ Failed to save error state: {save_error}, traceback is {traceback.format_exc()}")

        logger.debug(f"📦[POST-PROCESSING]🔄 process_artifact[{artifact.artifact_type}]:{artifact.artifact_id} creating async task")
        # Create async task for processing and updating
        asyncio.create_task(_process_artifact())
        logger.info(f"📦[POST-PROCESSING]✅ process_artifact[{artifact.artifact_type}]:{artifact.artifact_id} async task created")


    async def add_artifact(
            self,
            artifact: Artifact
    ) -> None:
        """
        Create a new artifact with thread-safe lock protection

        Args:
            artifact: Artifact

        Returns:
            None
        """
        async with self._save_lock:
            # Check if artifact ID already exists
            existing_artifact = self._get_artifact(artifact.artifact_id)
            if existing_artifact:
                await self._update_artifact(artifact)
                await self._notify_observers("update", artifact)
            else:
                # Add to workspace
                self.artifacts.append(artifact)

                await self._notify_observers("create", artifact)

            # Store in repository
            await self._store_artifact(artifact)

            # Update workspace time
            self.updated_at = datetime.now().isoformat()
        
        # 锁释放后，再调用 save() 避免死锁
        await self.save()


    async def _update_artifact(self, artifact: Artifact) -> None:
        """
        Update artifact in the artifacts list with thread-safe lock protection
        
        Args:
            artifact: Artifact to update
            
        Returns:
            None
        """
        for i, a in enumerate(self.artifacts):
            if a.artifact_id == artifact.artifact_id:
                self.artifacts[i] = artifact
                logger.info(f"[📂WORKSPACEX]🔄 Updating artifact in repository: {artifact.artifact_id}")
                break

    async def update_artifact(
            self,
            artifact_id: str,
            content: Any,
            description: str = "Content update"
    ) -> Optional[Artifact]:
        """
        Update artifact content with thread-safe lock protection
        
        Args:
            artifact_id: Artifact ID
            content: New content
            description: Update description
            
        Returns:
            Updated artifact, or None if it doesn't exist
        """
        async with self._save_lock:
            artifact = self._get_artifact(artifact_id)
            if artifact:
                artifact.update_content(content, description)

                # Update storage
                await self._store_artifact(artifact)

                # Update workspace time
                self.updated_at = datetime.now().isoformat()

                # Notify observers
                await self._notify_observers("update", artifact)

                return artifact
            return None
    
    async def update_artifact_metadata(self, artifact: Artifact, metadata: Dict[str, Any]) -> bool:
        """
        Update artifact metadata with thread-safe lock protection
        """
        async with self._save_lock:
            if artifact.parent_id:
                parent_artifact = self._get_artifact(artifact.parent_id)
                if parent_artifact:
                    for sub_artifact in parent_artifact.sublist:
                        if sub_artifact.artifact_id == artifact.artifact_id:
                            sub_artifact.update_metadata(metadata)
                            self.repository.store_artifact(parent_artifact, save_sub_list_content=False)
                            return True
            else:
                artifact.update_metadata(metadata)
                self.repository.store_artifact(artifact, save_sub_list_content=False)
            return True

    async def save_artifact(self, artifact: Artifact, save_sub_list_content=False):
        self.repository.store_artifact(artifact, save_sub_list_content=save_sub_list_content)

    async def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete an artifact from the workspace with thread-safe lock protection
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            Whether deletion was successful
        """
        async with self._save_lock:
            for i, artifact in enumerate(self.artifacts):
                if artifact.artifact_id == artifact_id:
                    # Mark as archived
                    artifact.archive()
                    # Store the archived state
                    await self._store_artifact(artifact)
                    # Remove from list
                    self.artifacts.pop(i)

                    # Update workspace time
                    self.updated_at = datetime.now().isoformat()
            
            # 锁释放后，再调用 save() 避免死锁
            await self.save()

            # Notify observers
            await self._notify_observers("delete", artifact)
            return True
        return False
    
    async def _store_artifact(self, artifact: Artifact) -> None:
        """Store artifact in repository"""
        try:
            # Create semaphore to limit concurrent operations (default: 10)
            max_concurrent = getattr(self.workspace_config, 'max_concurrent_embeddings', 10)
            semaphore = asyncio.Semaphore(max_concurrent)

            # Process main artifact and subartifacts in parallel for maximum concurrency
            tasks = [self._store_artifact_chunk_and_embedding_with_semaphore(artifact, semaphore)]

            if artifact.sublist and len(artifact.sublist) > 0:
                # Add subartifacts to parallel processing
                sub_tasks = [self._store_artifact_chunk_and_embedding_with_semaphore(subartifact, semaphore)
                             for subartifact in artifact.sublist]
                tasks.extend(sub_tasks)
                logger.info(
                    f"🚀 Processing {len(tasks)} artifacts in parallel (1 main + {len(sub_tasks)} subartifacts) with max {max_concurrent} concurrent operations")

            # Execute all embedding tasks in parallel with error handling
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any errors that occurred during parallel processing
            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.error(f"❌ {len(errors)} errors occurred during parallel :")
                for error in errors:
                    logger.error(f"[Workspace]- {type(error).__name__}: {error}")
            else:
                logger.info(f"✅ All {len(tasks)} artifacts processed successfully in parallel")
        finally:
            # save artifact
            self.repository.store_artifact(artifact=artifact)
            logger.info(f"📦[CONTENT] store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} content finished")

    async def _store_artifact_chunk_and_embedding_with_semaphore(self, artifact: Artifact, semaphore: asyncio.Semaphore) -> None:
        """Store artifact embedding with concurrency control"""
        async with semaphore:
            return await self._chunk_and_embedding(artifact)

    async def _chunk_and_embedding(self, artifact: Artifact) -> None:
        """Store artifact embedding"""

        # if chunking is enabled, chunk the artifact first
        chunks = []
        if self.workspace_config.chunk_config.enabled and artifact.support_chunking:
            chunks = await self._chunk_artifact(artifact)
            if not chunks:
                return
        index_tasks = [self._rebuild_artifact_embedding(artifact, chunks), self._rebuild_artifact_fulltext(artifact, chunks)]
        await asyncio.gather(*index_tasks)

    async def _chunk_artifact(self, artifact: Artifact) -> Optional[list[Chunk]]:
        """Chunk artifact"""
        chunker = self.get_chunker_by_artifact(artifact)
        if chunker:
            try:
                chunks = await chunker.chunk(artifact)
                artifact.mark_chunkable()
                logger.info(f"📦[CHUNKING]✅ store_artifact_chunk[{artifact.artifact_type}]:{artifact.artifact_id} chunks size: {len(chunks)}")
                
                if chunks:
                    await self.save_artifact_chunks(artifact, chunks)
                    artifact.after_chunker()
                    return chunks
                else:
                    logger.info(f"📦[CHUNKING] store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} chunks is empty")
                    return []
            except Exception as e:
                logger.error(f"📦[CHUNKING] store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}\n traceback is {traceback.format_exc()}")
                raise
        else:
            return []

    def get_chunker_by_artifact(self, artifact):
        if hasattr(artifact, "chunker"):
            return artifact.chunker
        return self.chunker

    async def rebuild_index(self):
        await self.rebuild_fulltext()
        await self.rebuild_embedding()

    async def rebuild_embedding(self):
        for artifact in tqdm(self.artifacts, desc="workspace_rebuild_embedding"):
            await self.rebuild_artifact_embedding(artifact)

    async def rebuild_artifact_index(self, artifact: Artifact):
       logger.info(f"📦[REBUILD_ARTIFACT_INDEX]✅ start rebuild_artifact_index ->[{artifact.artifact_type}]:{artifact.artifact_id}")
       # rebuild [CHUNK -> embedding]
       # rebuild [      -> fulltext]
       await self._chunk_and_embedding(artifact)

       # rebuild sub_list
       for sub_artifact in tqdm(artifact.sublist, f"[{artifact.artifact_id}-SUBLIST]rebuild_artifact_index"):
           await self.rebuild_artifact_index(sub_artifact)

       logger.info(f"📦[REBUILD_ARTIFACT_INDEX]✅ rebuild_artifact_index finished -> [{artifact.artifact_type}]:{artifact.artifact_id} ")

    async def rebuild_artifact_embedding(self, artifact: Artifact):
        await self._rebuild_artifact_embedding(artifact)
        for sub_artifact in tqdm(artifact.sublist, f"artifact_rebuild_embedding_sublist#{artifact.artifact_id}"):
            await self._rebuild_artifact_embedding(sub_artifact)

    async def _rebuild_artifact_embedding(self, artifact: Artifact, chunks: list[Chunk] = None):
        if not self.workspace_config.embedding_config.enabled:
            return

        self.vector_db.delete(self.default_vector_collection, filter={"artifact_id": artifact.artifact_id})
        logger.info(f"📦[EMBEDDING]✅ delete_embeddings[{artifact.artifact_type}]:{artifact.artifact_id} finished")

        chunkable = artifact.get_metadata_value("chunkable")
        if chunkable:
            if not chunks:
                chunks = await self._load_artifact_chunks(artifact)
            if chunks:
                embedding_results = await self.embedder.async_embed_chunks(chunks)
                await asyncio.to_thread(self.vector_db.insert, self.default_vector_collection, embedding_results)
                logger.info(
                    f"📦[EMBEDDING-CHUNKING]✅ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} embedding_result finished")
        else:
            # if embedding is not enabled, skip
            if not artifact.get_embedding_text():
                logger.info(
                    f"📦[EMBEDDING]❌ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} embedding is not enabled or embedding_text is empty")
                return
            try:
                embedding_result = await asyncio.to_thread(self.embedder.embed_artifact, artifact)
                await asyncio.to_thread(self.vector_db.insert, self.default_vector_collection, [embedding_result])
                logger.info(
                    f"📦[EMBEDDING]✅ store_artifact(unchunkable)[{artifact.artifact_type}]:{artifact.artifact_id} embedding_result finished")
            except Exception as e:
                logger.error(
                    f"📦[EMBEDDING]❌ store_artifact(unchunkable)[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}")
                raise

    async def _load_artifact_chunks(self, artifact: Artifact) -> Optional[list[Chunk]]:
        return self.repository.get_chunks(artifact.artifact_id, artifact.parent_id)
    
    async def save_artifact_chunks(self, artifact: Artifact, chunks: List[Chunk]) -> None:
        """Save artifact chunks"""
        self.repository.store_artifact_chunks(artifact, chunks)

    async def _store_artifact_fulltext(self, artifact: Artifact, chunks: List[Chunk] = None) -> None:
        """Store artifact content in full-text search database.
        
        Args:
            artifact (Artifact): The artifact to store
            chunks (List[Chunk], optional): Chunks of the artifact. If None, uses the artifact's content directly.
        """
        if not self.fulltext_db:
            return
        if not chunks:
            return
            
        try:
            documents = []

            # default use origin text
            if chunks and self.workspace_config.fulltext_db_config.config.get('use_chunk', True):
                # Store each chunk as a separate document
                for chunk in chunks:
                    doc = {
                        "id": chunk.chunk_id,
                        "content": chunk.content,
                        "artifact_id": artifact.artifact_id,
                        "chunk_id": chunk.chunk_id,
                        "metadata": {
                            "artifact_type": artifact.artifact_type.value,
                            "chunk_index": chunk.chunk_metadata.chunk_index,
                            "chunk_size": chunk.chunk_metadata.chunk_size,
                            "chunk_overlap": chunk.chunk_metadata.chunk_overlap,
                            **chunk.chunk_metadata.model_dump()
                        },
                        "created_at": artifact.created_at,
                        "updated_at": artifact.updated_at
                    }
                    documents.append(doc)
            else:
                # Store the entire artifact as a single document
                content = artifact.get_embedding_text()
                if content:
                    doc = {
                        "id": artifact.artifact_id,
                        "content": content,
                        "artifact_id": artifact.artifact_id,
                        "metadata": {
                            "artifact_type": artifact.artifact_type.value,
                            "content_size": len(content),
                            **artifact.metadata
                        },
                        "created_at": artifact.created_at,
                        "updated_at": artifact.updated_at
                    }
                    documents.append(doc)
            
            if documents:
                await asyncio.to_thread(self.fulltext_db.insert, self.full_text_index, documents)
                logger.info(f"📦[FULLTEXT]✅ store_fulltext[{artifact.artifact_type}]:{artifact.artifact_id} finished, {len(documents)} documents")
            else:
                logger.warning(f"📦[FULLTEXT]⚠️ store_fulltext[{artifact.artifact_type}]:{artifact.artifact_id} no content to store")
                
        except Exception as e:
            logger.error(f"📦[FULLTEXT]❌ store_fulltext[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}")
            raise


    async def _rebuild_artifact_fulltext(self, artifact: Artifact, chunks: List[Chunk] = None) -> None:
        """Store artifact content in full-text search database.
        
        This is a public method that can be called independently to store artifacts
        in the full-text search database without rebuilding embeddings.
        
        Args:
            artifact (Artifact): The artifact to store
            chunks (List[Chunk], optional): Chunks of the artifact. If None, uses the artifact's content directly.
        """
        if not self.fulltext_db:
            logger.warning(f"📦[FULLTEXT]⚠️ fulltext_db is not enabled for artifact {artifact.artifact_id}")
            return
            
        # Delete existing full-text data for this artifact
        self.fulltext_db.delete(self.full_text_index, filter={"artifact_id": artifact.artifact_id})
        logger.info(f"📦[FULLTEXT]✅ delete_fulltext[{artifact.artifact_type}]:{artifact.artifact_id} finished")
        chunkable = artifact.get_metadata_value("chunkable")
        if chunkable and self.workspace_config.fulltext_db_config.config.get('use_chunk', True):
            if not chunks:
                chunks = await self._load_artifact_chunks(artifact)
        await self._store_artifact_fulltext(artifact, chunks)

    async def delete_artifact_fulltext(self, artifact_id: str) -> None:
        """Delete artifact content from full-text search database.
        
        Args:
            artifact_id (str): The artifact ID to delete
        """
        if not self.fulltext_db:
            return
            
        try:
            self.fulltext_db.delete(self.workspace_id, filter={"artifact_id": artifact_id})
            logger.info(f"📦[FULLTEXT]✅ delete_fulltext for artifact_id: {artifact_id} finished")
        except Exception as e:
            logger.error(f"📦[FULLTEXT]❌ delete_fulltext for artifact_id: {artifact_id} failed: {e}")
            raise

    async def rebuild_fulltext(self) -> None:
        """Rebuild full-text search index for all artifacts or a specific artifact.
        
        Args:
            artifact (Artifact, optional): Specific artifact to rebuild. If None, rebuilds all artifacts.
        """
        if not self.fulltext_db:
            logger.warning("📦[FULLTEXT]⚠️ fulltext_db is not enabled")
            return

        try:
            # Rebuild for all artifacts
            logger.info("📦[FULLTEXT]🔄 rebuilding fulltext for all artifacts")
            for artifact in self.artifacts:
                await self.rebuild_artifact_fulltext(artifact)
            logger.info("📦[FULLTEXT]✅ rebuild_fulltext completed for all artifacts")

        except Exception as e:
            logger.error(f"📦[FULLTEXT]❌ rebuild_fulltext failed: {e}")
            raise

    async def rebuild_artifact_fulltext(self, artifact: Artifact):
        await self._rebuild_artifact_fulltext(artifact)
        for sub_artifact in tqdm(artifact.sublist, f"rebuild_artifact_fulltext_sublist#{artifact.artifact_id}"):
            if not sub_artifact.content:
                sub_artifact.content = self._get_file_content_by_artifact_id(artifact_id=sub_artifact.artifact_id, parent_id=artifact.artifact_id)
            await self._rebuild_artifact_fulltext(sub_artifact)

    #########################################################
    # Artifact Retrieval
    #########################################################
    @property
    def total_artifacts(self):
        results = []
        for artifact in self.artifacts:
            results += [artifact]
            if artifact.sublist:
                results += artifact.sublist
        return results

    def list_artifacts(self, artifact_ids: Optional[List[str]] = None, filter_types: Optional[List[ArtifactType]] = None, sublist=False) -> List[Artifact]:
        """
        List all artifacts in the workspace
        
        Args:
            filter_type: Optional filter type
            
        Returns:
            List of artifacts
        """
        if artifact_ids:
            return [a for a in self.artifacts if a.artifact_id in artifact_ids]
        if filter_types:
            return [a for a in self.artifacts if a.artifact_type in filter_types]
        if not sublist:
            return [a for a in self.artifacts]
        return self.total_artifacts


    
    def get_artifact(self, artifact_id: str, parent_id: str = None, load_content:bool = True, load_summary = True) -> Optional[Artifact]:
        """
        Get an artifact by its ID
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            Artifact object if found, None otherwise
        """
        if parent_id:
            parent_artifact = self.get_artifact(artifact_id=parent_id)
            if parent_artifact:
                if not parent_artifact.sublist:
                    return None
                for sub_artifact in parent_artifact.sublist:
                    if sub_artifact.artifact_id == artifact_id:
                        if load_content:
                            sub_artifact.content = self.repository.get_subaritfact_content(artifact_id, parent_id)
                        if load_summary:
                            if self.vector_db:
                                summary_result = self.vector_db.query(self.summary_vector_collection, filter={
                                    "artifact_id": sub_artifact.artifact_id
                                })
                                if summary_result and len(summary_result.docs) > 0:
                                    sub_artifact.summary = summary_result.docs[0].content
                        return sub_artifact
                return None

        return self._get_artifact(artifact_id)

    def get_next_artifact(self, artifact_id: str) -> Optional[Artifact]:
        for i, artifact in enumerate(self.artifacts):
            if artifact.artifact_id == artifact_id:
                if i + 1 >= len(self.artifacts):
                    return None
                return self.artifacts[i + 1]
            if artifact.sublist:
                for si, sub_artifact in enumerate(artifact.sublist):
                    if sub_artifact.artifact_id == artifact_id:
                        if si + 1 >= len(artifact.sublist):
                            return None
                        return artifact.sublist[si + 1]
        return None

    def get_pre_artifact(self, artifact_id: str) -> Optional[Artifact]:
        for i, artifact in enumerate(self.artifacts):
            if artifact.artifact_id == artifact_id:
                if i - 1 < 0:
                    return None
                return self.artifacts[i - 1]
            if artifact.sublist:
                for si,sub_artifact in enumerate(artifact.sublist):
                    if sub_artifact.artifact_id == artifact_id:
                        if si - 1 < 0:
                            return None
                        return artifact.sublist[si - 1]

        return None

    def _get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
            if artifact.sublist:
                for sub_artifact in artifact.sublist:
                    if sub_artifact.artifact_id == artifact_id:
                        return sub_artifact
        return None
    
    def get_file_content_by_artifact_id(self, artifact_id: str, parent_id: str = None) -> Optional[str]:
        """
        Get concatenated content of all artifacts with the same filename.

        Args:
            artifact_id: artifact_id

        Returns:
            Raw unescaped concatenated content of all matching artifacts
        """
        artifact = self._get_artifact(artifact_id)
        if not artifact:
            return None
        return self._get_file_content_by_artifact_id(artifact.artifact_id, artifact.parent_id)

    def _get_file_content_by_artifact_id(self, artifact_id: str, parent_id: str = None) -> Optional[str]:
        if parent_id:
            return self.repository.get_subaritfact_content(artifact_id, parent_id)
        else:
            return None

    async def get_attachment_file_stream(self, artifact_id: str, file_name: str) -> Optional[bytes]:
        """
        获取指定artifact的附件文件内容（二进制数据）

        Args:
            artifact_id (str): artifact的ID
            file_name (str): 附件文件名

        Returns:
            Optional[bytes]: 附件文件内容（二进制数据），如果不存在则返回None
        """
        # ⚡️支持并发调用
        logger.info(f"📎 get_attachment_file_stream: artifact_id={artifact_id}, file_name={file_name}")
        return self.repository.get_attachment_file(artifact_id, file_name)
    
    async def get_attachment_file_path(self, artifact_id: str, file_name: str) -> Optional[str]:
        """
        获取指定artifact的附件文件路径（用于流式传输）

        Args:
            artifact_id (str): artifact的ID
            file_name (str): 附件文件名

        Returns:
            Optional[str]: 附件文件路径，如果不存在则返回None
        """
        # ⚡️支持并发调用
        logger.info(f"📎 get_attachment_file_path: artifact_id={artifact_id}, file_name={file_name}")
        return self.repository.get_attachment_file_path(artifact_id, file_name)
    
    def get_storage_type(self) -> str:
        """
        获取存储类型
        
        Returns:
            str: 存储类型 ("local" 或 "s3" 等)
        """
        if hasattr(self.repository, '__class__'):
            repo_class_name = self.repository.__class__.__name__.lower()
            if 'local' in repo_class_name:
                return "local"
            elif 's3' in repo_class_name:
                return "s3"
            else:
                return "unknown"
        return "unknown"
    
    async def get_attachment_file_stream_chunks(self, artifact_id: str, file_name: str):
        """
        获取指定artifact的附件文件流式数据块（支持S3等远程存储）

        Args:
            artifact_id (str): artifact的ID
            file_name (str): 附件文件名

        Yields:
            bytes: 文件数据块
        """
        # ⚡️支持并发调用
        logger.info(f"📎 get_attachment_file_stream_chunks: artifact_id={artifact_id}, file_name={file_name}")
        
        # 根据存储类型选择不同的流式读取方式
        storage_type = self.get_storage_type()
        
        if storage_type == "local":
            # 本地存储：使用文件流
            file_path = await self.get_attachment_file_path(artifact_id, file_name)
            if file_path and os.path.exists(file_path):
                import aiofiles
                async with aiofiles.open(file_path, 'rb') as f:
                    chunk_size = 64 * 1024  # 64KB chunks
                    while True:
                        chunk = await f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
        else:
            # S3 或其他远程存储：使用 repository 的流式读取
            async for chunk in self.repository.get_attachment_file_stream_chunks(artifact_id, file_name):
                yield chunk
    
    #########################################################
    # Hybrid Search
    #########################################################


    async def retrieve_artifacts(self, search_query: HybridSearchQuery) -> Optional[list[HybridSearchResult]]:
        """
        Retrieve an artifact by its ID

        Args:
            query: Query string
            filter_types: Optional filter types

        Returns:
            Artifact object if found, None otherwise
        """
        logger.info(f"🔍 retrieve_artifact search_query: {search_query}")

        if not self.workspace_config.hybrid_search_config.enabled:
            return []

        if not search_query:
            logger.warning("🔍 retrieve_artifact search_query is None")
            return None

        if not search_query.limit:
            search_query.limit = self.workspace_config.hybrid_search_config.top_k

        if not search_query.threshold:
            search_query.threshold = self.workspace_config.hybrid_search_config.threshold
        logger.debug(f"🔍 retrieve_artifact final search_query: {search_query}")

        candidate_results = []

        # Execute vector and fulltext search concurrently
        vector_task = asyncio.create_task(self._vector_search_artifacts(search_query))
        vector_summary_task = asyncio.create_task(self._vector_search_artifacts_by_summary(search_query))
        fulltext_task = asyncio.create_task(self._fulltext_search_artifacts(search_query))

        vector_results, fulltext_results,  vector_summary_results = await asyncio.gather(vector_task, fulltext_task, vector_summary_task)

        if vector_results:
            candidate_results += [vector_result.artifact for vector_result in vector_results]
            logger.info(f"🔍 retrieve_artifact vector_results size: {len(vector_results)}")
            for item in vector_results:
                logger.debug(f"🔍 retrieve_artifact vector_results item: {item.artifact.artifact_id}: {item.score}")

        if vector_summary_results:
            candidate_results += [vector_summary_result.artifact for vector_summary_result in vector_summary_results]
            logger.info(f"🔍 retrieve_artifact vector_results size: {len(vector_summary_results)}")
            for item in vector_summary_results:
                logger.debug(f"🔍 retrieve_artifact vector_results item: {item.artifact.artifact_id}: {item.score}")

        if fulltext_results:
            candidate_results += [fulltext_result.artifact for fulltext_result in fulltext_results]
            logger.info(f"🔍 retrieve_artifact fulltext_results size: {len(fulltext_results)}")
            for item in fulltext_results:
                logger.debug(f"🔍 retrieve_artifact fulltext_results item: {item.artifact.artifact_id}: {item.score}")

        if fulltext_results:
            candidate_results += [fulltext_result.artifact for fulltext_result in fulltext_results]
            logger.info(f"🔍 retrieve_artifact fulltext_results size: {len(fulltext_results)}")
            for item in fulltext_results:
                logger.debug(f"🔍 retrieve_artifact fulltext_results item: {item.artifact.artifact_id}: {item.score}")

        logger.info(f"🔍 retrieve_artifact candidate_results size: {len(candidate_results)}")
        rerank_results = await self._rerank_candidate_artifacts(search_query.query,candidate_results)
        for item in rerank_results:
            logger.debug(f"🔍 retrieve_artifact rerank_results item: {item.artifact.artifact_id}: {item.score}")

        # Convert rerank results to HybridSearchResults and limit to requested size
        results = [
            HybridSearchResult(artifact=result.artifact, score=result.score)
            for result in rerank_results[:search_query.limit]
        ]

        logger.info(f"🔍 retrieve_artifact results size: {len(results)}")
        return results

    async def _fulltext_search_chunks(self, search_query: ChunkSearchQuery) -> Dict[str, Chunk]:
        if not self.fulltext_db:
            return {}
        fulltext_search_results = await asyncio.to_thread(
            self.fulltext_db.search,
            self.full_text_index, search_query.query,
            filter=search_query.filters, limit=search_query.limit
        )
        chunks = {}
        if fulltext_search_results and fulltext_search_results.results:
            for result in fulltext_search_results.results:
                if result.chunk_id and result.chunk_id not in chunks:
                    metadata = result.metadata or {}
                    chunk_metadata_obj = ChunkMetadata(
                        chunk_index=metadata.get('chunk_index'),
                        parent_artifact_id=metadata.get('parent_artifact_id'),
                        chunk_size=metadata.get('chunk_size'),
                        chunk_overlap=metadata.get('chunk_overlap'),
                        artifact_id=metadata.get('artifact_id'),
                        artifact_type=metadata.get('artifact_type'),
                    )
                    chunk = Chunk(
                        chunk_id=result.chunk_id,
                        content=result.content,
                        chunk_metadata=chunk_metadata_obj
                    )
                    chunks[result.chunk_id] = chunk
        return chunks

    async def _vector_search_chunks(self, search_query: ChunkSearchQuery) -> Dict[str, Chunk]:
        chunk_query_embedding = self.embedder.embed_query(search_query.query)
        vector_search_results = await asyncio.to_thread(
            self.vector_db.search, self.default_vector_collection, [chunk_query_embedding],
            filter=search_query.filters, threshold=search_query.threshold, limit=search_query.limit
        )
        chunks = {}
        if vector_search_results and vector_search_results.docs:
            for doc in vector_search_results.docs:
                if doc.metadata and doc.metadata.chunk_id and doc.metadata.chunk_id not in chunks:
                    chunk_metadata_obj = ChunkMetadata(
                        chunk_index=doc.metadata.chunk_index,
                        parent_artifact_id=doc.metadata.parent_id,
                        chunk_size=doc.metadata.chunk_size,
                        chunk_overlap=doc.metadata.chunk_overlap,
                        artifact_id=doc.metadata.artifact_id,
                        artifact_type=doc.metadata.artifact_type
                    )
                    chunk = Chunk(
                        chunk_id=doc.metadata.chunk_id,
                        content=doc.content,
                        chunk_metadata=chunk_metadata_obj
                    )
                    chunks[doc.metadata.chunk_id] = chunk
        return chunks

    async def retrieve_chunk(self, search_query: ChunkSearchQuery) -> Optional[List[ChunkSearchResult]]:
        """
        Hybrid retrieval with fallback mechanism (z)
        1. Parallel vector and fulltext search
        2. Combine and deduplicate results
        3. Rerank with error handling and fallback
        4. Get context window for final results
        
        Args:
            search_query: Search query parameters
            
        Returns:
            List of chunk search results with context windows
            
        """
        # 1. Vector and Full-text search in parallel (z)
        fulltext_task = self._fulltext_search_chunks(search_query)
        vector_task = self._vector_search_chunks(search_query)

        fulltext_chunks, vector_chunks = await asyncio.gather(
            fulltext_task, vector_task
        )
        logger.info(f"🔍 retrieve_chunk vector_search_chunks: {len(vector_chunks.keys())}")
        logger.info(f"🔍 retrieve_chunk fulltext_search_chunks: {len(fulltext_chunks.keys())}")

        # 2. & 3. Combine and deduplicate chunks for reranking (z)
        combined_chunks: Dict[str, Chunk] = {}
        combined_chunks.update(fulltext_chunks)
        for chunk_id, chunk in vector_chunks.items():
            if chunk_id not in combined_chunks:
                combined_chunks[chunk_id] = chunk
        
        logger.info(f"🔍 retrieve_chunk combined_chunks final size: {len(combined_chunks)}")

        if not combined_chunks:
            return []

        # Helper function for fallback to vector search results (z)
        async def _fallback_to_vector_search() -> List[ChunkSearchResult]:
            """Fallback mechanism when reranker is not available or fails (z)"""
            logger.warning("🔄 Using fallback to vector search results")
            results = []
            # Use vector search results as fallback
            vector_search_results = await self._vector_search_chunks(search_query)
            if not vector_search_results:
                return []
            
            # Convert chunks to search results with context window
            for chunk in list(vector_search_results.values())[:search_query.limit]:
                pre_n_chunks, chunk_obj, next_n_chunks = await asyncio.to_thread(
                    self.repository.get_chunk_window, 
                    chunk.chunk_metadata.artifact_id, 
                    chunk.chunk_metadata.parent_artifact_id,
                    chunk.chunk_metadata.chunk_index, 
                    search_query.pre_n, 
                    search_query.next_n
                )
                if chunk_obj:
                    results.append(ChunkSearchResult(
                        pre_n_chunks=pre_n_chunks, 
                        chunk=chunk_obj,
                        next_n_chunks=next_n_chunks, 
                        score=1.0  # Default score for fallback
                    ))
            return results

        # Fallback to vector search if reranker is not available (z)
        if not self.reranker:
            logger.warning("⚠️ Reranker is not available, using fallback mechanism")
            return await _fallback_to_vector_search()

        # 4. Rerank with error handling and fallback (z)
        try:
            artifacts_to_rerank = [
                Artifact(
                    artifact_id=chunk.chunk_id, content=chunk.content,
                    artifact_type=ArtifactType.TEXT, metadata={'original_chunk': chunk}
                ) for chunk in combined_chunks.values()
            ]

            reranked_results = await asyncio.to_thread(
                self.reranker.run, search_query.query, artifacts_to_rerank, top_n=search_query.limit
            )

            if not reranked_results:
                logger.warning("⚠️ Rerank returned empty results, using fallback mechanism")
                return await _fallback_to_vector_search()
                
        except Exception as e:
            logger.error(f"❌ Rerank failed with error: {e}, using fallback mechanism")
            return await _fallback_to_vector_search()

        # 5. Get context window for final results and format (z)
        window_fetch_tasks = []
        for rerank_result in reranked_results:
            original_chunk: Chunk = rerank_result.artifact.metadata['original_chunk']
            async def fetch_window(chunk, score):
                pre_n, c, next_n = await asyncio.to_thread(
                    self.repository.get_chunk_window, chunk.chunk_metadata.artifact_id, chunk.chunk_metadata.parent_artifact_id,
                    chunk.chunk_metadata.chunk_index, search_query.pre_n, search_query.next_n
                )
                return ChunkSearchResult(
                    pre_n_chunks=pre_n, chunk=c, next_n_chunks=next_n, score=score
                )
            window_fetch_tasks.append(fetch_window(original_chunk, rerank_result.score))

        return await asyncio.gather(*window_fetch_tasks)

    async def search_fulltext(self, query: str, limit: int = 10, filter_types: Optional[List[ArtifactType]] = None) -> \
    Optional[list[FulltextSearchResult]]:
        """Search artifacts using full-text search only.

        Args:
            query (str): Search query
            limit (int): Maximum number of results
            filter_types (Optional[List[ArtifactType]]): Filter by artifact types

        Returns:
            Optional[list[FulltextSearchResult]]: Search results
        """
        if not self.fulltext_db:
            logger.warning("🔍 search_fulltext fulltext_db is not enabled")
            return None

        try:
            # Build filter for artifact types if specified
            filter_dict = {}
            if filter_types:
                filter_dict["metadata.artifact_type"] = [t.value for t in filter_types]

            # Perform full-text search
            search_results = await asyncio.to_thread(
                self.fulltext_db.search,
                self.full_text_index,
                query,
                filter=filter_dict,
                limit=limit,
                offset=0
            )

            if not search_results:
                logger.info("🔍 search_fulltext no results found")
                return None

            logger.info(f"🔍 search_fulltext found {len(search_results.results)} results")
            return search_results.results

        except Exception as e:
            logger.error(f"🔍 search_fulltext failed: {e}")
            return None

    async def _fulltext_search_artifacts(self, search_query: HybridSearchQuery) -> Optional[list[HybridSearchResult]]:
        """Search artifacts using full-text search.
        
        Args:
            search_query (HybridSearchQuery): Search query
            
        Returns:
            Optional[list[HybridSearchResult]]: Search results
        """
        if not self.fulltext_db:
            return None
            
        try:
            # Build filter for artifact types if specified
            filter_dict = {}
            if search_query.filter_types:
                filter_dict["metadata.artifact_type"] = [t.value for t in search_query.filter_types]
            
            # Perform full-text search
            search_results = await asyncio.to_thread(
                self.fulltext_db.search,
                self.full_text_index,
                search_query.query,
                filter=filter_dict,
                limit=search_query.limit,
                offset=0
            )
            
            if not search_results or not search_results.results:
                logger.info("🔍 _fulltext_search_artifacts no results found")
                return None
            
            results = []
            existing_artifact_ids = []
            
            for result in search_results.results:
                if result.artifact_id in existing_artifact_ids:
                    logger.debug(f"🔍 _fulltext_search_artifacts artifact_id already exists: {result.artifact_id}")
                    continue
                    
                artifact = self.get_artifact(result.artifact_id)
                if not artifact:
                    logger.warning(f"🔍 _fulltext_search_artifacts artifact not found: {result.artifact_id}")
                    continue
                    
                logger.debug(f"🔍 _fulltext_search_artifacts artifact- {artifact.artifact_id} score: {result.score}")
                results.append(HybridSearchResult(artifact=artifact, score=result.score))
                existing_artifact_ids.append(result.artifact_id)
            
            logger.info(f"🔍 _fulltext_search_artifacts found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"🔍 _fulltext_search_artifacts failed: {e}")
            return None

    
    #########################################################
    # Observer Management
    #########################################################

    def add_observer(self, observer: WorkspaceObserver) -> None:
        """
        Add a workspace observer
        
        Args:
            observer: Observer object implementing WorkspaceObserver interface
        """
        if not isinstance(observer, WorkspaceObserver):
            raise TypeError("Observer must be an instance of WorkspaceObserver")
        self.observers.append(observer)

    def remove_observer(self, observer: WorkspaceObserver) -> None:
        """Remove an observer"""
        if observer in self.observers:
            self.observers.remove(observer)

    async def _notify_observers(self, operation: str, artifact: Artifact) -> List[Any]:
        """
        Notify all observers of workspace changes
        
        Args:
            operation: Type of operation (create, update, delete)
            artifact: Affected artifact
            
        Returns:
            List of results from handlers
        """
        results = []
        for observer in self.observers:
            try:
                if operation == "create":
                    result = await observer.on_create(workspace_id=self.workspace_id, artifact=artifact)
                    if result:
                        results.append(result)
                elif operation == "update":
                    result = await observer.on_update(workspace_id=self.workspace_id, artifact=artifact)
                    if result:
                        results.append(result)
                elif operation == "delete":
                    result = await observer.on_delete(workspace_id=self.workspace_id, artifact=artifact)
                    if result:
                        results.append(result)
            except Exception as e:
                print(f"Observer notification failed: {e}")
        return results


    #########################################################
    # Workspace Management
    #########################################################

    async def save(self) -> None:
        """
        Save workspace state with thread-safe lock protection
        
        This method is protected by a threading lock to prevent concurrent access
        from multiple threads that could lead to data corruption or race conditions.
        
        Returns:
            None
        """
        async with self._save_lock:
            workspace_data = {
                "workspace_id": self.workspace_id,
                "name": self.name,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "metadata": self.metadata,
                "artifact_ids": [a.artifact_id for a in self.artifacts],
                "artifacts": [
                    {
                        "artifact_id": a.artifact_id,
                        "type": str(a.artifact_type),
                        "metadata": a.metadata,
                        # "version": a.current_version
                    } for a in self.artifacts
                ]
            }

            logger.info(f"💼 save_workspace {self.workspace_id} start")
            # Store workspace information with workspace_id in metadata
            self.repository.store_index(
                index_data=workspace_data
            )

            logger.info(f"💼 save_workspace {self.workspace_id} finished")

    
    def _load_workspace_data(self) -> Optional[Dict[str, Any]]:
        """
        Load workspace data from index.json and artifacts/{artifact_id}/index.json

        Returns:
            Dictionary containing workspace data if exists, None otherwise
        """
        try:
            # 1. retrieve workspace index.json
            index_data = self.repository.get_index_data()
            if not index_data:
                return None
            workspace_data = index_data.get("workspace")
            if not workspace_data:
                return None

            # 2. retrieve all artifacts 
            artifacts = []
            for artifact_meta in workspace_data.get("artifacts", []):
                artifact_id = artifact_meta.get("id") or artifact_meta.get("artifact_id")
                if not artifact_id:
                    continue
                artifact_data = self.repository.retrieve_artifact(artifact_id)
                from workspacex.artifacts.factory import ArtifactFactory
                artifact = ArtifactFactory.from_dict(artifact_data)
                if not artifact:
                    continue
                artifacts.append(artifact)

            return {
                "artifacts": artifacts,
                "metadata": workspace_data.get("metadata", {}),
                "created_at": workspace_data.get("created_at"),
                "updated_at": workspace_data.get("updated_at")
            }
        except Exception as e:
            traceback.print_exc()
            print(f"Error loading workspace data: {e}")
            return None
        
    def generate_tree_data(self) -> Dict[str, Any]:
        """
        Generate a tree structure based on artifacts and their sublist recursively.
        Returns:
            A dictionary representing the artifact tree.
        """
        def build_node(artifact, parent_id="-1", depth=1):
            node = {
                "name": artifact.metadata.get('filename', artifact.artifact_id),
                "id": artifact.artifact_id,
                "type": str(artifact.artifact_type),
                "artifactId": artifact.artifact_id,
                "parentId": parent_id,
                "depth": depth,
                "expanded": False,
                "children": []
            }
            for sub in getattr(artifact, 'sublist', []):
                node["children"].append(build_node(sub, parent_id=artifact.artifact_id, depth=depth+1))
            return node

        root = {
            "name": self.name,
            "id": "-1",
            "type": "workspace",
            "children": [build_node(artifact) for artifact in self.artifacts]
        }
        return root
