import uuid
import os
from workspacex import Artifact, ArtifactType
from workspacex.chunk.base import ChunkConfig
from workspacex.chunk.character import CharacterChunker
from workspacex.chunk.sentence import SentenceTokenChunker


def test_character(chapter_artifact: Artifact):
    chunker = CharacterChunker(config=ChunkConfig(chunk_size=1000, chunk_overlap=50))
    chunk_list = chunker.chunk(chapter_artifact)
    print(f"Chunk list: {len(chunk_list)}")
    for i, chunk in enumerate(chunk_list):
        print(f"Chunk {i + 1}: {chunk.content[:100]}")
        print(f"Chunk metadata: {chunk.chunk_metadata}")
        print("=" * 40)


def test_sentence(chapter_artifact: Artifact):
    os.environ['HF_ENDPOINT']='https://hf-mirror.com'
    chunker = SentenceTokenChunker(config=ChunkConfig(chunk_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", tokens_per_chunk=128, chunk_overlap=50))

    chunk_list = chunker.chunk(chapter_artifact)
    print(f"Chunk list: {len(chunk_list)}")
    for i, chunk in enumerate(chunk_list):
        print(f"Chunk {i + 1}: {chunk.content[:1000]}")
        print(f"Chunk metadata: {chunk.chunk_metadata}")
        print("=" * 40)



if __name__ == '__main__':

    file_path = os.path.join(os.path.pardir, "data", "noval.txt")
    if not os.path.exists(file_path):
        print("❌ noval.txt 文件不存在，请在父目录的 data 目录下创建该文件。")
        exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()


    artifact = Artifact(
        artifact_id=str(uuid.uuid4()),
        artifact_type=ArtifactType.TEXT,
        content=content,
        parent_id=str(uuid.uuid4())
    )

    # test_character(artifact)
    test_sentence(artifact)
