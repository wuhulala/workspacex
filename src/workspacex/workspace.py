import logging
import os
import traceback
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict

from workspacex.artifact import ArtifactType, Artifact, HybridSearchResult, HybridSearchQuery
from workspacex.base import WorkspaceConfig
from workspacex.embedding.base import EmbeddingFactory, Embeddings
from workspacex.noval_artifact import NovelArtifact
from workspacex.code_artifact import CodeArtifact
from workspacex.storage.base import BaseRepository
from workspacex.storage.local import LocalPathRepository
from workspacex.observer import WorkspaceObserver, get_observer
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
    embedder: Optional[Embeddings] = Field(default=None, description="embedder instance", exclude=True)
    vector_db: Optional[VectorDB] = Field(default=None, description="vector_db instance", exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    
    def __init__(
            self,
            workspace_id: Optional[str] = None,
            name: Optional[str] = None,
            storage_path: Optional[str] = None,
            observers: Optional[List[WorkspaceObserver]] = None,
            use_default_observer: bool = True,
            clear_existing: bool = False,
            repository: Optional[BaseRepository] = None
    ):
        super().__init__()
        self.workspace_id = workspace_id or str(uuid.uuid4())
        self.name = name or f"Workspace-{self.workspace_id[:8]}"
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.workspace_config = WorkspaceConfig()

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

        self.embedder = EmbeddingFactory.get_embedder(self.workspace_config.embedding_config)
        self.vector_db = VectorDBFactory.get_vector_db(self.workspace_config.vector_db_config)
        if clear_existing:
            self.vector_db.delete(self.workspace_id)

    

    @classmethod
    def from_local_storages(cls, workspace_id: Optional[str] = None,
                            name: Optional[str] = None,
                            storage_path: Optional[str] = None,
                            observers: Optional[List[WorkspaceObserver]] = None,
                            use_default_observer: bool = True
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
            clear_existing=False  # Always try to load existing data
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
            novel_file_path: Optional[str] = None,
            embedding_flag: bool = False
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
                artifact_id=artifact_id,
                embedding=embedding_flag
            )
        else:
            artifact = Artifact(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                content=content,
                metadata=metadata,
                embedding=embedding_flag
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
        existing_artifact = self.get_artifact(artifact.artifact_id)
        logging.info(f"🔍 add_artifact {artifact.artifact_id} {existing_artifact}")
        if existing_artifact:
            raise ValueError(f"Artifact with ID {artifact.artifact_id} already exists")
        # Add to workspace
        self.artifacts.append(artifact)
        # Store in repository
        self._store_artifact(artifact)

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
        artifact = self.get_artifact(artifact_id)
        if artifact:
            artifact.update_content(content, description)

            # Update storage
            self._store_artifact(artifact)

            # Update workspace time
            self.updated_at = datetime.now().isoformat()

            # Notify observers
            await self._notify_observers("update", artifact)

            return artifact
        return None

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
                self._store_artifact(artifact)
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
    
    def _store_artifact(self, artifact: Artifact) -> None:
        """Store artifact in repository"""

        self.repository.store_artifact(artifact=artifact)
        logging.info(f"📦[CONTENT] store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} content finished")

        if artifact.embedding:
            if artifact.get_embedding_text():
                embedding_result = self.embedder.embed_artifact(artifact)
                self.vector_db.insert(self.workspace_id, [embedding_result])
                logging.info(f"📦[EMBEDDING]✅ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} embedding_result finished")
            else:
                logging.info(f"📦[EMBEDDING]❌ store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} embedding_text is empty")

            if artifact.sublist and len(artifact.sublist) > 0:
                for subartifact in artifact.sublist:
                    if subartifact.embedding and subartifact.get_embedding_text():
                        embedding_result = self.embedder.embed_artifact(subartifact)
                        self.vector_db.insert(self.workspace_id, [embedding_result])
                        logging.info(f"📦[EMBEDDING]✅ store_sub_artifact[{subartifact.artifact_type}]:{subartifact.artifact_id} embedding_result finished")

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
                        return sub_artifact
                return None

        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
        return None
    
    def get_file_content_by_artifact_id(self, artifact_id: str) -> str:
        """
        Get concatenated content of all artifacts with the same filename.
        
        Args:
            artifact_id: artifact_id
            
        Returns:
            Raw unescaped concatenated content of all matching artifacts
        """
        filename = artifact_id
        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                filename = artifact.metadata.get('filename')
                break

        result = ""
        for artifact in self.artifacts:
            if artifact.metadata.get('filename') == filename:
                if artifact.content:
                    result = result + artifact.content
        decoded_string = result.encode('utf-8').decode('unicode_escape')
        print(result)

        return decoded_string
    
    #########################################################
    # Hybrid Search
    #########################################################


    async def retrieve_artifact(self, search_query: HybridSearchQuery) -> Optional[list[HybridSearchResult]]:
        """
        Retrieve an artifact by its ID
        
        Args:
            query: Query string
            filter_types: Optional filter types

        TODO: 全文检索

        Returns:
            Artifact object if found, None otherwise
        """
        logging.info(f"🔍 retrieve_artifact search_query: {search_query}")
        results = []
        if not search_query:
            logging.warning("🔍 retrieve_artifact search_query is None")
            return None
        
        if not search_query.limit:
            search_query.limit = self.workspace_config.hybrid_search_config.top_k
        
        if not search_query.threshold:
            search_query.threshold = self.workspace_config.hybrid_search_config.threshold

        # 1. Embed query
        if self.workspace_config.hybrid_search_config.enabled:
            query_embedding = self.embedder.embed_query(search_query.query)

            # 2. Search vector db
            search_results = self.vector_db.search(self.workspace_id, [query_embedding], filter={}, threshold=search_query.threshold, limit=search_query.limit)
            if not search_results:
                logging.warning("🔍 retrieve_artifact search_results is None")
                return None
            
            if not search_results.docs:
                logging.warning("🔍 retrieve_artifact search_results.docs is None")
                return None
            
            for doc in search_results.docs:
                if not doc.metadata:
                    logging.warning("🔍 retrieve_artifact doc.metadata is None")
                    continue
                artifact = self.get_artifact(doc.metadata.artifact_id, parent_id = doc.metadata.parent_id)
                if not artifact:
                    logging.warning(f"🔍 retrieve_artifact artifact is None: {doc.metadata.artifact_id}")
                    continue
                results.append(HybridSearchResult(artifact=artifact, score=doc.score))
        
        logging.info(f"🔍 retrieve_artifact results size: {len(results)}")
        return results
    
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

        logging.info(f"💼 save_workspace {self.workspace_id}")
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
