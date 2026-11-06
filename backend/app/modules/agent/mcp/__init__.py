"""Agent MCP 工具服务（P1：5 个只读工具的外部入口）

通过 FastMCP 将现有只读工具以标准 MCP 协议（Streamable HTTP）暴露给外部客户端。
身份上下文经 McpAuthMiddleware（Authorization 头 → ContextVar）传递，
Adapter 只做参数透传与身份装配，业务逻辑全部复用原 handler，一行不改。
"""
from app.modules.agent.mcp import adapters  # noqa: F401  触发 5 个工具注册
