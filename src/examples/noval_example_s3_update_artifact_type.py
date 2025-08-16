import asyncio
import os

from dotenv import load_dotenv

from workspacex.artifact import ArtifactType, HybridSearchQuery
from workspacex.workspace import WorkSpace

NOVEL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'noval_large.txt')
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
    storage_path = 'novel'
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
    ws = WorkSpace(workspace_id="novel",
                   name="Novel Example Workspace S3",
                   repository=repo,
                   clear_existing=clear_existing)
    return ws

async def update_artifact_type():

    ws = await build_s3_workspace()

    for artifact in ws.artifacts:
        if not artifact.sublist:
            continue
        for sub_artifact in artifact.sublist:
            sub_artifact.artifact_type = ArtifactType.NOVEL_CHAPTER
        ws.repository.store_artifact(artifact, save_sub_list_content=False)

    ws.save()




if __name__ == "__main__":
    # asyncio.run(create_novel_artifact_example())
    # Uncomment the following line to test S3/MinIO integration
    # asyncio.run(create_novel_artifact_s3_example())
    # asyncio.run(rebuild_novel_workspace_full_text_example())
    # asyncio.run(rebuild_embedding_novel_artifact_s3_example())
    # ws = WorkSpace(workspace_id="novel_example_workspace_v7", name="Novel Example Workspace", clear_existing=False)
    asyncio.run(update_artifact_type())