from workspacex.reranker.base import RerankConfig, BaseRerankRunner

class RerankerFactory:
    @staticmethod
    def getReranker(reranker_config: RerankConfig) -> BaseRerankRunner:
        if reranker_config.provider == "local":
            from workspacex.reranker.local import Qwen3RerankerRunner
            return Qwen3RerankerRunner(reranker_config)
        elif reranker_config.provider == "dashscope":
            from workspacex.reranker.dashscope import AliyunRerankRunner
            return AliyunRerankRunner(reranker_config)
        elif reranker_config.provider == "qwen3":
            from workspacex.reranker.local import Qwen3RerankerRunner
            return Qwen3RerankerRunner(reranker_config)
        elif reranker_config.provider == "http":
            from workspacex.reranker.http import HttpRerankRunner
            return HttpRerankRunner(reranker_config)
        elif reranker_config.provider == "bm25":
            from workspacex.reranker.bm25 import BM25RerankRunner
            return BM25RerankRunner(reranker_config)
        else:
            raise ValueError(f"Invalid reranker provider: {reranker_config.provider}")