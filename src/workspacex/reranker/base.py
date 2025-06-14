from abc import ABC, abstractmethod
from typing import Optional

from workspacex.artifact import Artifact



class BaseRerankRunner(ABC):
    @abstractmethod
    def run(
        self,
        query: str,
        documents: list[Artifact],
        score_threshold: Optional[float] = None,
        top_n: Optional[int] = None,
        user: Optional[str] = None,
    ) -> list[Artifact]:
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