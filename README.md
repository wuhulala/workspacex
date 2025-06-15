# workspacex

**workspacex** is a Python library for managing AIGC (AI-Generated Content) artifacts. It provides a collaborative workspace environment for handling multiple artifacts with features like version control, update notifications, artifact management, and pluggable storage and embedding backends.

---

## Features

- **Artifact Management**: Create, update, and manage different types of artifacts (text, code, etc.)
- **Workspace Organization**: Group related artifacts in collaborative workspaces
- **Storage Backends**: Local file system and S3-compatible storage (via `s3fs`)
- **Embedding Backends**: OpenAI-compatible and Ollama embedding support
- **Reranking**: Local reranking using Qwen3-Reranker models
- **HTTP Service**: FastAPI-based reranking service

---

## Installation

### Basic Installation
```bash
pip install workspacex
```

### With Reranker Support
```bash
pip install "workspacex[reranker]"  # For using reranker in your code
pip install "workspacex[reranker-server]"  # For running the reranker HTTP service
```

Using Poetry:
```bash
poetry install --extras "reranker-server"  # Installs all features
```

---

## Usage

### Basic Example

```python
import asyncio
import logging

from workspacex import WorkSpace, ArtifactType

if __name__ == '__main__':
    workspace = WorkSpace.from_local_storages(workspace_id="demo")
    asyncio.run(workspace.create_artifact(ArtifactType.TEXT, "artifact_001"))
```

### Using the Reranker

```python
from workspacex.reranker.base import RerankConfig
from workspacex.reranker.local import Qwen3RerankerRunner
from workspacex.artifact import Artifact, ArtifactType

# Initialize reranker
config = RerankConfig(
    model_name="Qwen/Qwen3-Reranker-0.6B",  # or "Qwen/Qwen3-Reranker-8B"
    api_key="not_needed",  # Local model doesn't need these
    base_url="not_needed"
)
reranker = Qwen3RerankerRunner(config)

# Create some test documents
documents = [
    Artifact(artifact_type=ArtifactType.TEXT, content="Python is a programming language."),
    Artifact(artifact_type=ArtifactType.TEXT, content="Python is a type of snake.")
]

# Rerank documents
results = reranker.run(
    query="What is Python programming?",
    documents=documents,
    top_n=2
)

# Print results
for result in results:
    print(f"Score: {result.score}, Content: {result.artifact.content}")
```

### Running the Reranker Server

1. Install server dependencies:
```bash
pip install "workspacex[reranker-server]"
```

2. Start the server:
```bash
python -m workspacex.reranker.server.reranker_server
```

> Default model: Qwen/Qwen3-Reranker-0.6B
> 
> To download the model first:
> ```bash
> # Install huggingface_hub
> pip install -U huggingface_hub
> 
> # Set mirror for faster download in China
> export HF_ENDPOINT=https://hf-mirror.com
> 
> # Download the model
> huggingface-cli download --resume-download Qwen/Qwen3-Reranker-0.6B --local-dir Qwen/Qwen3-Reranker-0.6B
> ```

```
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B  # or Qwen/Qwen3-Reranker-8B
RERANKER_PORT=8000
RERANKER_RELOAD=False
```

The server will start on http://localhost:8000 with the following endpoints:
- POST `/rerank`: Main reranking endpoint
- POST `/dify/rerank`: Dify-compatible reranking endpoint
- GET `/health`: Health check endpoint
- Interactive API docs at `/docs` and `/redoc`



Example API usage:
```bash
# Using Document objects (recommended)
curl -X POST "http://localhost:8000/rerank" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is Python?",
       "documents": [
         {
           "content": "Python is a programming language.",
           "metadata": {}
         },
         {
           "content": "Python is a type of snake.",
           "metadata": {}
         }
       ],
       "top_n": 2,
       "score_threshold": 0.5
     }'

# Using simple strings (also supported)
curl -X POST "http://localhost:8000/rerank" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is Python?",
       "documents": [
         "Python is a programming language.",
         "Python is a type of snake."
       ],
       "top_n": 2
     }'
```

Response format:
```json
{
  "docs": [
    {
      "index": 0,
      "text": "Python is a programming language.",
      "metadata": {"index": 0},
      "score": 0.9954494833946228
    },
    {
      "index": 1,
      "text": "Python is a type of snake.",
      "metadata": {"index": 1},
      "score": 0.8291763067245483
    }
  ],
  "model": "Qwen/Qwen3-Reranker-0.6B"
}
```

### Dify Integration

For Dify compatibility, use the `/dify/rerank` endpoint:

```bash
curl -X POST "http://localhost:8000/dify/rerank" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is Python?",
       "documents": [
         "Python is a programming language.",
         "Python is a type of snake."
       ],
       "top_n": 2
     }'
```

Dify response format:
```json
{
  "results": [
    {
      "index": 0,
      "text": "Python is a programming language.",
      "metadata": {"index": 0},
      "relevance_score": 0.9954494833946228
    },
    {
      "index": 1,
      "text": "Python is a type of snake.",
      "metadata": {"index": 1},
      "relevance_score": 0.8291763067245483
    }
  ],
  "model": "Qwen/Qwen3-Reranker-0.6B"
}
```

### Endpoint Differences

The server provides two reranking endpoints with different response formats:

| Feature | `/rerank` | `/dify/rerank` |
|---------|-----------|----------------|
| Response field | `docs` | `results` |
| Score field | `score` | `relevance_score` |
| Text field | `text` | `text` |
| Index tracking | ✅ | ✅ |
| Model info | ✅ | ✅ |
| Use case | General purpose | Dify integration |

### Storage Backends

- **Local**: Default, stores data in the local file system.
  ```python
  from workspacex.storage.local import LocalPathRepository
  repo = LocalPathRepository("data/workspaces/demo")
  ```
- **S3**: Store artifacts in S3-compatible storage.
  ```python
  from workspacex.storage.s3 import S3Repository
  repo = S3Repository(storage_path="demo", bucket="your-bucket", s3_kwargs={"key": "...", "secret": "..."})
  ```

### Embedding Backends

- **OpenAI-Compatible**:
  ```python
  from workspacex.embedding.openai_compatible import OpenAICompatibleEmbeddings, EmbeddingsConfig
  config = EmbeddingsConfig(api_key="sk-...", base_url="https://api.openai.com/v1", model_name="text-embedding-ada-002")
  embedder = OpenAICompatibleEmbeddings(config)
  ```
- **Ollama**:
  ```python
  from workspacex.embedding.ollama import OllamaEmbeddings, OllamaConfig
  config = OllamaConfig(model="nomic-embed-text", base_url="http://localhost:11434")
  embedder = OllamaEmbeddings(config)
  ```

### Example Scripts

- See `src/examples/` for ready-to-run scripts:
  - `noval_example.py`
  - `embeddings/openai_example.py`
  - `embeddings/ollama_embedding_example.py`
  - `image_examples.py`

Run an example:
```bash
export PYTHONPATH=src
python src/examples/embeddings/openai_example.py
```

---

## Notes

- All source code is under `src/`.
- Make sure to activate the correct conda environment before using Poetry commands or running code.
- If you see `ModuleNotFoundError: No module named 'workspacex'`, ensure your `PYTHONPATH` includes `src`.
- Storage and embedding backends are pluggable and extensible.
- For S3 support, install `s3fs` and configure credentials as needed.
- For reranking, CUDA is recommended for better performance.
- The reranker server supports both CPU and GPU inference.

---

Let me know if you want to add more details, such as advanced usage, API docs, or contribution guidelines!
