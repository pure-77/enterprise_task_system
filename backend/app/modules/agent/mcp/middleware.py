"""MCP 鉴权中间件 — 把 Authorization 头写入 ContextVar，供工具执行时读取

MCP 是「一次调用一次请求」，FastAPI 的 Depends(get_current_user) 进不来，
ORM 对象也无法随请求序列化传递，因此在 ASGI 层把 token 暂存到 ContextVar，
工具执行时再由 auth.resolve_context() 解码并重建业务 context。

P6：顺带记录每个 MCP 请求的耗时/状态码到 trace（kind=mcp），
使 trace 能看到「Agent → MCP 工具调用」这条链路。
"""
import time
from contextvars import ContextVar

from app.modules.agent.graph.trace import record_mcp_request

_token: ContextVar[str | None] = ContextVar("mcp_token", default=None)


class McpAuthMiddleware:
    """纯 ASGI 中间件：提取 Bearer token 写入 ContextVar"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        raw = headers.get(b"authorization", b"").decode()
        if raw.lower().startswith("bearer "):
            _token.set(raw[7:])

        start = time.time()
        status_code = 0

        async def _send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            record_mcp_request(
                scope.get("method", ""),
                scope.get("path", ""),
                status_code or 500,
                int((time.time() - start) * 1000),
            )
