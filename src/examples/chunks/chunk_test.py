import uuid
import os
from workspacex import Artifact, ArtifactType
from workspacex.chunk.base import ChunkConfig
from workspacex.chunk.character import CharacterChunker

if __name__ == '__main__':

    file_path = os.path.join(os.path.pardir, "data", "noval.txt")
    if not os.path.exists(file_path):
        print("❌ noval.txt 文件不存在，请在父目录的 data 目录下创建该文件。")
        exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()


    chapter_artifact = Artifact(
        artifact_id=str(uuid.uuid4()),
        artifact_type=ArtifactType.TEXT,
        content=content,
        parent_id=str(uuid.uuid4())
    )
    chunker = CharacterChunker(config=ChunkConfig(chunk_size=1000, chunk_overlap=50))
    chunk_list =  chunker.chunk(chapter_artifact)
    print(f"Chunk list: {len(chunk_list)}")
    for i, chunk in enumerate(chunk_list):
        print(f"Chunk {i + 1}: {chunk.content[:100]}")
        print(f"Chunk metadata: {chunk.chunk_metadata}")
        print("=" * 40)
