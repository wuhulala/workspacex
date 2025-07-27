import asyncio
from abc import abstractmethod
from typing import List

from tqdm import tqdm

from workspacex import Artifact
from workspacex import WorkSpace
from workspacex.extractor.base import BaseExtractor
from workspacex.utils.logger import logger


class SummaryHandler:

    workspace: "WorkSpace"

    def __init__(self, workspace: "WorkSpace", summarizer: BaseExtractor):
        self.workspace = workspace
        self.vector_db = self.workspace.vector_db
        self.embedder = self.workspace.vector_db
        self.workspace_id = workspace.workspace_id
        self.summarizer = summarizer
        self.collection = workspace.summary_vector_collection

    async def rebuild_summary(self, artifacts: List[Artifact]):
        for artifact in tqdm(artifacts, desc="workspace_rebuild_summary"):
            await self.rebuild_artifact_summary(artifact)

    async def rebuild_artifact_summary(self, artifact: Artifact):
        await self._rebuild_artifact_summary(artifact)
        for sub_artifact in tqdm(artifact.sublist, f"artifact_rebuild_summary_sublist#{artifact.artifact_id}"):
            await self._rebuild_artifact_summary(sub_artifact)

    async def _rebuild_artifact_summary(self, artifact: Artifact):

        self.vector_db.delete(self.collection, filter={"artifact_id": artifact.artifact_id})
        logger.info(f"📦[summary]✅ vector_store_delete_summary[{artifact.artifact_type}]:{artifact.artifact_id} finished")

        try:
            summary_result = await asyncio.to_thread(self._process_artifact_summary, artifact)
            await asyncio.to_thread(self.vector_db.insert, self.collection, summary_result)
            logger.info(
                f"📦[summary]✅ vector_store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} summary_result finished")
        except Exception as e:
            logger.error(
                f"📦[summary]❌ vector_store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}")
            raise

    @abstractmethod
    async def _process_artifact_summary(self, artifact: Artifact) -> list[Artifact]:
        pass
