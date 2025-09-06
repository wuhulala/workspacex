
import uuid
from typing import Dict, Any, Optional

from pydantic import Field

from workspacex.artifact import Artifact, ArtifactType, AttachmentFile
from workspacex.extractor import noval_extractor


class NovelArtifact(Artifact):
    """
    Artifact for handling novels. Loads a novel file, splits it by chapters, and uploads each chapter as a separate file in the artifact's folder.
    """

    @staticmethod
    def from_novel_file_path(
        novel_name: str,
        author: str,
        novel_desc: str,
        novel_file_path: str,
        **kwargs
    ):
        """
        Initialize a NovelArtifact, load and split the novel file, and create subartifacts for each chapter.
        """
        
        
        artifact = NovelArtifact(
            artifact_type=ArtifactType.NOVEL,
            metadata={
                "novel_name": novel_name,
                "author": author,
                "novel_desc": novel_desc
            },
            content="",
            **kwargs
        )
        # Create subartifacts for each chapter
        chatper_artifacts = noval_extractor.extract(novel_file_path)
        artifact.chapter_num = len(chatper_artifacts)
        for sub_artifact in chatper_artifacts:
            sub_artifact.parent_id = artifact.artifact_id
            sub_artifact.mark_complete()
            artifact.add_subartifact(sub_artifact)
        artifact.add_attachment_file(AttachmentFile(
            file_name=f"{novel_name}.txt",
            file_desc=f"{novel_desc} by {author}",
            file_path=novel_file_path
        ))
        artifact.mark_complete()
        return artifact

    @property
    def novel_file_path(self) -> str:
        return self.metadata.get('novel_file_path')

    @novel_file_path.setter
    def novel_file_path(self, novel_file_path: str):
        self.metadata['novel_file_path'] = novel_file_path

    @property
    def chapter_num(self) -> int:
        return self.metadata.get('chapter_num', 0)

    @chapter_num.setter
    def chapter_num(self, chapter_num: int):
        self.metadata['chapter_num'] = chapter_num

    @property
    def novel_name(self) -> str:
        return self.metadata.get('novel_name', '')

    @property
    def author(self) -> str:
        return self.metadata.get('author', '')

    @property
    def novel_desc(self) -> str:
        return self.metadata.get('novel_desc', '')
