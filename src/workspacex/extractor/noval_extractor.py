import os
from typing import Any, List
from workspacex.artifact import Artifact, ArtifactType
from workspacex.extractor.base import BaseExtractor


class NovalExtractor(BaseExtractor):
    
    """
    Extractor for Noval files.
    Loads a novel file, splits it by chapters, 
    """
    
    def extract(self, content: Any) -> list[Artifact]:
        """Extract artifacts from content."""
        novel_file_path = content

        chapters, chapter_titles = self._load_and_split_novel(novel_file_path)

        artifacts = []
        # Create subartifacts for each chapter
        for idx, (title, chapter) in enumerate(zip(chapter_titles, chapters)):
            sub_meta = {
                "chapter_title": title,
                "chapter_index": idx + 1
            }
            subartifact = Artifact(
                artifact_id=f"chapter_{idx+1}_{title.replace(' ', '')}",
                artifact_type=ArtifactType.TEXT,
                content=chapter,
                metadata=sub_meta
            )
            artifacts.append(subartifact)
        return artifacts

    def _load_and_split_novel(self, novel_file_path: str) -> tuple[str, List[str], List[str]]:
        """
        Load the novel file and split it into chapters.
        Args:
            novel_file_path: Path to the novel file
        Returns:
            Tuple of (full content, list of chapters, list of chapter titles)
        """
        with open(novel_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        import re
        # Split by chapter heading, e.g., "第001章" or "第1章"
        pattern = r'(第[0-9一二三四五六七八九十百千]+章[\s\S]*?)(?=第[0-9一二三四五六七八九十百千]+章|$)'
        chapters = re.findall(pattern, content)
        # Extract chapter titles
        title_pattern = r'(第[0-9一二三四五六七八九十百千]+章[^\n]*)'
        chapter_titles = re.findall(title_pattern, content)
        return chapters, chapter_titles
    
noval_extractor = NovalExtractor()