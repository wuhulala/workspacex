import json
from typing import List, Optional

import requests

from workspacex.artifact import Artifact
from workspacex.reranker.base import BaseRerankRunner, RerankConfig, RerankResult
from workspacex.utils.logger import logger
from workspacex.utils.timeit import timeit

prefix = '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

query_template = "{prefix}<Instruct>: {instruction}\n<Query>: {query}\n"
document_template = "<Document>: {doc}{suffix}"
instruction = (
        "Given a web search query, retrieve relevant passages that answer the query"
)

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
            score_threshold: Optional[float] = 0.8,
            top_n: Optional[int] = 5,
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

    @timeit(logger.info, "HttpRerankRunner._run_http took {elapsed_time:.3f} seconds")
    def _run_http(
            self,
            query: str,
            documents: List[Artifact],
            score_threshold: Optional[float] = 0.8,
            top_n: Optional[int] = 10,
            user: Optional[str] = None,
    ) -> List[RerankResult]:
        """
        Run rerank using Aliyun HTTP API.
        """
        url = self.config.base_url
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        if self.config.model_name.__contains__("Qwen3-Reranker"):
            rerank_query = query_template.format(prefix=prefix, instruction=instruction, query=query)
            documents_text = [document_template.format(doc=doc.get_reranked_text(), suffix=suffix) for doc in documents]
        else:
            rerank_query = query
            documents_text = [doc.get_reranked_text() for doc in documents]

        logger.info(f"HttpRerankRunner._run_http documents_text total length: {sum(len(doc) for doc in documents_text)}")
        payload = {
            "model": self.config.model_name,
            "query": rerank_query,
            "documents": documents_text,
        }
        logger.info(f"HttpRerankRunner._run_http payload: \n {json.dumps(payload, indent=2, ensure_ascii=False)}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        results = []
        
        # compatiblity with two formats: old format (docs) and new format (results)
        items = data.get('docs', []) or data.get('results', [])
        
        for item in items:
            # compatibility with different field names
            if 'score' in item:
                # old format
                score = item['score']
                index = item['index']
            elif 'relevance_score' in item:
                # new format
                score = item['relevance_score']
                index = item['index']
            else:
                logger.warning(f"⚠️ unknown response format, skip item: {item}")
                continue
                
            if score_threshold is not None and score < score_threshold:
                continue
            artifact = documents[index]
            results.append(RerankResult(artifact=artifact, score=score))
            
        if top_n is not None:
            results = sorted(results, key=lambda x: x.score, reverse=True)[:top_n]
        return results
