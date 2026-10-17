"""Agent 会话持久化模型

Redis vs MySQL 分工：
- Redis: 短期对话上下文（24h TTL），Agent.chat() 推理时加载 → 快
- MySQL: 持久化会话列表 + 完整消息历史 → 永久留存、跨设备同步

为什么用 MySQL 而不是前端 localStorage？
- localStorage 限制 ~5MB；MySQL 无限制
- localStorage 换设备/清缓存就丢；MySQL 永久留存
- localStorage 数据在前端不安全；MySQL 在服务端可控可审计
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import BaseModel


class AgentSession(BaseModel):
    """Agent 会话 — 每条记录代表一个独立对话"""
    __tablename__ = "agent_session"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(Integer, nullable=False, default=0, index=True, comment="所属工作空间（0=个人模式）")

    # 会话标识
    session_key = Column(String(64), unique=True, nullable=False, index=True, comment="会话唯一标识（前端传的 session_id）")

    # 元数据
    title = Column(String(200), nullable=True, comment="会话标题（自动取第一条用户消息前 20 字）")
    model_used = Column(String(32), nullable=True, comment="最后一次用的模型")
    message_count = Column(Integer, nullable=False, default=0, comment="消息总数（user+assistant）")

    # 关系
    messages = relationship("AgentMessage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agent_session_user_ws", "user_id", "workspace_id"),
    )


class AgentMessage(BaseModel):
    """Agent 会话中的单条消息"""
    __tablename__ = "agent_message"

    session_id = Column(Integer, ForeignKey("agent_session.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(16), nullable=False, comment="user / assistant / system / tool")
    content = Column(Text, nullable=False, comment="消息内容（Markdown 纯文本，前端渲染）")

    # assistant 消息专用
    tool_calls = Column(Text, nullable=True, comment="本次对话执行的工具调用 JSON（null=没调工具）")
    thinking = Column(Text, nullable=True, comment="思考过程 JSON（null=没开启）")

    # user 消息专用
    image_url = Column(String(500), nullable=True, comment="多模态图片 URL（null=无图片）")

    # 排序
    seq = Column(Integer, nullable=False, default=0, comment="在会话内的顺序号（从 0 开始）")

    session = relationship("AgentSession", back_populates="messages")
