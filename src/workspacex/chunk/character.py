from typing import List

from langchain_text_splitters import CharacterTextSplitter

from workspacex.artifact import Artifact
from .base import Chunk, ChunkConfig, ChunkerBase


class CharacterChunker(ChunkerBase):
    """
    A chunker that splits text by characters.
    """

    def __init__(self, config: ChunkConfig):
        super().__init__(config=config)
        self._text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    async def chunk(self, artifact: Artifact) -> List[Chunk]:
        """
        Chunks the given content by characters.

        Args:
            content: The string content to chunk.

        Returns:
            A list of `Chunk` objects.
        """
        texts = self._text_splitter.split_text(artifact.content)

        return self._create_chunks(texts, artifact)