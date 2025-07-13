import asyncio
import os

from dotenv import load_dotenv

from workspacex.artifact import ArtifactType, HybridSearchQuery, ChunkSearchQuery
from workspacex.workspace import WorkSpace

NOVEL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'noval.txt')
"""
noval.txt 内容如下：

第001章 星空中的青铜巨棺
　　生命是世间最伟大的奇迹。
　　


第002章 素问
　　"上古之人，春秋皆度百岁，而动作不衰。"叶凡合上《黄帝内经》，对于素问篇所载的上古时代悠然神往。

"""
SAVE_CHAPTERS_BASE_FOLDER = os.path.join(os.path.dirname(__file__), 'novel_chapters')
from workspacex.utils.logger import logger
# import logging
# logging.basicConfig(level=logging.DEBUG)

def ensure_output_folder(folder_path: str) -> None:
    """
    Ensure the output folder exists.
    Args:
        folder_path: Path to the folder
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


async def create_novel_artifact_example() -> None:
    """
    Example: Create a NovelArtifact from a novel file, split by chapters, and save chapters to files.
    """
    ensure_output_folder(SAVE_CHAPTERS_BASE_FOLDER)
    # Create a workspace
    ws = WorkSpace(workspace_id="novel_example_workspace_v9", name="Novel Example Workspace", clear_existing=True)
    # Create the novel artifact and save chapters
    artifacts = await ws.create_artifact(
        artifact_id="novel_artifact",
        artifact_type=ArtifactType.NOVEL,
        novel_file_path=NOVEL_FILE_PATH
    )
    novel_artifact = artifacts[0]
    logger.info(f"Novel artifact created: {novel_artifact.artifact_id}")
    logger.info(f"Total chapters: {novel_artifact.chapter_num}")
    # Print first 3 chapter titles as a sample
    for i, subartifact in enumerate(novel_artifact.sublist[:3]):
        logger.info(f"Chapter {i+1}: {subartifact.content[:100]}")

    if ws.workspace_config.embedding_config.enabled:
        logger.info("🔍 Hybrid search example")
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
    bucket = 'agentworkspace'
    storage_path = 'novel_workspace'
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
    ws = WorkSpace(workspace_id="novel_workspace",
                   name="Novel Example Workspace S3",
                   repository=repo, clear_existing=True)
    # Create the novel artifact and store in S3
    artifacts = await ws.create_artifact(artifact_id="novel_artifact",
                                         artifact_type=ArtifactType.NOVEL,
                                         novel_file_path=NOVEL_FILE_PATH)
    novel_artifact = artifacts[0]
    print(f"[S3] Novel artifact created: {novel_artifact.artifact_id}")
    # print(f"[S3] Total chapters: {novel_artifact.chater_num}")
    for i, subartifact in enumerate(novel_artifact.sublist[:3]):
        print(f"[S3] Chapter {i+1}: {subartifact.content[:100]}")


async def rebuild_embedding_novel_artifact_s3_example() -> None:
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
    bucket = 'agentworkspace'
    storage_path = 'novel_workspace_test'
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
    ws = WorkSpace(workspace_id="novel_workspace_test",
                   name="Novel Example Workspace S3",
                   repository=repo)

    await ws.rebuild_embedding()

    # await hybrid_search_chunk_example(ws)
async def hybrid_search_example(ws: WorkSpace) -> None:
    """
    Example: Hybrid search for a novel artifact.
    
    Args:
        ws: WorkSpace instance to perform search on
    """
    # Using a meaningful search query that should match content
    search_query = "国际空间站"  # This should match content about ancient times in chapter 2
    logger.info(f"Performing hybrid search with query: '{search_query}'")
    
    results = await ws.retrieve_artifact(
        HybridSearchQuery(
            query=search_query,
            filter_types=[ArtifactType.NOVEL],
            threshold=0.7
        )
    )
    
    if not results:
        logger.info("No results found")
        return
        
    logger.info(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        logger.info(f"\nResult #{i}:")
        logger.info(f"Chapter ID: {result.artifact.artifact_id}")
        logger.info(f"Similarity Score: {result.score:.4f}")
        logger.info(f"Content Preview: {result.artifact.content[:200]}...")

async def hybrid_search_chunk_example(ws: WorkSpace) -> None:
    """
    Example: Hybrid search for a novel artifact.

    Args:
        ws: WorkSpace instance to perform search on
    """
    # Using a meaningful search query that should match content
    search_query = "国际空间站"  # This should match content about ancient times in chapter 2
    logger.info(f"Performing hybrid search with query: '{search_query}'")

    results = await ws.retrieve_chunk(
        ChunkSearchQuery(
            query=search_query,
            threshold=0.7
        )
    )

    if not results:
        logger.info("No results found")
        return

    logger.info(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        logger.info(f"=== Result #{i} ===[{result.chunk.chunk_id}:{result.score:.4f}]===")
        logger.info(f"Chunk Content: {result.chunk.content[:100]}...")
        logger.info(f"Chunk Pre Chunks: {[chunk.chunk_id for chunk in result.pre_n_chunks]}")
        logger.info(f"Chunk Next Chunks: {[chunk.chunk_id for chunk in result.next_n_chunks]}")

if __name__ == "__main__":
    # asyncio.run(create_novel_artifact_example())
    # Uncomment the following line to test S3/MinIO integration
    asyncio.run(create_novel_artifact_s3_example())
    # asyncio.run(rebuild_embedding_novel_artifact_s3_example())
    # ws = WorkSpace(workspace_id="novel_example_workspace_v7", name="Novel Example Workspace", clear_existing=False)
    # asyncio.run(hybrid_search_example(ws))
    # asyncio.run(hybrid_search_chunk_example(ws))