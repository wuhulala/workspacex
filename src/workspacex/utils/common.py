import os

from workspacex import WorkSpace
from workspacex.base import WorkspaceConfig


async def load_workspace(workspace_id, workspace_type, storage_path, config: WorkspaceConfig = None) -> WorkSpace:
    if workspace_type == "local":
        parent_dir = os.environ.get("WORKSPACEX_LOCAL_BASE_DIR", "data/workspaces")
        return WorkSpace.from_local_storages(workspace_id=workspace_id, storage_path=parent_dir + "/" + workspace_id, config = config)
    elif workspace_type == "s3":
        return WorkSpace.from_s3_storages(workspace_id=workspace_id, storage_path=storage_path, config = config)
    else:
        raise ValueError(f"not support workspace#{workspace_type}: {workspace_id}")

def sync_load_workspace(workspace_id, workspace_type, storage_path, config: WorkspaceConfig = None) -> WorkSpace:
    if workspace_type == "local":
        parent_dir = os.environ.get("WORKSPACEX_LOCAL_BASE_DIR", "data/workspaces")
        return WorkSpace.from_local_storages(workspace_id=workspace_id, storage_path=parent_dir + "/" + workspace_id, config = config)
    elif workspace_type == "s3":
        return WorkSpace.from_s3_storages(workspace_id=workspace_id, storage_path=storage_path, config = config)
    else:
        raise ValueError(f"not support workspace#{workspace_type}: {workspace_id}")
