"""企业公告模块 — 数据模型"""
from sqlalchemy import Column, String, Text, Integer, Integer, ForeignKey, Enum, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class AnnouncementType(str, enum.Enum):
    NOTICE = "notice"
    NEWS = "news"
    POLICY = "policy"
    URGENT = "urgent"


class Announcement(BaseModel):
    """公告表"""
    __tablename__ = "announcements"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, comment="富文本内容")
    type = Column(Enum(AnnouncementType), default=AnnouncementType.NOTICE)
    is_pinned = Column(Boolean, default=False, comment="置顶")
    is_must_read = Column(Boolean, default=False, comment="必读")
    publish_at = Column(DateTime, nullable=True, comment="定时发布时间")
    expire_at = Column(DateTime, nullable=True, comment="过期时间")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    creator = relationship("User", foreign_keys=[created_by])


class AnnouncementRead(BaseModel):
    """公告已读记录 — 复合唯一约束防重复"""
    __tablename__ = "announcement_reads"
    __table_args__ = (
        UniqueConstraint('announcement_id', 'user_id', name='uq_announcement_read'),
        {'extend_existing': True},
    )

    announcement_id = Column(Integer, ForeignKey("announcements.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime, nullable=True)

    announcement = relationship("Announcement", foreign_keys=[announcement_id])
    user = relationship("User", foreign_keys=[user_id])
