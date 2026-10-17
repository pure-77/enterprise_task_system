"""Agent 操作审计日志模型

记录每次 Agent 对话的完整调用链，用于：
- 企业合规审计（谁在什么时候让 Agent 做了什么）
- 问题排查（Agent 执行异常时回溯）
- 行为分析（工具使用频率、意图分布）
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, func, Index
from app.db.base import BaseModel


class AgentAuditLog(BaseModel):
    """Agent 操作审计日志"""
    __tablename__ = "agent_audit_log"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="操作用户 ID")
    workspace_id = Column(Integer, nullable=False, default=0, index=True, comment="操作空间 ID（0=个人模式）")
    session_id = Column(String(64), nullable=True, index=True, comment="会话 ID")

    # 用户输入
    user_message = Column(Text, nullable=False, comment="用户输入的原始文本")

    # 工具调用链路
    tool_calls = Column(JSON, nullable=True, comment="本次对话所有工具调用记录 JSON")
    tool_call_count = Column(Integer, nullable=False, default=0, comment="工具调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")

    # Agent 输出
    reply = Column(Text, nullable=True, comment="Agent 最终自然语言回复")

    # 模型信息
    model_used = Column(String(32), nullable=True, comment="实际使用的模型名称")
    intent_group = Column(String(32), nullable=True, comment="意图路由到的模块分组")

    # 性能指标
    duration_ms = Column(Integer, nullable=True, comment="本次对话总耗时（毫秒）")

    # 索引优化高频查询
    __table_args__ = (
        Index("ix_agent_audit_ws_user", "workspace_id", "user_id"),
    )
