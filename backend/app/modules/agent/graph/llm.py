"""LangGraph 引擎 LLM 工厂（P2）

DeepSeek 优先、失败自动降级 Qwen —— 与 legacy 主循环里的降级行为一致。
每次 ainvoke 前按本轮意图过滤后的工具集 bind_tools。
"""
import logging

from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger("agent.graph.llm")


class ChatLLMWithFallback:
    """带降级链的 ChatOpenAI 包装器"""

    def __init__(self, temperature: float = 0.7):
        self._backends: list[tuple[str, str, ChatOpenAI]] = []
        if settings.DEEPSEEK_API_KEY:
            self._backends.append(("deepseek", settings.DEEPSEEK_MODEL, ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=temperature,
            )))
        if settings.QWEN_API_KEY:
            self._backends.append(("qwen", settings.QWEN_MODEL, ChatOpenAI(
                model=settings.QWEN_MODEL,
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
                temperature=temperature,
            )))
        if not self._backends:
            raise RuntimeError("LLM 未配置：至少需要 DEEPSEEK 或 QWEN 之一")
        self._preferred = 0
        self.last_model = f"{self._backends[0][0]}:{self._backends[0][1]}"

    async def ainvoke(self, messages, tool_schemas: list[dict] | None = None):
        """按优先级调用，失败自动切下一个后端；tool_schemas 为 OpenAI 格式 dict 列表"""
        errors = []
        for offset in range(len(self._backends)):
            idx = (self._preferred + offset) % len(self._backends)
            name, model, llm = self._backends[idx]
            try:
                bound = llm.bind_tools(tool_schemas) if tool_schemas else llm
                resp = await bound.ainvoke(messages)
                self._preferred = idx
                self.last_model = f"{name}:{model}"
                return resp
            except Exception as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"[GraphLLM] {name}:{model} 调用失败，尝试降级: {e}")
        raise RuntimeError("所有 LLM 后端调用失败 | " + " ; ".join(errors))
