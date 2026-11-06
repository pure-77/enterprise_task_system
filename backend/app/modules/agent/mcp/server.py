"""FastMCP 实例 + ASGI 工厂

按安装版本选择传输实现（6.4 探测结论：mcp 1.30.0 暴露 streamable_http_app）。
stateless_http=True：每次请求独立会话，适配「一次调用一次请求」的无状态部署。
"""
from mcp.server.fastmcp import FastMCP

# streamable_http_path="/"：挂载到 /mcp 后，客户端请求 /mcp/ 即可命中（默认 "/mcp" 会错成 /mcp/mcp）
mcp = FastMCP("personal-task-agent", stateless_http=True, streamable_http_path="/")


def build_mcp_asgi():
    """返回挂好鉴权中间件的 MCP ASGI 应用"""
    from app.modules.agent.mcp.middleware import McpAuthMiddleware
    from app.modules.agent.mcp import adapters  # noqa: F401  触发 5 个工具注册

    if hasattr(mcp, "streamable_http_app"):
        return McpAuthMiddleware(mcp.streamable_http_app())
    return McpAuthMiddleware(mcp.http_app(path="/"))  # fastmcp 2.x 兜底
