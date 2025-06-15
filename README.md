# workspacex

**workspacex** is a Python library for managing AIGC (AI-Generated Content) artifacts. It provides a collaborative workspace environment for handling multiple artifacts with features like version control, update notifications, artifact management, and pluggable storage and embedding backends.

---

## Features

- **Artifact Management**: Create, update, and manage different types of artifacts (text, code, etc.)
- **Version Control**: Track changes and maintain version history for artifacts
- **Workspace Organization**: Group related artifacts in collaborative workspaces
- **Event Handling**: Observer pattern for artifact creation and updates
- **Storage Backends**: Local file system and S3-compatible storage (via `s3fs`)
- **Embedding Backends**: OpenAI-compatible and Ollama embedding support
- **Type Safety**: Built with Pydantic for robust data validation
- **Async Support**: Asynchronous operations for better performance
- **Extensible**: Easy to add new storage, embedding, extractor, and reranker backends

---

## Project Structure

```
workspacex/
  src/
    workspacex/   # Main package code
      artifact.py
      code_artifact.py
      workspace.py
      observer.py
      storage/
        local.py
        s3.py
        base.py
      embedding/
        openai_compatible.py
        ollama.py
        base.py
      extractor/
        noval_extractor.py
        base.py
      reranker/
        base.py
      utils/
        timeit.py
    examples/     # Example scripts
      embeddings/
      data/
      novel_chapters/
```

---

## Environment Setup

1. **Install dependencies**
   ```bash
   poetry install
   ```

2. **Activate the conda environment**
   ```bash
   conda activate rl
   ```

---

## Usage

### Basic Example

```python
import asyncio
import logging

from workspacex import WorkSpace, ArtifactType, get_observer, on_artifact_create

@on_artifact_create
async def handle_artifact_create(artifact):
    logging.info(f"Artifact created: {artifact.artifact_id}")

if __name__ == '__main__':
    workspace = WorkSpace.from_local_storages(workspace_id="demo")
    asyncio.run(workspace.create_artifact(ArtifactType.TEXT, "artifact_001"))
```

Artifacts and workspace data will be stored in `data/workspaces`.

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

---

Let me know if you want to add more details, such as advanced usage, API docs, or contribution guidelines!
