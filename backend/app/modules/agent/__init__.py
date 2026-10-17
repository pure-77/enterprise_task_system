"""Agent 模块 — 企业办公智能助手

通过 LLM Function Calling 将业务 API 包装为可调用工具，
支持多 LLM 路由（DeepSeek 推理 + 千问 VL 多模态）、对话记忆、
工具分组路由等能力。
"""
from app.modules.agent.router import router

__all__ = ["router"]
