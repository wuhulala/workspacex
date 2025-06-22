import uuid
from typing import List

from langchain_text_splitters import CharacterTextSplitter

from workspacex.artifact import Artifact, ArtifactType

from .base import Chunk, ChunkMetadata, ChunkerBase


class CharacterChunker(ChunkerBase):
    """
    A chunker that splits text by characters.
    """

    def chunk(self, artifact: Artifact) -> List[Chunk]:
        """
        Chunks the given content by characters.

        Args:
            content: The string content to chunk.

        Returns:
            A list of `Chunk` objects.
        """
        text_splitter = CharacterTextSplitter(
            separator="\\n",
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        texts = text_splitter.split_text(artifact.content)

        chunks: List[Chunk] = []
        for i, text in enumerate(texts):
            chunk = Chunk(
                content=text,
                chunk_metadata=ChunkMetadata(
                    chunk_index=i,
                    chunk_size=len(text),
                    chunk_overlap=self.config.chunk_overlap,
                    origin_artifact_id=artifact.artifact_id,
                )
            )
            chunks.append(chunk)

        return chunks 