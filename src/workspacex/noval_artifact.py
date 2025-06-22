
from pydantic import Field
from workspacex.artifact import Artifact, ArtifactType
from workspacex.extractor import noval_extractor
import uuid
from typing import Dict, Any, Optional

class NovelArtifact(Artifact):
    """
    Artifact for handling novels. Loads a novel file, splits it by chapters, and uploads each chapter as a separate file in the artifact's folder.
    """
    novel_file_path: str = Field(..., description="Path to the novel file")
    chapter_num: int = Field(default=0, description="Number of chapters")

    def __init__(
        self,
        artifact_type: ArtifactType,
        novel_file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        artifact_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a NovelArtifact, load and split the novel file, and create subartifacts for each chapter.
        """
        super().__init__(
            artifact_id=artifact_id or str(uuid.uuid4()),
            artifact_type=artifact_type,
            content=None,
            metadata=metadata or {},
            novel_file_path=novel_file_path,
            **kwargs
        )
        # Create subartifacts for each chapter
        artifacts = noval_extractor.extract(novel_file_path)
        self.chapter_num = len(artifacts)
        for sub_artifact in artifacts:
            sub_artifact.parent_id = self.artifact_id
            sub_artifact.embedding = self.embedding
            sub_artifact.mark_complete()
            self.add_subartifact(sub_artifact)
        self.mark_complete()