"""Agent 模块 — LLM Provider 抽象层

设计思路：
- 统一接口 LLMProvider.chat()，屏蔽不同厂商 SDK 差异
- DeepSeek 和千问都走 OpenAI 兼容协议，只需换 base_url + api_key
- 提供工厂函数 get_llm() 根据场景自动选择引擎

后续如需接入更多模型（豆包、本地 Ollama…），只需新增实现类即可。
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger("agent.llm")


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> object:
        """
        调用 LLM 完成一次对话（非流式）

        Args:
            messages: OpenAI 格式的 messages 列表
            tools: OpenAI 格式的 tools (Function Calling)
            temperature: 采样温度

        Returns:
            openai.types.chat.ChatCompletion 对象
        """
        ...

    async def chat_stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ):
        """
        流式调用 LLM（默认降级为非流式 yield 一次完整内容）
        子类应覆盖此方法实现真正的流式输出
        """
        resp = await self.chat(messages=messages, tools=tools, temperature=temperature)
        content = resp.choices[0].message.content or ""
        # yield 一个 token 一次，模拟流式
        for char in content:
            yield char

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前使用的模型名称（用于日志和响应）"""
        ...


class DeepSeekProvider(LLMProvider):
    """DeepSeek 推理引擎（默认）"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self._model = settings.DEEPSEEK_MODEL

    @property
    def model_name(self) -> str:
        return f"deepseek:{self._model}"

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ):
        kwargs = dict(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            return resp
        except Exception as e:
            logger.error(f"[DeepSeek] 调用失败: {e}")
            raise


class QwenVLProvider(LLMProvider):
    """通义千问 VL — 多模态图片理解"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        self._model = settings.QWEN_VL_MODEL

    @property
    def model_name(self) -> str:
        return f"qwen-vl:{self._model}"

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ):
        kwargs = dict(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            return resp
        except Exception as e:
            logger.error(f"[QwenVL] 调用失败: {e}")
            raise


class QwenTextProvider(LLMProvider):
    """通义千问 — 纯文本推理（备选/降级用）"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        self._model = settings.QWEN_MODEL

    @property
    def model_name(self) -> str:
        return f"qwen:{self._model}"

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ):
        kwargs = dict(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            return resp
        except Exception as e:
            logger.error(f"[Qwen] 调用失败: {e}")
            raise


# ==================== 工厂 / 路由 ====================

def get_llm(has_image: bool = False, use_qwen: bool = False) -> LLMProvider:
    """
    获取合适的 LLM Provider

    选择逻辑：
    - 检测到图片输入 → QwenVLProvider（多模态理解）
    - 强制指定千问 → QwenTextProvider（降级/测试用）
    - 默认 → DeepSeekProvider

    Args:
        has_image: 本次请求是否包含图片
        use_qwen: 是否强制使用千问文本模型

    Returns:
        LLMProvider 实例
    """
    if has_image:
        return QwenVLProvider()
    if use_qwen:
        return QwenTextProvider()
    return DeepSeekProvider()
