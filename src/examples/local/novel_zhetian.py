import asyncio
import os

from dotenv import load_dotenv

from workspacex.artifact import ArtifactType, HybridSearchQuery, ChunkSearchQuery
from workspacex.artifacts.novel_artifact import NovelArtifact
from workspacex.workspace import WorkSpace

# 获取当前文件的父目录，然后拼接 data/noval.txt
NOVEL_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'noval.txt')
SAVE_CHAPTERS_BASE_FOLDER = os.path.join(os.path.dirname(__file__), 'novel_chapters')
from workspacex.utils.logger import logger
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


async def build_s3_workspace(workspace_id, clear_existing = False) -> WorkSpace:
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
    storage_path = workspace_id
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
    ws = WorkSpace(workspace_id=workspace_id,
                   name="Novel Example Workspace S3",
                   repository=repo,
                   clear_existing=clear_existing)
    return ws


async def create_novel_artifact_s3_example() -> None:
    # Create a workspace using S3Repository
    ws = await build_s3_workspace("zhetianv2", clear_existing=True)
    # Create the novel artifact and store in S3
    artifact = NovelArtifact.from_novel_file_path(
        novel_file_path=NOVEL_FILE_PATH, 
        novel_name="遮天",
        author="辰东", 
        novel_desc="《遮天》，网络作家辰东所著的玄幻小说，于2010年10月14日连载于起点中文网，于2013年5月21日完结，全书共636.32万字 [1]。"
    )

    await ws.add_artifact(artifact)
    


async def search_novel_workspace_artifacts_example() -> None:
    load_dotenv()
    """
    Example: Create a NovelArtifact and store it in S3 (MinIO backend).
    """
    ws = await build_s3_workspace("zhetian")

    search_query = "叶凡和小鹏王打了几次"

    results = await ws.retrieve_chunk(
        ChunkSearchQuery(query=search_query, threshold=0.3)
    )

    if not results:
        logger.info("No results found")
        return

    logger.info(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        logger.info(f"\nResult #{i}:")
        logger.info(f"Chunk ID: {result.chunk.chunk_id}")
        logger.info(f"Similarity Score: {result.score:.4f}")
        logger.info(f"Content Preview: {result.chunk.content[:200]}...")


if __name__ == "__main__":
    # Uncomment the following line to test S3/MinIO integration
    asyncio.run(create_novel_artifact_s3_example())
    # asyncio.run(search_novel_workspace_artifacts_example())