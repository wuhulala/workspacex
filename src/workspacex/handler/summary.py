import asyncio
from abc import abstractmethod

from tqdm import tqdm

from workspacex import Artifact
from workspacex import WorkSpace
from workspacex.artifact import SummaryArtifact
from workspacex.utils.logger import logger


class SummaryHandler:

    workspace: "WorkSpace"

    def __init__(self, workspace: "WorkSpace"):
        self.workspace = workspace
        self.vector_db = self.workspace.vector_db
        self.embedder = self.workspace.embedder
        self.workspace_id = workspace.workspace_id
        self.collection = workspace.summary_vector_collection

    async def rebuild_summary(self):
        await self.pre_rebuild_summary(self.workspace)
        for artifact in tqdm(self.workspace.artifacts, desc="workspace_rebuild_summary"):
            await self.rebuild_artifact_summary(artifact)

    async def rebuild_artifact_summary(self, artifact: Artifact):
        await self._rebuild_artifact_summary(artifact)
        for sub_artifact in tqdm(artifact.sublist, f"artifact_rebuild_summary_sublist#{artifact.artifact_id}"):
            await self._rebuild_artifact_summary(sub_artifact)

    async def _rebuild_artifact_summary(self, artifact: Artifact):

        self.vector_db.delete(self.collection, filter={"artifact_id": artifact.artifact_id})
        logger.debug(f"📦[summary]✅ vector_store_delete_summary[{artifact.artifact_type}]:{artifact.artifact_id} finished")

        try:
            summary_result = await self._process_artifact_summary(artifact)
            if not summary_result or len(summary_result) == 0:
                logger.debug(
                    f"📦[summary]✅ _rebuild_artifact_summary[{artifact.artifact_type}]:{artifact.artifact_id} is empty ")
                return
            embedding_results = [await self.embedder.async_embed_artifact(summary) for summary in summary_result]
            await asyncio.to_thread(self.vector_db.insert, self.collection, embedding_results)
            logger.info(
                f"📦[summary]✅ vector_store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} summary_result finished")
        except Exception as e:
            logger.error(
                f"📦[summary]❌ vector_store_artifact[{artifact.artifact_type}]:{artifact.artifact_id} failed: {e}")
            raise

    @abstractmethod
    async def _process_artifact_summary(self, artifact: Artifact) -> list[SummaryArtifact]:
        pass

    @abstractmethod
    async def pre_rebuild_summary(self, workspace):
        pass
