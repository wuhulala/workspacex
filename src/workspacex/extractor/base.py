import json
import logging
import traceback
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from workspacex.artifact import Artifact, ArtifactType
from workspacex.utils.rag_utils import call_llm, call_llm_async


class BaseExtractor(ABC):
    """Base class for extractors.
    Extractors are used to extract artifacts from content. such as text, images, audio, video, html, pdf, markdown, noval.txt, etc.
    """

    @abstractmethod
    def extract(self, content: Any) -> Optional[list[Artifact]]:
        """Extract artifacts from content."""
        raise NotImplementedError

    @abstractmethod
    async def async_extract(self, content: Any, **kwargs) -> Optional[list[Artifact]]:
        """Extract artifacts from content."""
        raise NotImplementedError


class BaseLLMExtractor(BaseExtractor):
    def __init__(self, extractor_model: str, extractor_prompt: str, extract_type: str, format_json: bool = False):
        self.extractor_model = extractor_model
        self.extractor_prompt = extractor_prompt
        self.format_json = format_json
        self.extract_type = extract_type

    def extract(self, content: Any, llm_config: dict[str, Any] = None) -> list[Artifact]:
        try:
            extracted_data = self.extract_by_llm(content, llm_config)
            artifact = Artifact(
                artifact_id=f"{str(uuid.uuid4().hex)}_{self.extract_type}",
                content=f"{extracted_data}",
                artifact_type=ArtifactType.TEXT
            )
            return [artifact]
        except Exception as e:
            logging.error(f"[Extractor#{self.extract_type}] error: {e}, \n trace is {traceback.format_exc()}")
            raise e

    def extract_by_llm(self, content: Any, llm_config: dict[str, Any] = None) -> str:
        prompt = self.extractor_prompt.format(text=content)
        extract_model = self.extractor_model
        if llm_config and llm_config.get("extract_model"):
            extract_model = llm_config.get("extract_model")
        llm_result = call_llm(prompt, extract_model, llm_config)
        if self.format_json:
            extracted_data = json.loads(llm_result.replace("```json", "").replace("```", ""))
            logging.debug(f"extracted_data: {extracted_data}")
            return extracted_data
        else:
            return llm_result

    async def async_extract(self, content: Any, llm_config: dict[str, Any] = None) -> list[Artifact]:
        try:
            extracted_data = await self.extract_by_llm_async(content, llm_config)
            artifact = Artifact(
                artifact_id=f"{str(uuid.uuid4().hex)}_{self.extract_type}",
                content=f"{extracted_data}",
                artifact_type=ArtifactType.TEXT
            )
            return [artifact]
        except Exception as e:
            logging.error(f"[Extractor#{self.extract_type}] error: {e}, \n trace is {traceback.format_exc()}")
            raise e

    async def extract_by_llm_async(self, content: Any, llm_config: dict[str, Any] = None) -> str:
        prompt = self.extractor_prompt.format(text=content)
        extract_model = self.extractor_model
        if llm_config and llm_config.get("extract_model"):
            extract_model = llm_config.get("extract_model")
        llm_result = await call_llm_async(prompt, extract_model, llm_config)
        if self.format_json:
            extracted_data = json.loads(llm_result.replace("```json", "").replace("```", ""))
            logging.debug(f"extracted_data: {extracted_data}")
            return extracted_data
        else:
            return llm_result


class BaseJudgeLLMExtractor(BaseLLMExtractor):

    def __init__(self, extractor_type: str,
                 extractor_model: str,
                 extractor_prompt: str,
                 format_json: bool,
                 judge_prompt: str,
                 judge_model: str,
                 format_judge_json: bool= False):
        super().__init__(extractor_model, extractor_prompt, extractor_type, format_json=format_json)
        self.judge_model = judge_model
        self.judge_prompt = judge_prompt
        self.format_judge_json = format_judge_json

    def extract(self, content: Any, llm_config: dict[str, Any] = None) -> list[Artifact]:
        artifacts = []
        try:
            extracted_data = self.extract_by_llm(content, llm_config)
            logging.info(f"Extractor#{self.extract_type} extracted_data: {extracted_data}")
            judge_data = self.judge(extracted_data)
            logging.info(f"Extractor#{self.extract_type} judge_data: {judge_data}")
            artifact = Artifact(
                artifact_id=f"{str(uuid.uuid4().hex)}_level_up",
                content=f"{judge_data}",
                artifact_type=ArtifactType.TEXT,
                metadata={
                    "origin_extracted_data": extracted_data,
                }
            )
            artifacts.append(artifact)
            return artifacts
        except Exception as e:
            logging.error(f"Error is {e}, \n trace is {traceback.format_exc()}")
            raise

    async def async_extract(self, content: Any, llm_config: dict[str, Any] = None) -> list[Artifact]:
        try:
            extracted_data = await self.extract_by_llm_async(content, llm_config)
            judge_data = await self.async_judge(extracted_data)
            artifact = Artifact(
                artifact_id=f"{str(uuid.uuid4().hex)}_level_up",
                content=f"{judge_data}",
                artifact_type=ArtifactType.TEXT,
                metadata={
                    "origin_extracted_data": extracted_data,
                }
            )
            return [artifact]
        except Exception as e:
            logging.error(f"[Extractor#{self.extract_type}] error: {e}, \n trace is {traceback.format_exc()}")
            raise

    @abstractmethod
    def judge(self, extracted_data: Any) -> Any:
        raise NotImplementedError
    @abstractmethod
    async def async_judge(self, extracted_data: Any) -> Any:
        raise NotImplementedError

    def _judge_by_llm(self, judge_prompt: str, llm_config: dict[str, Any] = None) -> Any:
        judge_result = call_llm(judge_prompt, self.judge_model, llm_config)
        if self.format_judge_json:
            judge_data = json.loads(judge_result.replace("```json", "").replace("```", ""))
            logging.debug(f"judge_data: {judge_data}")
            return judge_data
        else:
            return judge_result

    async def _async_judge_by_llm(self, judge_prompt: str, llm_config: dict[str, Any] = None) -> Any:
        judge_result = await call_llm_async(judge_prompt, self.judge_model, llm_config)
        if self.format_judge_json:
            judge_data = json.loads(judge_result.replace("```json", "").replace("```", ""))
            logging.debug(f"judge_data: {judge_data}")
            return judge_data
        else:
            return judge_result
