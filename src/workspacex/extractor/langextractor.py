import asyncio
import json
import os
from typing import Any, Optional, Dict

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

    async def async_extract(self, content: Any, llm_config: Dict[str, Any] = None, **kwargs) -> Optional[list[Artifact]]:

        if llm_config:
            model_config = ModelConfig(
                model_id=llm_config.get("llm_model", os.environ.get("LLM_MODEL")),
                # Automatically selects OpenAI provider
                provider="openai",
                provider_kwargs={
                    "api_key": os.environ.get('LLM_API_KEY'),
                    "base_url": os.environ.get("LLM_BASE_URL"),
                    "timeout": llm_config.get("timeout", 30),
                    "max_tokens": llm_config.get("max_tokens", 2048),
                    "temperature": llm_config.get("temperature", 0),
                }
            )
        else:
            model_config = self.model_config

        result = await asyncio.to_thread(self.lx.extract,
            text_or_documents=content,
            prompt_description=self.prompt,
            examples=self.examples,
            config=model_config,
            fence_output=False,
            use_schema_constraints=False,
            # resolver_params={
            #     "fence_output": True
            # }
        )
        artifact_id = kwargs.get("artifact_id", "unknown")

        doc_dict = data_lib.annotated_document_to_dict(result)
        logger.info(f"Extracted {self.name} from {artifact_id} finished")
        langextract_artifact = LangExtractorArtifact(origin_artifact_id=artifact_id, extract_type=self.name,content=doc_dict)
        return [langextract_artifact]

    def extract(self, content: Any, **kwargs) -> Optional[list[Artifact]]:
        return asyncio.run(self.async_extract(content, **kwargs))
