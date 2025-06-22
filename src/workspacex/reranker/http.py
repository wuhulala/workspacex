from typing import List, Optional
from workspacex.reranker.base import BaseRerankRunner, RerankConfig, RerankResult
from workspacex.artifact import Artifact
import logging

import requests

from workspacex.utils.timeit import timeit

class HttpRerankRunner(BaseRerankRunner):
    """
    Aliyun Rerank Runner supporting both SDK and HTTP methods.
    The method is selected based on the config or SDK availability.
    """
    def __init__(self, config: RerankConfig, use_sdk: Optional[bool] = None) -> None:
        """
        Initialize AliyunRerankRunner.
        Args:
            config (RerankConfig): Configuration for rerank model and API.
            use_sdk (Optional[bool]): Whether to use SDK (if available). If None, auto-detect.
        """
        self.config = config

    def run(
        self,
        query: str,
        documents: List[Artifact],
        score_threshold: Optional[float] = None,
        top_n: Optional[int] = None,
        user: Optional[str] = None,
    ) -> List[RerankResult]:
        """
        Run Aliyun rerank model using SDK or HTTP.
        Args:
            query (str): Search query.
            documents (List[Artifact]): Documents for reranking.
            score_threshold (Optional[float]): Score threshold.
            top_n (Optional[int]): Top n results.
            user (Optional[str]): Unique user id if needed.
        Returns:
            List[RerankResult]: List of rerank results.
        """
        return self._run_http(query, documents, score_threshold, top_n, user)

    @timeit(logging.info, "HttpRerankRunner._run_http took {elapsed_time:.3f} seconds")
    def _run_http(
        self,
        query: str,
        documents: List[Artifact],
        score_threshold: Optional[float],
        top_n: Optional[int],
        user: Optional[str],
    ) -> List[RerankResult]:
        """
        Run rerank using Aliyun HTTP API.
        """
        url = self.config.base_url
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.config.model_name,
            "query": query,
            "documents": [doc.get_reranked_text() for doc in documents],
        }
        if top_n is not None:
            payload["top_n"] = top_n
        if score_threshold is not None:
            payload["score_threshold"] = score_threshold
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get('results', []):
            score = item['score']
            if score_threshold is not None and score < score_threshold:
                continue
            artifact = documents[item['index']]
            results.append(RerankResult(artifact=artifact, score=score))
        if top_n is not None:
            results = sorted(results, key=lambda x: x.score, reverse=True)[:top_n]
        return results
