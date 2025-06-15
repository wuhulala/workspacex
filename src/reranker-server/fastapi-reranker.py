from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import logging
from workspacex.reranker.base import RerankConfig
from workspacex.reranker.local import Qwen3RerankerRunner
from workspacex.artifact import Artifact, ArtifactType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Reranker API",
    description="A FastAPI service for reranking documents using Qwen3-Reranker",
    version="1.0.0"
)

class Document(BaseModel):
    """Document model for reranking"""
    content: str = Field(..., description="The document content to rerank")
    metadata: dict = Field(default_factory=dict, description="Optional metadata")

class RerankerRequest(BaseModel):
    """Request model for reranking"""
    query: str = Field(..., description="The search query")
    documents: List[Document] = Field(..., description="List of documents to rerank")
    score_threshold: Optional[float] = Field(None, description="Optional score threshold")
    top_n: Optional[int] = Field(None, description="Optional top N results to return")

class RerankerResponse(BaseModel):
    """Response model for reranking results"""
    results: List[dict] = Field(..., description="Ranked results with scores")

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
                model_name="Qwen/Qwen3-Reranker-0.6B",
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
            Artifact(
                artifact_type=ArtifactType.TEXT,
                content=doc.content,
                metadata=doc.metadata
            ) for doc in request.documents
        ]

        # Get reranker instance
        runner = get_reranker()

        # Run reranking
        results = runner.run(
            query=request.query,
            documents=artifacts,
            score_threshold=request.score_threshold,
            top_n=request.top_n
        )

        # Convert results to response format
        response_results = [
            {
                "content": result.artifact.content,
                "metadata": result.artifact.metadata,
                "score": result.score
            }
            for result in results
        ]

        return RerankerResponse(results=response_results)

    except Exception as e:
        logger.error(f"Error during reranking: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during reranking: {str(e)}"
        )

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
    # Add FastAPI to optional dependencies if not already present
    uvicorn.run(
        "fastapi-reranker:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
