"""LangGraph 对话状态定义（P2）"""
import operator
from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # 对话消息（LangChain Message 对象，add_messages 去重合并）
    messages: Annotated[list, add_messages]
    # 意图分组：None=全量工具；list[str]=命中的工具组
    intent_groups: Optional[list[str]]
    # 本轮过滤后的工具集（OpenAI function schema dict 列表）
    tools: list[dict]
    # 意图分组标签（"all" / "task" / "multi:task+im"，供审计记录）
    intent_group: str
    # 工具执行记录（供审计/持久化/_full 回传，与 legacy 的 tool_calls_record 对齐）
    tool_records: Annotated[list[dict], operator.add]
    # LLM 调用轮次（防死循环，对齐 legacy max_iterations 语义）
    iteration: int
    # 实际使用的模型名（"provider:model"，对齐 legacy llm.model_name）
    model_used: str
