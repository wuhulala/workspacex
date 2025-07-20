import os
from typing import Dict, Any

from fastmcp import FastMCP, Context

from workspacex.artifact import ArtifactType
from workspacex.base import WorkspaceConfig
from workspacex.utils.common import load_workspace

mcp = FastMCP("WorkspaceX Local RAG Tools 🔍")

class MCPConfig:
    """MCP client configuration"""
    def __init__(
        self,
        workspace_config: WorkspaceConfig = None
    ):
        # Priority: constructor param > env var > default
        self.workspace_id = os.getenv("WORKSPACE_ID", "test")
        self.workspace_type = os.getenv("WORKSPACE_TYPE", "local")
        self.threshold = os.getenv("SEARCH_THRESHOLD", 0.8)
        self.filter_types = os.getenv("FILTER_TYPES", None)
        self.workspace_config = workspace_config or WorkspaceConfig()
        
        self._load_workspace()

    async def _load_workspace(self):
        self.workspace = await load_workspace(self.workspace_id, self.workspace_type, config=self.workspace_config)


@mcp.tool
async def rag_search(
    query: str,
    limit: int = 10,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Search artifacts in the workspace using semantic search.
    
    Args:
        query: The search query text
        limit: Maximum number of results to return (default: 10)
        threshold: Similarity threshold for results (default: 0.8)
        filter_types: Optional list of artifact types to filter (e.g. ["CODE", "NOVEL"])
        ctx: MCP context (automatically injected)
        
    Returns:
        Dict containing search results or error message
    """
    config = MCPConfig()
    
    try:
        # 使用Context进行HTTP请求
        await ctx.info(f"Searching for: {query}")
        
        # 转换过滤类型（如果提供）
        artifact_types = None
        if config.filter_types:
            artifact_types = [ArtifactType(t) for t in config.filter_types]
        
        results = await config.workspace.search_artifacts(query, limit, config.threshold, artifact_types)
        
        await ctx.info(f"Found {len(results.get('results', []))} results")
        return results
    
    except Exception as e:
        await ctx.error(f"Error during search: {str(e)}")
        return {"error": f"Search failed: {str(e)}"}

if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run()
