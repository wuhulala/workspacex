from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from workspacex.artifact import Artifact


class RerankConfig(BaseModel):
    provider: str = Field(default="local", description="Provider")
    base_url: str = Field(..., description="Base URL")
    api_key: Optional[str] = Field(default=None, description="API key")
    model_name: Optional[str] = Field(default=None, description="Model name")
    
    @staticmethod
    def from_config(config: dict) -> "RerankConfig":
        if not config:
            return None
        return RerankConfig(**config)



class RerankResult(BaseModel):
    artifact: Artifact = Field(..., description="Artifact")
    score: float = Field(..., description="Score")


class BaseRerankRunner(ABC):
    @abstractmethod
    def run(
            self,
            query: str,
            documents: list[Artifact],
            score_threshold: Optional[float] = 0.8,
            top_n: Optional[int] = 5,
            user: Optional[str] = None,
    ) -> list[RerankResult]:
        """
        Run rerank model
        :param query: search query
        :param documents: documents for reranking
        :param score_threshold: score threshold
        :param top_n: top n
        :param user: unique user id if needed

                results = reranker.run("你好", documents=[
                    Artifact(artifact_type=ArtifactType.TEXT, content="你好"),
                    Artifact(artifact_type=ArtifactType.TEXT, content="我很好"),
                    Artifact(artifact_type=ArtifactType.TEXT, content="谢谢你"),
                    Artifact(artifact_type=ArtifactType.TEXT, content="很高兴遇到你"),
                ])
                for result in results:
                    print(f"{result.artifact.content}: {result.score}")
                # 你好: 0.989096999168396
                # 很高兴遇到你: 0.30921047925949097
                # 谢谢你: 0.10078048706054688
                # 我很好: 0.06917418539524078
        """
        raise NotImplementedError
