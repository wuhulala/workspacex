# workspacex
workspacex is a Python library for managing AIGC (AI-Generated Content) artifacts. It provides a collaborative workspace environment for handling multiple artifacts with features like version control, update notifications, and artifact management. The library supports various artifact types and includes an observer pattern for event handling.

## Features

- **Artifact Management**: Create, update, and manage different types of artifacts (text, code, etc.)
- **Version Control**: Track changes and maintain version history for artifacts
- **Workspace Organization**: Group related artifacts in collaborative workspaces
- **Event Handling**: Observer pattern for artifact creation and updates
- **Storage**: Local storage support with extensible repository system
- **Type Safety**: Built with Pydantic for robust data validation
- **Async Support**: Asynchronous operations for better performance
- [-] Remote Storeage
- [-] MCP supported

## Project Structure

```
workspacex/
  src/
    workspacex/   # Main package code
    examples/     # Example scripts
```

## Environment Setup


1. **Install dependencies**
   ```bash
   poetry install
   ```

## Add dependencies

```bash
poetry add <package-name>
```

## Usage

- To run example scripts, use:
  ```bash
  python -m workspacex.<module>
  ```
  or set the `PYTHONPATH`:
  ```bash
  export PYTHONPATH=src
  python src/examples/your_example.py
  ```

examples:
```
import asyncio
import logging

from workspacex import WorkSpace
from workspacex import ArtifactType
from workspacex.observer import on_artifact_create, get_observer


@on_artifact_create
async def handle_artifact_create(artifact):
    logging.info(f"Artifact created: {artifact.artifact_id}")


@on_artifact_create(workspace_id="demo", filters={"artifact_type": "text"})
async def handle_specific_artifacts(artifact, **kwargs):
    logging.info(f"text artifact created in specific workspace {kwargs['workspace_id']}: {artifact.artifact_id}")


class DemoClass:
    def __init__(self):
        observer = get_observer()
        observer.register_create_handler(
            self.artifact_create,
            instance=self,
            workspace_id="demo"
        )

    async def artifact_create(self, artifact, **kwargs):
        logging.info(f"DemoClass : text artifact created in specific workspace {kwargs['workspace_id']}: {artifact.artifact_id}")


if __name__ == '__main__':
    DemoClass()
    workspace = WorkSpace.from_local_storages(workspace_id="demo")
    asyncio.run(workspace.create_artifact(ArtifactType.TEXT, "artifact_001"))
```
you can see it in `data/workspaces`

```shell
❯ tree .
.
└── workspaces
    └── demo
        ├── artifact_e4114394ca07a57fea465936b5c80d69e7754c75674521dd07cad9d8e77d3036.json
        ├── index.json
        └── workspace_67b60981fd59b82e1c50826d15af5449fb6dcd53017aa7a2e31ade4df88a4b76.json
```

## Notes
- All source code is under `src/`.
- Make sure to activate the correct conda environment before using Poetry commands or running code.
- If you see `ModuleNotFoundError: No module named 'workspacex'`, ensure your `PYTHONPATH` includes `src`.
