from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from workspacex.artifact import Artifact

class RerankConfig(BaseModel):
    model_name: str = Field(..., description="Model name")
    api_key: str = Field(..., description="API key")
    base_url: str = Field(..., description="Base URL")
    score_threshold: Optional[float] = Field(default=None, description="Score threshold")
    top_n: Optional[int] = Field(default=None, description="Top n")

class RerankResult(BaseModel):
    artifact: Artifact = Field(..., description="Artifact")
    score: float = Field(..., description="Score")

class BaseRerankRunner(ABC):
    @abstractmethod
    def run(
        self,
        query: str,
        documents: list[Artifact],
        score_threshold: Optional[float] = None,
        top_n: Optional[int] = None,
        user: Optional[str] = None,
    ) -> list[RerankResult]:
        """
        Run rerank model
        :param query: search query
        :param documents: documents for reranking
        :param score_threshold: score threshold
        :param top_n: top n
        :param user: unique user id if needed
        :return:
        """
        raise NotImplementedError