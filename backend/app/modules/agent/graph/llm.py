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

    async def astream_collect(
        self,
        messages,
        tool_schemas: list[dict] | None = None,
    ):
        """流式 LLM 调用：底层用 astream，逐 token yield content 文本片段，
        循环结束后 self._last_aimessage 持有完整 AIMessage（LangGraph State 需要）。

        调用方用法：
          async for text_piece in llm.astream_collect(messages, tool_schemas):
              # text_piece: 单段 content 增量字符串（tool_calls 轮次里可能为空字符串）
              writer(streaming.message(text_piece))
          full = llm._last_aimessage  # 完整 AIMessage，含 tool_calls 等
        """
        from langchain_core.messages import AIMessage, AIMessageChunk

        self._last_aimessage: AIMessage | None = None
        errors = []
        for offset in range(len(self._backends)):
            idx = (self._preferred + offset) % len(self._backends)
            name, model, llm = self._backends[idx]
            try:
                bound = llm.bind_tools(tool_schemas) if tool_schemas else llm
                accumulated: AIMessageChunk | None = None
                async for chunk in bound.astream(messages):
                    if accumulated is None:
                        accumulated = chunk
                    else:
                        accumulated += chunk
                    # tool_calls 增量片段（含 tool_call_incremental_chunk / tool_calls 数组更新）
                    # 和 content 文本片段是两种不同的 chunk，这里只 yield 纯文本
                    text_piece = getattr(chunk, "content", None)
                    if isinstance(text_piece, str) and text_piece:
                        yield text_piece
                self._preferred = idx
                self.last_model = f"{name}:{model}"
                if accumulated is None:
                    raise RuntimeError(f"{name}:{model} 未返回任何内容")
                # AIMessageChunk → AIMessage
                self._last_aimessage = (
                    accumulated.to_message()
                    if hasattr(accumulated, "to_message")
                    else AIMessage(
                        content=accumulated.content or "",
                        tool_calls=getattr(accumulated, "tool_calls", None),
                        usage_metadata=getattr(accumulated, "usage_metadata", None),
                        response_metadata=getattr(accumulated, "response_metadata", None),
                    )
                )
                return  # 成功，不再尝试降级后端
            except Exception as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"[GraphLLM] {name}:{model} astream 失败，尝试降级: {e}")
        raise RuntimeError("所有 LLM 后端调用失败 | " + " ; ".join(errors))
