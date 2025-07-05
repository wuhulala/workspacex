from langchain_text_splitters import SentenceTransformersTokenTextSplitter

from workspacex.artifact import Artifact
from workspacex.chunk.base import Chunk, ChunkConfig, ChunkerBase


class SentenceTokenChunker(ChunkerBase):
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config=config)
        self._text_splitter = SentenceTransformersTokenTextSplitter(
            chunk_overlap=self.config.chunk_overlap,
            model_name=self.config.chunk_model,
            tokens_per_chunk=self.config.tokens_per_chunk,
        )

    """
    A chunker that splits text by sentences.
    """
    async def chunk(self, artifact: Artifact) -> list[Chunk]:
        texts = self._text_splitter.split_text(artifact.content)
        return self._create_chunks(texts, artifact)
