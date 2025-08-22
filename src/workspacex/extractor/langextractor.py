import asyncio
import json
import os
from typing import Any, Optional

from langextract import data_lib
from langextract.factory import ModelConfig

from workspacex import Artifact
from workspacex.artifacts.langextract import LangExtractorArtifact
from workspacex.extractor.base import BaseExtractor
import langextract as lx

from workspacex.utils.logger import logger


class LangExtractor(BaseExtractor):

    def __init__(self, name: str, prompt: str, examples: list[lx.data.ExampleData]):
        self.name = name
        self.lx = lx
        self.prompt = prompt
        self.examples = examples
        self.model_config = ModelConfig(
            model_id=os.environ.get("LLM_MODEL"),  # Automatically selects OpenAI provider
            provider="openai",
            provider_kwargs={
                "api_key": os.environ.get('LLM_API_KEY'),
                "base_url": os.environ.get("LLM_BASE_URL"),
            }
        )

    async def async_extract(self, content: Any, **kwargs) -> Optional[list[Artifact]]:
        if not isinstance(content, Artifact):
            logger.warning(f"content must be Artifact, but got {type(content)}")
            return None
        result = self.lx.extract(
            text_or_documents=content.content,
            prompt_description=self.prompt,
            examples=self.examples,
            config=self.model_config,
            fence_output=False,
            use_schema_constraints=False,
            # resolver_params={
            #     "fence_output": True
            # }
        )

        doc_dict = data_lib.annotated_document_to_dict(result)
        logger.info(f"Extracted {self.name} from {content.artifact_id} finished")
        langextract_artifact = LangExtractorArtifact(origin_artifact_id=content.artifact_id, extract_type=self.name,content=doc_dict)
        return [langextract_artifact]

    def extract(self, content: Any, **kwargs) -> Optional[list[Artifact]]:
        return asyncio.run(self.async_extract(content, **kwargs))
