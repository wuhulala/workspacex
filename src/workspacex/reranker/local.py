from typing import List, Optional, Dict, Any

from workspacex.reranker.base import BaseRerankRunner, RerankConfig, RerankResult
from workspacex.artifact import Artifact
import logging


class Qwen3RerankerRunner(BaseRerankRunner):
    """
    Local reranker using Qwen3-Reranker model via transformers.
    Requires transformers>=4.51.0 and torch.
    """
    def __init__(self, config: RerankConfig) -> None:
        """
        Initialize Qwen3RerankerRunner.
        Args:
            config (RerankConfig): Configuration for rerank model.
        Raises:
            ImportError: If required dependencies (torch, transformers) are not installed.
        """
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
        except ImportError as e:
            logging.error("Required dependencies not installed. Please install torch and transformers>=4.51.0")
            raise ImportError("Required dependencies not installed. Please install torch and transformers>=4.51.0") from e

        self.config = config
        self.model_id = config.model_name or "Qwen/Qwen3-Reranker-0.6B"

        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id,
                                                      padding_side='left')
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id)

        # Enable flash attention if available
        if torch.cuda.is_available():
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    torch_dtype=torch.float16,
                    attn_implementation="flash_attention_2").cuda()
            except Exception as e:
                logging.warning(
                    f"Failed to enable flash attention: {e}. Using default model."
                )
                self.model = self.model.cuda()
        self.model.eval()

        # Setup tokens and constants
        self.token_false_id = self.tokenizer.convert_tokens_to_ids("no")
        self.token_true_id = self.tokenizer.convert_tokens_to_ids("yes")
        self.max_length = 8192

        # Setup prompt templates
        self.prefix = "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n"
        self.suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        self.prefix_tokens = self.tokenizer.encode(self.prefix,
                                                  add_special_tokens=False)
        self.suffix_tokens = self.tokenizer.encode(self.suffix,
                                                  add_special_tokens=False)

        # Default instruction
        self.instruction = 'Given a web search query, retrieve relevant passages that answer the query'

    def format_instruction(self, query: str, doc: str) -> str:
        """
        Format the instruction, query and document into the required prompt format.
        Args:
            query (str): The search query
            doc (str): The document text
        Returns:
            str: Formatted prompt
        """
        return f"<Instruct>: {self.instruction}\n<Query>: {query}\n<Document>: {doc}"

    def process_inputs(self, pairs: List[str]) -> Dict[str, Any]:
        """
        Process and tokenize the input pairs.
        Args:
            pairs (List[str]): List of formatted instruction-query-document pairs
        Returns:
            Dict[str, Any]: Processed inputs ready for model
        """
        inputs = self.tokenizer(pairs,
                               padding=False,
                               truncation='longest_first',
                               return_attention_mask=False,
                               max_length=self.max_length -
                               len(self.prefix_tokens) -
                               len(self.suffix_tokens))
        for i, ele in enumerate(inputs['input_ids']):
            inputs['input_ids'][
                i] = self.prefix_tokens + ele + self.suffix_tokens
        inputs = self.tokenizer.pad(inputs,
                                   padding=True,
                                   return_tensors="pt",
                                   max_length=self.max_length)
        
        try:
            import torch
            if torch.cuda.is_available():
                for key in inputs:
                    inputs[key] = inputs[key].to(self.model.device)
        except ImportError:
            logging.error("torch not found when trying to move tensors to GPU")
            raise
        return inputs

    def compute_logits(self, inputs: Dict[str, Any]) -> List[float]:
        """
        Compute relevance scores using the model.
        Args:
            inputs (Dict[str, Any]): Processed inputs
        Returns:
            List[float]: List of relevance scores
        """
        try:
            import torch
            with torch.no_grad():
                batch_scores = self.model(**inputs).logits[:, -1, :]
                true_vector = batch_scores[:, self.token_true_id]
                false_vector = batch_scores[:, self.token_false_id]
                batch_scores = torch.stack([false_vector, true_vector], dim=1)
                batch_scores = torch.nn.functional.log_softmax(batch_scores, dim=1)
                scores = batch_scores[:, 1].exp().tolist()
                return scores
        except ImportError:
            logging.error("torch not found when computing logits")
            raise

    def run(
        self,
        query: str,
        documents: List[Artifact],
        score_threshold: Optional[float] = None,
        top_n: Optional[int] = None,
        user: Optional[str] = None,
    ) -> List[RerankResult]:
        """
        Run rerank using Qwen3-Reranker model locally.
        Args:
            query (str): Search query.
            documents (List[Artifact]): Documents for reranking.
            score_threshold (Optional[float]): Score threshold.
            top_n (Optional[int]): Top n results.
            user (Optional[str]): Unique user id if needed.
        Returns:
            List[RerankResult]: List of rerank results.
        Raises:
            ImportError: If required dependencies are not installed.
        """
        # Format inputs
        pairs = [
            self.format_instruction(query, doc.get_reranked_text())
            for doc in documents
        ]

        # Process and get scores
        inputs = self.process_inputs(pairs)
        scores = self.compute_logits(inputs)

        # Create results
        rerank_results = []
        for idx, score in enumerate(scores):
            if score_threshold is not None and score < score_threshold:
                continue
            rerank_results.append(
                RerankResult(artifact=documents[idx], score=score))

        # Sort and filter results
        rerank_results = sorted(rerank_results,
                               key=lambda x: x.score,
                               reverse=True)
        if top_n is not None:
            rerank_results = rerank_results[:top_n]

        return rerank_results
