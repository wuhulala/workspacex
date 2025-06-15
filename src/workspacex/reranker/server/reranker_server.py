import os
import time
from typing import List, Optional, Union
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
import uvicorn
import logging
from workspacex.reranker.base import RerankConfig
from workspacex.reranker.local import Qwen3RerankerRunner
from workspacex.artifact import Artifact, ArtifactType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Reranker API",
              description="A FastAPI service for reranking documents",
              version="1.0.0")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url}")

    if request.method == "POST":
        body = await request.json()
        logger.info(f"Request body: {body}")

    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

class Document(BaseModel):
    """Document model for reranking"""
    content: str = Field(..., description="The document content to rerank")
    metadata: dict = Field(default_factory=dict, description="Optional metadata")

class RerankerRequest(BaseModel):
    """Request model for reranking"""
    query: str = Field(..., description="The search query")
    documents: List[Union[Document, str]] = Field(..., description="List of documents to rerank (can be strings or Document objects)")
    score_threshold: Optional[float] = Field(None, description="Optional score threshold")
    top_n: Optional[int] = Field(None, description="Optional top N results to return")

    @field_validator('documents')
    @classmethod
    def validate_documents(cls, v):
        """Convert string documents to Document objects for compatibility"""
        processed_docs = []
        for idx, doc in enumerate(v):
            if isinstance(doc, str):
                processed_docs.append(Document(content=doc, metadata={"index": idx}))
            elif isinstance(doc, dict):
                # Handle dict format
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                processed_docs.append(Document(content=content, metadata=metadata))
            elif isinstance(doc, Document):
                processed_docs.append(doc)
            else:
                raise ValueError(f"Invalid document format: {type(doc)}. Expected str, dict, or Document object.")
        return processed_docs


class RerankerResponse(BaseModel):
    """Response model for reranking results"""
    docs: List[dict] = Field(..., description="Ranked results with scores")
    model: str = Field(..., description="Model name")

# Global reranker instance
reranker: Optional[Qwen3RerankerRunner] = None

def get_reranker() -> Qwen3RerankerRunner:
    """
    Get or initialize the reranker instance.
    Returns:
        Qwen3RerankerRunner: The reranker instance
    """
    global reranker
    if reranker is None:
        try:
            config = RerankConfig(
                model_name=os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-0.6B"),
                api_key="not_needed",  # Not used for local model
                base_url="not_needed"   # Not used for local model
            )
            reranker = Qwen3RerankerRunner(config)
            logger.info("Reranker initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to initialize reranker: {e}")
            raise HTTPException(
                status_code=500,
                detail="Reranker dependencies not installed. Please install with 'pip install workspacex[reranker]'"
            )
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize reranker: {str(e)}"
            )
    return reranker

@app.post("/rerank", response_model=RerankerResponse)
async def rerank(request: RerankerRequest) -> RerankerResponse:
    """
    Rerank documents based on a query.
    Args:
        request (RerankerRequest): The rerank request containing query and documents
    Returns:
        RerankerResponse: The reranked results with scores
    """
    try:
        # Convert documents to Artifacts
        artifacts = [
            Artifact(artifact_type=ArtifactType.TEXT,
                     content=doc.content,
                     metadata=doc.metadata) for doc in request.documents
        ]

        # Get reranker instance
        runner = get_reranker()

        # Run reranking
        results = runner.run(query=request.query,
                             documents=artifacts,
                             score_threshold=request.score_threshold,
                             top_n=request.top_n)

        # Convert results to response format
        response_results = [{
            "index": result.artifact.metadata.get("index", idx),
            "text": result.artifact.content,
            "metadata": result.artifact.metadata,
            "score": result.score,
        } for idx, result in enumerate(results)]

        return RerankerResponse(docs=response_results,
                                model=runner.config.model_name)

    except Exception as e:
        logger.error(f"Error during reranking: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Error during reranking: {str(e)}")


@app.post("/dify/rerank")
async def rerank(request: RerankerRequest) -> dict:
    """
    Rerank documents based on a query.
    Args:
        request (RerankerRequest): The rerank request containing query and documents
    Returns:
        RerankerResponse: The reranked results with scores
    """
    try:
        # Convert documents to Artifacts
        artifacts = [
            Artifact(artifact_type=ArtifactType.TEXT,
                     content=doc.content,
                     metadata=doc.metadata) for doc in request.documents
        ]

        # Get reranker instance
        runner = get_reranker()

        # Run reranking
        results = runner.run(query=request.query,
                             documents=artifacts,
                             score_threshold=request.score_threshold,
                             top_n=request.top_n)

        # Convert results to response format
        response_results = [{
            "index": result.artifact.metadata.get("index", idx),
            "text": result.artifact.content,
            "metadata": result.artifact.metadata,
            "relevance_score": result.score,
        } for idx, result in enumerate(results)]

        return {"results": response_results, "model": runner.config.model_name}

    except Exception as e:
        logger.error(f"Error during reranking: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Error during reranking: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try to access the reranker to check if it's initialized
        get_reranker()
        return {"status": "healthy", "model": "initialized"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run("workspacex.reranker.server.reranker_server:app",
                host="0.0.0.0",
                port=int(os.getenv("RERANKER_PORT", "8000")),
                reload=os.getenv("RERANKER_RELOAD", "False") == "True")
