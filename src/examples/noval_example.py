import os
import sys
from workspacex.artifact import ArtifactType
from workspacex.workspace import WorkSpace
import asyncio

NOVEL_FILE_PATH = os.path.join(os.path.dirname(__file__), '遮天（精校版）.txt')
SAVE_CHAPTERS_BASE_FOLDER = os.path.join(os.path.dirname(__file__), 'novel_chapters')


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
    ws = WorkSpace(workspace_id="novel_example_workspace", name="Novel Example Workspace")
    # Create the novel artifact and save chapters
    artifacts = await ws.create_artifact(
        artifact_id="novel_artifact",
        artifact_type=ArtifactType.NOVEL,
        novel_file_path=NOVEL_FILE_PATH
    )
    novel_artifact = artifacts[0]
    print(f"Novel artifact created: {novel_artifact.artifact_id}")
    print(f"Total chapters: {len(novel_artifact.chapters)}")
    # Print first 3 chapter titles as a sample
    for i, title in enumerate(novel_artifact.chapter_titles[:3]):
        print(f"Chapter {i+1}: {title}")

if __name__ == "__main__":
    asyncio.run(create_novel_artifact_example())
