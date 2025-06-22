import asyncio
import logging
from typing import List
from workspacex.artifact import Artifact, ArtifactType
from workspacex.embedding.base import EmbeddingsConfig
from workspacex.embedding.ollama import OllamaEmbeddings
from workspacex.vector.dbs.chroma import ChromaVectorDB
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)

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
    
    # Initialize ChromaDB client
    vector_store = ChromaVectorDB()
    
    # Create sample artifacts
    artifacts = [
        Artifact(
            artifact_type=ArtifactType.TEXT,
            content="Paris is the capital of France.",
            metadata={"source": "geography", "category": "cities"}
        ),
        Artifact(
            artifact_type=ArtifactType.TEXT,
            content="Berlin is the capital of Germany.",
            metadata={"source": "geography", "category": "cities"}
        ),
        Artifact(
            artifact_type=ArtifactType.TEXT,
            content="The Eiffel Tower is located in Paris.",
            metadata={"source": "landmarks", "category": "attractions"}
        )
    ]
    
    # Generate embeddings for artifacts
    print("\nGenerating embeddings...")
    embedding_results = embeddings.embed_artifacts(artifacts)
    
    # Store embeddings in ChromaDB
    collection_name = "cities_demo"
    print(f"\nStoring embeddings in collection: {collection_name}")
    
    # Delete collection if it exists (for demo purposes)
    if vector_store.has_collection(collection_name):
        logging.info(f"Deleting collection: {collection_name}")
        vector_store.delete_collection(collection_name)
    
    # Insert embeddings
    vector_store.insert(collection_name, embedding_results)
    
    # Example 1: Search by vector similarity
    print("\nSearching similar documents to 'capital city in Europe'...")
    query = "capital city in Europe"
    query_embedding = embeddings.embed_query(query)
    search_results = vector_store.search(
        collection_name=collection_name,
        vectors=[query_embedding],
        limit=2,
        filter={},
        threshold=0.5
    )
    
    if search_results and search_results.docs:
        print("\nSearch results:")
        for doc in search_results.docs:
            print(f"Content: {doc.content}")
            print(f"Metadata: {doc.metadata}")
            print(f"Similarity Score: {doc.score:.4f}" if doc.score is not None else "Score: N/A")
            print("---")
    
    # Example 2: Query by metadata filter
    print("\nQuerying documents about landmarks...")
    filter_query = {"category": "attractions"}
    filter_results = vector_store.query(
        collection_name=collection_name,
        filter=filter_query
    )
    
    if filter_results and filter_results.docs:
        print("\nFilter results:")
        for doc in filter_results.docs:
            print(f"ID: {doc.id}")
            print(f"Content: {doc.content}")
            print(f"Metadata: {doc.metadata}")
            print(f"Score: {doc.score}" if doc.score is not None else "Score: N/A")
            print("---")
    
    # Example 3: Get all documents
    print("\nRetrieving all documents...")
    all_results = vector_store.get(collection_name)
    
    if all_results and all_results.docs:
        print("\nAll documents:")
        for doc in all_results.docs:
            print(f"Content: {doc.content}")
            print(f"Metadata: {doc.metadata}")
            print(f"Score: {doc.score}" if doc.score is not None else "Score: N/A")
            print("---")

if __name__ == "__main__":
    asyncio.run(main()) 