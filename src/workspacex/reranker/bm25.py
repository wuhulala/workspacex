import math
import re
from collections import Counter
from typing import List, Optional

from workspacex.artifact import Artifact
from workspacex.reranker.base import BaseRerankRunner, RerankConfig, RerankResult
from workspacex.utils.logger import logger
from workspacex.utils.timeit import timeit


class BM25RerankRunner(BaseRerankRunner):
    """
    BM25 Rerank Runner implementation.
    BM25 is a ranking function used by search engines to rank documents based on relevance.
    """

    def __init__(self, config: RerankConfig) -> None:
        """
        Initialize BM25RerankRunner.
        Args:
            config (RerankConfig): Configuration for BM25 parameters.
        """
        self.config = config
        # BM25 parameters with defaults
        self.k1 = getattr(config, 'k1', 1.2)  # Term frequency saturation parameter
        self.b = getattr(config, 'b', 0.75)   # Length normalization parameter
        self.avgdl = 0.0  # Average document length
        self.doc_freq = {}  # Document frequency for each term
        self.doc_lengths = {}  # Document lengths
        self.term_freq = {}  # Term frequency in each document
        self.corpus_size = 0  # Total number of documents

    def run(
            self,
            query: str,
            documents: List[Artifact],
            score_threshold: Optional[float] = 0.8,
            top_n: Optional[int] = 5,
            user: Optional[str] = None,
    ) -> List[RerankResult]:
        """
        Run BM25 rerank model.
        Args:
            query (str): Search query.
            documents (List[Artifact]): Documents for reranking.
            score_threshold (Optional[float]): Score threshold.
            top_n (Optional[int]): Top n results.
            user (Optional[str]): Unique user id if needed.
        Returns:
            List[RerankResult]: List of rerank results.
        """
        return self._run_bm25(query, documents, score_threshold, top_n, user)

    @timeit(logger.info, "BM25RerankRunner._run_bm25 took {elapsed_time:.3f} seconds")
    def _run_bm25(
            self,
            query: str,
            documents: List[Artifact],
            score_threshold: Optional[float] = 0.8,
            top_n: Optional[int] = 10,
            user: Optional[str] = None,
    ) -> List[RerankResult]:
        """
        Run BM25 rerank algorithm.
        """
        if not documents:
            return []

        # Preprocess documents and build corpus statistics
        self._build_corpus_stats(documents)
        
        # Tokenize query
        query_terms = self._tokenize(query)
        
        # Calculate BM25 scores for each document
        results = []
        for i, doc in enumerate(documents):
            score = self._calculate_bm25_score(query_terms, i)
            logger.info(f"📊 rerank_results item: {doc.artifact_id}: {score}")
            if score_threshold is None or score >= score_threshold:
                results.append(RerankResult(artifact=doc, score=score))
        
        # Sort by score in descending order
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply top_n filter
        if top_n is not None:
            results = results[:top_n]
        
        return results

    def _build_corpus_stats(self, documents: List[Artifact]) -> None:
        """
        Build corpus statistics for BM25 calculation.
        Args:
            documents (List[Artifact]): List of documents to process.
        """
        self.corpus_size = len(documents)
        self.doc_lengths = {}
        self.term_freq = {}
        self.doc_freq = {}
        
        total_length = 0
        
        # Process each document
        for i, doc in enumerate(documents):
            text = doc.get_reranked_text()
            terms = self._tokenize(text)
            
            # Store document length
            doc_length = len(terms)
            self.doc_lengths[i] = doc_length
            total_length += doc_length
            
            # Count term frequencies in this document
            term_counts = Counter(terms)
            self.term_freq[i] = dict(term_counts)
            
            # Update document frequency for each unique term
            for term in term_counts:
                if term not in self.doc_freq:
                    self.doc_freq[term] = 0
                self.doc_freq[term] += 1
        
        # Calculate average document length
        self.avgdl = total_length / self.corpus_size if self.corpus_size > 0 else 0

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms.
        Args:
            text (str): Text to tokenize.
        Returns:
            List[str]: List of tokens.
        """
        # Simple tokenization - split on whitespace and remove punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def _calculate_bm25_score(self, query_terms: List[str], doc_id: int) -> float:
        """
        Calculate BM25 score for a document given query terms.
        Args:
            query_terms (List[str]): Query terms.
            doc_id (int): Document ID.
        Returns:
            float: BM25 score.
        """
        score = 0.0
        
        for term in query_terms:
            # Skip terms not in vocabulary
            if term not in self.doc_freq:
                continue
                
            # Calculate IDF (Inverse Document Frequency)
            idf = math.log((self.corpus_size - self.doc_freq[term] + 0.5) / 
                          (self.doc_freq[term] + 0.5) + 1)
            
            # Get term frequency in this document
            tf = self.term_freq[doc_id].get(term, 0)
            
            # Calculate BM25 score component for this term
            doc_length = self.doc_lengths[doc_id]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avgdl))
            
            if denominator > 0:
                score += idf * (numerator / denominator)
        
        return score
