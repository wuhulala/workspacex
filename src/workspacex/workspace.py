import asyncio
import os
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict
from tqdm import tqdm

from workspacex.artifact import ArtifactType, Artifact, Chunk, ChunkSearchQuery, ChunkSearchResult, HybridSearchResult, \
    HybridSearchQuery
from workspacex.base import WorkspaceConfig
from workspacex.chunk.base import ChunkerFactory
from workspacex.code_artifact import CodeArtifact
from workspacex.embedding.base import EmbeddingFactory
from workspacex.fulltext.dbs.base import FulltextDB, FulltextSearchResult
from workspacex.fulltext.factory import FulltextDBFactory
from workspacex.noval_artifact import NovelArtifact
from workspacex.observer import WorkspaceObserver, get_observer
from workspacex.reranker.base import RerankResult
from workspacex.reranker.factory import RerankerFactory
from workspacex.storage.base import BaseRepository
from workspacex.storage.local import LocalPathRepository
from workspacex.utils.logger import logger
from workspacex.vector.dbs.base import VectorDB
from workspacex.vector.factory import VectorDBFactory


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
        
        if clear_existing:
            if self.vector_db:
                self.vector_db.delete(self.workspace_id)
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
            novel_file_path: Optional[str] = None
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
            if not novel_file_path:
                raise ValueError("novel_file_path must be provided for NOVEL artifact type")
            artifact = NovelArtifact(
                artifact_type=artifact_type,
                novel_file_path=novel_file_path,
                metadata=metadata,
                artifact_id=artifact_id
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
            return [artifact]
        
        if artifacts:
            for artifact in artifacts:
                await self.add_artifact(artifact)

        return artifacts

    async def add_artifact(
            self,
            artifact: Artifact
    ) -> None:
        """
        Create a new artifact

        Args:
            artifact: Artifact

        Returns:
            List of created artifact objects
        """
        # Check if artifact ID already exists
        existing_artifact = self._get_artifact(artifact.artifact_id)
        logger.info(f"🔍 add_artifact {artifact.artifact_id} {existing_artifact}")
        if existing_artifact:
            raise ValueError(f"Artifact with ID {artifact.artifact_id} already exists")
        # Add to workspace
        self.artifacts.append(artifact)
        # Store in repository
        await self._store_artifact(artifact)

        # Update workspace time
        self.updated_at = datetime.now().isoformat()

        # Save workspace state to create new version
        self.save()

        await self._notify_observers("create", artifact)

    async def update_artifact(
            self,
            artifact_id: str,
            content: Any,
            description: str = "Content update"
    ) -> Optional[Artifact]:
        """
        Update artifact content
        
        Args:
            artifact_id: Artifact ID
            content: New content
            description: Update description
            
        Returns:
            Updated artifact, or None if it doesn't exist
        """
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
        Update artifact metadata
        """
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

    async def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete an artifact from the workspace
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            Whether deletion was successful
        """
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

                # Save workspace state to create new version
                self.save()

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
        if self.workspace_config.chunk_config.enabled and artifact.support_chunking:
            chunks = await self._chunk_artifact(artifact)
            await self._rebuild_artifact_embedding(artifact, chunks)
            await self._rebuild_artifact_fulltext(artifact, chunks)
        else:
            await self._rebuild_artifact_embedding(artifact)
            await self._rebuild_artifact_fulltext(artifact)

    async def _chunk_artifact(self, artifact: Artifact) -> Optional[list[Chunk]]:
        """Chunk artifact"""
        if self.chunker:
            try:
                chunks = await self.chunker.chunk(artifact)
                artifact.mark_chunkable()
                logger.info(f"📦[CHUNKING]✅ store_artifact_chunk[{artifact.artifact_type}]:{artifact.artifact_id} chunks size: {len(chunks)}")
                
                if chunks:
                    await self.save_artifact_chunks(artifact, chunks)
                    return chunks
                else:
                    logger.info(f"📦[EMBEDDING-CHUNKING]❌ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} chunks is empty")
                    return []
            except Exception as e:
                logger.error(f"📦[CHUNKING]❌ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}\n traceback is {traceback.format_exc()}")
                raise
        else:
            return []

    async def rebuild_embedding(self):
        for artifact in tqdm(self.artifacts, desc="workspace_rebuild_embedding"):
            await self.rebuild_artifact_embedding(artifact)

    async def rebuild_artifact_embedding(self, artifact: Artifact, chunks: list[Chunk] = None):
        await self._rebuild_artifact_embedding(artifact)
        for sub_artifact in tqdm(artifact.sublist, f"artifact_rebuild_embedding_sublist#{artifact.artifact_id}"):
            await self._rebuild_artifact_embedding(sub_artifact)

    async def _rebuild_artifact_embedding(self, artifact: Artifact, chunks: list[Chunk] = None):
        if not self.workspace_config.embedding_config.enabled:
            return

        self.vector_db.delete(self.workspace_id, filter={"artifact_id": artifact.artifact_id})
        logger.info(f"📦[EMBEDDING]✅ delete_embeddings[{artifact.artifact_type}]:{artifact.artifact_id} finished")

        chunkable = artifact.get_metadata_value("chunkable")
        if chunkable:
            if not chunks:
                chunks = await self._load_artifact_chunks(artifact)
            if chunks:
                embedding_results = await self.embedder.async_embed_chunks(chunks)
                await asyncio.to_thread(self.vector_db.insert, self.workspace_id, embedding_results)
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
                await asyncio.to_thread(self.vector_db.insert, self.workspace_id, [embedding_result])
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
            
        try:
            documents = []
            
            if chunks:
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
                await asyncio.to_thread(self.fulltext_db.insert, self.workspace_id, documents)
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
        self.fulltext_db.delete(self.workspace_id, filter={"artifact_id": artifact.artifact_id})
        logger.info(f"📦[FULLTEXT]✅ delete_fulltext[{artifact.artifact_type}]:{artifact.artifact_id} finished")
        chunkable = artifact.get_metadata_value("chunkable")
        if chunkable:
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
            await self._rebuild_artifact_fulltext(sub_artifact)

    #########################################################
    # Artifact Retrieval
    #########################################################

    def list_artifacts(self, filter_types: Optional[List[ArtifactType]] = None) -> List[Artifact]:
        """
        List all artifacts in the workspace
        
        Args:
            filter_type: Optional filter type
            
        Returns:
            List of artifacts
        """
        if filter_types:
            return [a for a in self.artifacts if a.artifact_type in filter_types]
        return self.artifacts
    
    def get_artifact(self, artifact_id: str, parent_id: str = None) -> Optional[Artifact]:
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
                        sub_artifact.content = self.repository.get_subaritfact_content(artifact_id, parent_id)
                        return sub_artifact
                return None

        return self._get_artifact(artifact_id)

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
        return self.repository.get_subaritfact_content(artifact_id, parent_id)
    
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
        fulltext_task = asyncio.create_task(self._fulltext_search_artifacts(search_query))

        vector_results, fulltext_results = await asyncio.gather(vector_task, fulltext_task)

        if vector_results:
            candidate_results += [vector_result.artifact for vector_result in vector_results]
            logger.info(f"🔍 retrieve_artifact vector_results size: {len(vector_results)}")
            for item in vector_results:
                logger.debug(f"🔍 retrieve_artifact vector_results item: {item.artifact.artifact_id}: {item.score}")

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

    async def _rerank_candidate_artifacts(self, user_message: str, candidates: list[Artifact]) -> Optional[list[RerankResult]]:
        # remove duplicate results by artifact_id
        unique_results = {}
        for result in candidates:
            unique_results[result.artifact_id] = result
            if not result.content:
                result.content = self._get_file_content_by_artifact_id(artifact_id=result.artifact_id, parent_id=result.parent_id)

        logger.info(f"🔍 _rerank_candidate_artifacts unique_results: {len(unique_results)}")

        rerank_results = self.reranker.run(user_message, list(unique_results.values()), score_threshold=self.workspace_config.hybrid_search_config.threshold)
        for result in rerank_results:
            logger.debug(f"[rerank_result]: {user_message} artifact: {result.artifact.artifact_id} score: {result.score}")
        return rerank_results

    async def _vector_search_artifacts(self, search_query: HybridSearchQuery) -> Optional[list[HybridSearchResult]]:
        query_embedding = self.embedder.embed_query(search_query.query)
        results = []
        # 2. Search vector db
        search_results = self.vector_db.search(self.workspace_id, [query_embedding], filter={},
                                               threshold=search_query.threshold, limit=search_query.limit)
        if not search_results:
            logger.warning("🔍 retrieve_artifact search_results is None")
            return None

        if not search_results.docs:
            logger.warning("🔍 retrieve_artifact search_results.docs is None")
            return None
        existing_artifact_ids = []

        for doc in search_results.docs:
            if not doc.metadata:
                logger.warning("🔍 retrieve_artifact doc.metadata is None")
                continue
            if doc.metadata.artifact_id in existing_artifact_ids:
                logger.debug(f"🔍 retrieve_artifact artifact_id already exists: {doc.metadata.artifact_id}")
                continue
            artifact = self.get_artifact(doc.metadata.artifact_id, parent_id=doc.metadata.parent_id)
            existing_artifact_ids.append(doc.metadata.artifact_id)
            if not artifact:
                logger.warning(f"🔍 retrieve_artifact artifact is None: {doc.metadata.artifact_id}")
                continue
            logger.debug(f"🔍 retrieve_artifact artifact- {artifact.artifact_id} score: {doc.score}")
            results.append(HybridSearchResult(artifact=artifact, score=doc.score))
        return results
    
    async def retrieve_chunk(self, search_query: ChunkSearchQuery) -> Optional[list[ChunkSearchResult]]:
        """
        Retrieve a chunk by its ID
        """
        logger.info(f"🔍 retrieve_chunk search_query: {search_query}")
        if not self.workspace_config.chunk_config.enabled:
            logger.warning("🔍 retrieve_chunk chunk_config is not enabled")
            return None
        
        results = []
        if not search_query:
            logger.warning("🔍 retrieve_chunk search_query is None")
            return None
        
        if not search_query.limit:
            search_query.limit = 10
        
        if not search_query.threshold:
            search_query.threshold = 0.8
        
        if not search_query.pre_n:
            search_query.pre_n = 3
        
        if not search_query.next_n:
            search_query.next_n = 3

        chunk_query_embedding = self.embedder.embed_query(search_query.query)
        search_results = self.vector_db.search(self.workspace_id, [chunk_query_embedding], filter={}, threshold=search_query.threshold, limit=search_query.limit)
        if not search_results:
            logger.warning("🔍 retrieve_chunk search_results is None")
            return None
        
        if not search_results.docs:
            logger.warning("🔍 retrieve_chunk search_results.docs is None")
            return None
        
        existing_chunk_ids = []
        for doc in search_results.docs:
            if not doc.metadata:
                logger.warning("🔍 retrieve_chunk doc.metadata is None")
                continue
            if doc.metadata.chunk_id in existing_chunk_ids:
                logger.debug(f"🔍 retrieve_chunk chunk_id already exists: {doc.metadata.chunk_id}")
                continue
            pre_n_chunks, chunk, next_n_chunks = self.repository.get_chunk_window(doc.metadata.artifact_id, parent_id = doc.metadata.parent_id, chunk_index=doc.metadata.chunk_index, pre_n=search_query.pre_n, next_n=search_query.next_n)
            if not chunk:
                logger.warning(f"🔍 retrieve_chunk chunk is None: {doc.metadata.chunk_id}")
                continue
            logger.debug(f"🔍 retrieve_chunk chunks- {pre_n_chunks} {chunk} {next_n_chunks} score: {doc.score}")
            results.append(ChunkSearchResult(pre_n_chunks=pre_n_chunks, chunk=chunk, next_n_chunks=next_n_chunks, score=doc.score))

        return results

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
                self.workspace_id,
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
                self.workspace_id,
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

    def save(self) -> None:
        """
        Save workspace state
        
        Returns:
            Workspace storage ID
        """
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

        logger.info(f"💼 save_workspace {self.workspace_id}")
        # Store workspace information with workspace_id in metadata
        self.repository.store_index(
            index_data=workspace_data
        )
    
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
                artifacts.append(Artifact.from_dict(artifact_data))

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
