import asyncio
import os

from dotenv import load_dotenv

from workspacex.artifact import ArtifactType
from workspacex.utils.logger import logger
from workspacex.workspace import WorkSpace


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


async def build_s3_workspace(clear_existing = False):
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
    storage_path = 'test'
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
    ws = WorkSpace(workspace_id="test",
                   name="Novel Example Workspace S3",
                   repository=repo,
                   clear_existing=clear_existing)
    return ws


async def create_arxiv_artifact_example() -> None:
    """
    Example: Create a NovelArtifact from a novel file, split by chapters, and save chapters to files.
    """
    # Create a workspace
    ws = WorkSpace(workspace_id="arxiv_artifact_example_workspace_v9", name="Arxiv Example Workspace", clear_existing=True)
    # Create the novel artifact and save chapters
    artifacts = await ws.create_artifact(
        arxiv_id="2507.21509",
        artifact_type=ArtifactType.ARXIV,
    )
    arxiv = artifacts[0]
    logger.info(f"Novel artifact created: {arxiv.artifact_id}")



async def create_arxiv_artifact_s3_example() -> None:
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
    storage_path = 'arxiv_workspace'
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
    ws = WorkSpace(workspace_id="arxiv_workspace",
                   name="Arxiv Example Workspace S3",
                   repository=repo, clear_existing=True)
    artifacts = await ws.create_artifact(
        arxiv_id="2507.21509",
        artifact_type=ArtifactType.ARXIV,
    )
    arxiv = artifacts[0]
    logger.info(f"Novel artifact created: {arxiv.artifact_id}")


if __name__ == "__main__":
    # asyncio.run(create_arxiv_artifact_example())
    asyncio.run(create_arxiv_artifact_s3_example())
    # Uncomment the following line to test S3/MinIO integration
    # asyncio.run(create_novel_artifact_s3_example())
    # asyncio.run(rebuild_novel_workspace_full_text_example())
    # asyncio.run(rebuild_embedding_novel_artifact_s3_example())
    # ws = WorkSpace(workspace_id="novel_example_workspace_v7", name="Novel Example Workspace", clear_existing=False)
    # asyncio.run(search_novel_workspace_artifacts_example())