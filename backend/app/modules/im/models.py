"""即时通讯模块 — 数据模型"""
from sqlalchemy import Column, String, Text, Integer, Integer, ForeignKey, Enum, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy import PrimaryKeyConstraint
import enum
from app.db.base import Base, BaseModel, get_beijing_time


class ConversationType(str, enum.Enum):
    SINGLE = "single"
    GROUP = "group"
    CHANNEL = "channel"


class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    SYSTEM = "system"
    NOTICE = "notice"


class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Conversation(BaseModel):
    """会话表"""
    __tablename__ = "conversations"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, comment="所属空间")
    type = Column(Enum(ConversationType), nullable=False, comment="会话类型: single/group/channel")
    name = Column(String(100), nullable=True, comment="会话名称（群聊必填）")
    avatar = Column(String(500), nullable=True, comment="会话头像URL")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    last_message_id = Column(Integer, nullable=True, comment="最后一条消息ID（冗余，加速列表查询）")
    last_message_at = Column(DateTime, nullable=True, comment="最后消息时间")
    is_muted = Column(Boolean, default=False, comment="全员禁言")

    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="conversations")
    creator = relationship("User", foreign_keys=[created_by], backref="created_conversations")
    members = relationship("ConversationMember", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMember(BaseModel):
    """会话成员表"""
    __tablename__ = "conversation_members"
    __table_args__ = (
        Index("idx_conv_user", "conversation_id", "user_id"),
        {'extend_existing': True}
    )

    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="会话ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    role = Column(Enum(MemberRole), default=MemberRole.MEMBER, nullable=False, comment="群内角色")
    nickname = Column(String(50), nullable=True, comment="群内昵称")
    is_muted = Column(Boolean, default=False, comment="个人是否静音")
    unread_count = Column(Integer, default=0, comment="未读消息数")
    last_read_at = Column(DateTime, nullable=True, comment="最后已读时间")
    joined_at = Column(DateTime, default=get_beijing_time, comment="加入时间")

    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], backref="conversation_memberships")


class Message(BaseModel):
    """消息表"""
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_conv_created", "conversation_id", "created_at"),
        Index("idx_sender", "sender_id", "created_at"),
        {'extend_existing': True}
    )

    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="会话ID")
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="发送者ID")
    msg_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False, comment="消息类型")
    content = Column(Text, nullable=False, comment="消息内容（文本或JSON元数据）")
    reply_to_id = Column(Integer, ForeignKey("messages.id"), nullable=True, comment="引用回复的消息ID")
    is_recalled = Column(Boolean, default=False, comment="是否已撤回")
    recalled_at = Column(DateTime, nullable=True, comment="撤回时间")

    conversation = relationship("Conversation", back_populates="messages", foreign_keys=[conversation_id])
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    reply_to = relationship("Message", remote_side="Message.id", backref="replies")


class MessageRead(Base):
    """消息已读表 — 记录谁读了哪条消息（复合主键，不继承BaseModel）"""
    __tablename__ = "message_reads"
    __table_args__ = {'extend_existing': True}

    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True, nullable=False, comment="消息ID")
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False, comment="用户ID")
    read_at = Column(DateTime, default=get_beijing_time, comment="阅读时间")

    message = relationship("Message", foreign_keys=[message_id])
    user = relationship("User", foreign_keys=[user_id])
