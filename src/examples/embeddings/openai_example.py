import asyncio
import logging
import os
from workspacex.embedding.openai_compatible import OpenAICompatibleEmbeddings
from workspacex.embedding.base import EmbeddingsConfig, EmbeddingsResult
from workspacex.artifact import Artifact, ArtifactType
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
load_dotenv()
# Example configuration (replace with your real API key and endpoint)
config = EmbeddingsConfig(
    api_key=os.getenv("OPENAI_API_KEY"),  # Replace with your OpenAI API key
    model_name="text-embedding-v4",  # Or your compatible model
    base_url=os.getenv("BASE_URL"),  # Or your compatible endpoint
    timeout=60
)

# Create the embedding client
embedder = OpenAICompatibleEmbeddings(config)

# Example: embed a single query
query = "What is the capital of France?"
embedding = embedder.embed_query(query)
print(f"Query embedding: {embedding[:8]}... (length={len(embedding)})")

# Example: embed a list of artifacts
artifacts = [
    Artifact(artifact_type=ArtifactType.TEXT, content="Paris is the capital of France.", metadata={}),
    Artifact(artifact_type=ArtifactType.TEXT, content="Berlin is the capital of Germany.", metadata={}),
]
results = embedder.embed_artifacts(artifacts)
for i, result in enumerate(results):
    print(f"Artifact {i} embedding: {result.embedding[:8]}... (length={len(result.embedding)})")

# Example: async usage
def run_async_example():
    async def main():
        async_embedding = await embedder.async_embed_query(query)
        print(f"[Async] Query embedding: {async_embedding[:8]}... (length={len(async_embedding)})")
        async_results = await embedder.async_embed_artifacts(artifacts)
        for i, result in enumerate(async_results):
            print(f"[Async] Artifact {i} embedding: {result.embedding[:8]}... (length={len(result.embedding)})")
    asyncio.run(main())

if __name__ == "__main__":
    run_async_example()
