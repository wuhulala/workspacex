import os
import sys
import json
from dotenv import load_dotenv
from workspacex.artifact import ArtifactType, HybridSearchQuery
from workspacex.workspace import WorkSpace
import asyncio

NOVEL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'noval.txt')
"""
noval.txt 内容如下：

第001章 星空中的青铜巨棺
　　生命是世间最伟大的奇迹。
　　


第002章 素问
　　"上古之人，春秋皆度百岁，而动作不衰。"叶凡合上《黄帝内经》，对于素问篇所载的上古时代悠然神往。

"""
SAVE_CHAPTERS_BASE_FOLDER = os.path.join(os.path.dirname(__file__), 'novel_chapters')
import logging
logging.basicConfig(level=logging.INFO)

def ensure_output_folder(folder_path: str) -> None:
    """
    Ensure the output folder exists.
    Args:
        folder_path: Path to the folder
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


async def create_novel_artifact_example(embedding_flag: bool = False, chunker_flag: bool = False) -> None:
    """
    Example: Create a NovelArtifact from a novel file, split by chapters, and save chapters to files.
    """
    ensure_output_folder(SAVE_CHAPTERS_BASE_FOLDER)
    # Create a workspace
    ws = WorkSpace(workspace_id="novel_example_workspace_v5", name="Novel Example Workspace", clear_existing=True)
    # Create the novel artifact and save chapters
    artifacts = await ws.create_artifact(
        artifact_id="novel_artifact",
        artifact_type=ArtifactType.NOVEL,
        novel_file_path=NOVEL_FILE_PATH,
        embedding_flag=embedding_flag
    )
    novel_artifact = artifacts[0]
    logging.info(f"Novel artifact created: {novel_artifact.artifact_id}")
    logging.info(f"Total chapters: {novel_artifact.chapter_num}")
    # Print first 3 chapter titles as a sample
    for i, subartifact in enumerate(novel_artifact.sublist[:3]):
        logging.info(f"Chapter {i+1}: {subartifact.content[:100]}")
    if chunker_flag:
        await chunk_example(ws)

    if embedding_flag:
        logging.info("🔍 Hybrid search example")
        await hybrid_search_example(ws)


async def create_novel_artifact_s3_example() -> None:
    load_dotenv()
    """
    Example: Create a NovelArtifact and store it in S3 (MinIO backend).
    """
    from workspacex.storage.s3 import S3Repository
    # MinIO connection config
    s3_kwargs = {
        'key': os.getenv('MINIO_ACCESS_KEY'),  # MinIO default access key
        'secret': os.getenv('MINIO_SECRET_KEY'),  # MinIO default secret key
        'client_kwargs': {
            'endpoint_url':
            os.getenv('MINIO_ENDPOINT_URL'),  # MinIO server URL
        },
        'use_ssl': False
    }
    bucket = 'test-bucket'
    storage_path = 'novel-example-s3'
    # Ensure bucket exists (create if not)
    import s3fs
    fs = s3fs.S3FileSystem(**s3_kwargs)
    if not fs.exists(bucket):
        fs.mkdir(bucket)
    # Create S3Repository
    repo = S3Repository(storage_path=storage_path,
                        bucket=bucket,
                        s3_kwargs=s3_kwargs)
    # Create a workspace using S3Repository
    ws = WorkSpace(workspace_id="novel_example_workspace_s3",
                   name="Novel Example Workspace S3",
                   repository=repo)
    json.dump(ws.generate_tree_data(), open('tree_data.json', 'w'), indent=2)
    # Create the novel artifact and store in S3
    artifacts = await ws.create_artifact(artifact_id="novel_artifact_s3_v4",
                                         artifact_type=ArtifactType.NOVEL,
                                         novel_file_path=NOVEL_FILE_PATH)
    novel_artifact = artifacts[0]
    print(f"[S3] Novel artifact created: {novel_artifact.artifact_id}")
    print(f"[S3] Total chapters: {novel_artifact.chater_num}")
    for i, subartifact in enumerate(novel_artifact.sublist[:3]):
        print(f"[S3] Chapter {i+1}: {subartifact.content[:100]}")

async def hybrid_search_example(ws: WorkSpace) -> None:
    """
    Example: Hybrid search for a novel artifact.
    
    Args:
        ws: WorkSpace instance to perform search on
    """
    # Using a meaningful search query that should match content
    search_query = "上古时代的人们"  # This should match content about ancient times in chapter 2
    logging.info(f"Performing hybrid search with query: '{search_query}'")
    
    results = await ws.retrieve_artifact(
        HybridSearchQuery(
            query=search_query,
            filter_types=[ArtifactType.NOVEL],
            threshold=0.7
        )
    )
    
    if not results:
        logging.info("No results found")
        return
        
    logging.info(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        logging.info(f"\nResult #{i}:")
        logging.info(f"Chapter ID: {result.artifact.artifact_id}")
        logging.info(f"Similarity Score: {result.score:.4f}")
        logging.info(f"Content Preview: {result.artifact.content[:200]}...")

async def chunk_example(ws: WorkSpace) -> None:
    """
    Example: Demonstrate text chunking functionality on novel artifacts.
    
    Args:
        ws: WorkSpace instance containing the artifacts to chunk
    """
    from workspacex.chunk.base import ChunkConfig
    from workspacex.chunk.character import CharacterChunker

    # Get the first novel artifact
    artifacts = ws.list_artifacts(filter_types=[ArtifactType.NOVEL])
    if not artifacts:
        logging.info("No novel artifacts found")
        return

    novel_artifact = artifacts[0]

    # Create a chunker with custom configuration
    chunker = CharacterChunker(
        config=ChunkConfig(
            chunk_size=100,  # Smaller chunks for demonstration
            chunk_overlap=50
        )
    )
    
    # Chunk the artifact
    chunks = chunker.chunk(novel_artifact.sublist[0])
    
    # Display chunking results
    logging.info(f"\n📚 Chunking Results for artifact {novel_artifact.sublist[0].artifact_id}:")
    logging.info(f"Total chunks created: {len(chunks)}")
    
    # Show first 3 chunks as examples
    for i, chunk in enumerate(chunks[:3], 1):
        logging.info(f"\nChunk #{i}:")
        logging.info(f"Size: {chunk.chunk_metadata.chunk_size} characters")
        logging.info(f"Index: {chunk.chunk_metadata.chunk_index}")
        logging.info(f"Content preview: {chunk.content[:100]}...")

if __name__ == "__main__":
    asyncio.run(create_novel_artifact_example(embedding_flag=True, chunker_flag=False))
    # Uncomment the following line to test S3/MinIO integration
    # asyncio.run(create_novel_artifact_s3_example())
    # ws = WorkSpace(workspace_id="novel_example_workspace_v4", name="Novel Example Workspace", clear_existing=False)
    # asyncio.run(hybrid_search_example(ws))