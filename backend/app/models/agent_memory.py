"""Agent 长期记忆存储模型

配合 LangGraph Store（MySQLStore）使用：
- Redis 短期记忆：最近 N 轮对话，24h TTL
- MySQL agent_memory_item：跨会话长期记忆（用户偏好/身份/明确要求记住的事），永久留存

namespace 示例：("user_memory", "12")  → 存为字符串 "user_memory/12"
"""
from sqlalchemy import Column, String, Text, Integer, UniqueConstraint, Index

from app.db.base import BaseModel


class AgentMemoryItem(BaseModel):
    """一条长期记忆条目（LangGraph Store 的持久化载体）"""
    __tablename__ = "agent_memory_item"

    namespace = Column(String(255), nullable=False, index=True, comment="LangGraph 命名空间（/ 分隔）")
    key = Column(String(128), nullable=False, comment="条目 key（uuid）")
    value = Column(Text, nullable=False, comment="条目 JSON（text/kind/workspace_id/source）")
    text = Column(Text, nullable=True, comment="用于检索的扁平文本")
    embedding = Column(Text, nullable=True, comment="向量 JSON，embedding 不可用时为空")
    workspace_id = Column(Integer, nullable=True, comment="产生该记忆的工作空间（0=个人空间）")

    __table_args__ = (
        UniqueConstraint("namespace", "key", name="uq_agent_memory_ns_key"),
        Index("ix_agent_memory_ns_updated", "namespace", "updated_at"),
    )
