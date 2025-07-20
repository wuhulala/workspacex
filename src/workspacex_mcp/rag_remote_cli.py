import os
from typing import Dict, Any

import aiohttp
from fastmcp import FastMCP, Context

from workspacex.artifact import ArtifactType

# 创建FastMCP实例
mcp = FastMCP("WorkspaceX Remote RAG Tools 🔍")

class MCPConfig:
    """MCP client configuration"""
    def __init__(
        self
    ):
        # Priority: constructor param > env var > default
        self.workspace_id = os.getenv("WORKSPACE_ID", "test")
        self.api_base = os.getenv("WORKSPACE_API_BASE", "http://localhost:9588")
        self.threshold = float(os.getenv("WORKSPACE_SEARCH_THRESHOLD", 0.8))
        self.filter_types = os.getenv("WORKSPACE_FILTER_TYPES", None)

@mcp.tool
async def rag_search(
    query: str,
    limit: int = 3,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Search artifacts in the workspace using semantic search.
    
    Args:
        query: The search query text
        limit: Maximum number of results to return (default: 3)
        ctx: MCP context (automatically injected)
        
    Returns:
        Dict containing search results or error message
    """
    config = MCPConfig()
    
    try:
        # 使用aiohttp进行HTTP请求
        await ctx.info(f"Searching for: {query}")
        
        # 转换过滤类型（如果提供）
        artifact_types = None
        if config.filter_types:
            artifact_types = [ArtifactType(t) for t in config.filter_types]
        
        # 使用aiohttp进行异步HTTP请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.api_base}/api/v1/workspaces/{config.workspace_id}/search_artifacts",
                json={
                    "query": query,
                    "limit": limit,
                    "threshold": config.threshold,
                    "filter_types": [t.value for t in artifact_types] if artifact_types else None
                }
            ) as response:
                status_code = response.status
                if status_code != 200:
                    error_text = await response.text()
                    await ctx.error(f"Search failed with status {status_code}")
                    return {"error": f"Search failed: {error_text}"}
                
                results = await response.json()
                content = f"Found {len(results)} results\n"
                for i,result in enumerate(results):
                    content += f"Result#{i} {result['artifact']['artifact_id']} \n {result['artifact']['content']}\n\n"
                await ctx.info(f"Found {len(results)} results")
                return {"result": content}
    
    except Exception as e:
        await ctx.error(f"Error during search: {str(e)}")
        return {"error": f"Search failed: {str(e)}"}

if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run()
