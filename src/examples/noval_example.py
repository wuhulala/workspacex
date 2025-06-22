import os
import sys
import json
from dotenv import load_dotenv
from workspacex.artifact import ArtifactType, HybridSearchQuery
from workspacex.workspace import WorkSpace
import asyncio

NOVEL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'noval.txt')
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


async def create_novel_artifact_example(embedding_flag: bool = False) -> None:
    """
    Example: Create a NovelArtifact from a novel file, split by chapters, and save chapters to files.
    """
    ensure_output_folder(SAVE_CHAPTERS_BASE_FOLDER)
    # Create a workspace
    ws = WorkSpace(workspace_id="novel_example_workspace_v2", name="Novel Example Workspace", clear_existing=True)
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
    """
    results = await ws.retrieve_artifact(HybridSearchQuery(query="旅行者二号?", filter_types=[ArtifactType.NOVEL]))
    print(f"Hybrid search results: {results}")

if __name__ == "__main__":
    asyncio.run(create_novel_artifact_example(embedding_flag=True))
    # Uncomment the following line to test S3/MinIO integration
    # asyncio.run(create_novel_artifact_s3_example())