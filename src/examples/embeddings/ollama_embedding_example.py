
import asyncio
import os
from typing import List
from workspacex.artifact import Artifact, ArtifactType
from workspacex.embedding.base import EmbeddingsConfig
from workspacex.embedding.ollama import OllamaEmbeddings
from workspacex.utils.logger import logger
from dotenv import load_dotenv

logging.basicConfig(level=logger.info)

async def main():
    load_dotenv()   
    # Create embedding configuration
    config = EmbeddingsConfig(
        model_name="nomic-embed-text",  # Using nomic-embed-text model
        base_url=os.getenv("OLLAMA_BASE_URL"),  # Default Ollama URL
        timeout=30,  # 30 seconds timeout
        api_key="ollama-api-key"
    )
    
    # Initialize Ollama embeddings
    embeddings = OllamaEmbeddings(config)
    
    # Create sample artifacts
    artifacts = [
        Artifact(
            artifact_type=ArtifactType.TEXT,
            content="This is the first sample text for embedding."
        ),
        Artifact(
            artifact_type=ArtifactType.TEXT,
            content="This is another sample text for embedding."
        )
    ]
    
    # Example 1: Synchronous embedding
    print("Running synchronous embedding...")
    results = embeddings.embed_artifacts(artifacts)
    for result in results:
        print(f"Artifact content: {result.artifact.content}")
        print(f"Embedding dimension: {len(result.embedding)}")
        print(f"Model used: {result.embedding_model}")
        print("---")
    
    # Example 2: Asynchronous embedding
    print("\nRunning asynchronous embedding...")
    async_results = await embeddings.async_embed_artifacts(artifacts)
    for result in async_results:
        print(f"Artifact content: {result.artifact.content}")
        print(f"Embedding dimension: {len(result.embedding)}")
        print(f"Model used: {result.embedding_model}")
        print("---")
    
    # Example 3: Single query embedding
    print("\nRunning single query embedding...")
    query = "This is a test query"
    embedding = embeddings.embed_query(query)
    print(f"Query: {query}")
    print(f"Embedding dimension: {len(embedding)}")

if __name__ == "__main__":
    asyncio.run(main())
