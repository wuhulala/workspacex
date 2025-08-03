from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

from workspacex.artifact import Artifact, ChunkMetadata
from workspacex.chunk.base import Chunk, ChunkConfig, ChunkerBase


class MarkdownChunker(ChunkerBase):
    """
    A chunker that splits markdown content by headers.
    """
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config=config)
        # Define headers to split on: (header_level, header_name)
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3")
        ]
        self._text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        
    async def chunk(self, artifact: Artifact) -> List[Chunk]:
        """
        Chunks the given markdown content by headers.
        """
        texts = self._text_splitter.split_text(artifact.content)
        return self._create_chunks(texts, artifact)

    def _create_chunks(self, texts: List[Document], artifact: Artifact) -> List[Chunk]:
        chunks: List[Chunk] = []
        for i, text in enumerate(texts):
            content = (f"Header#1 {text.metadata.get("Header 1")}\n"
                      f"Header#2: {text.metadata.get("Header 2")}\n"
                      f"Header#3: {text.metadata.get("Header 3")}\n"
                      f"Content: \n\n  {text.page_content}"
                       )
            chunk = Chunk(
                chunk_id=f"{artifact.artifact_id}_chunk_{i}",
                content=content,
                chunk_metadata=ChunkMetadata(
                    chunk_index=i,
                    chunk_size=len(text.page_content),
                    artifact_id=artifact.artifact_id,
                    artifact_type=artifact.artifact_type.value,
                    parent_artifact_id=artifact.parent_id,
                )
            )
            chunks.append(chunk)
        return chunks
