"""通知中心模块 — 数据模型"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.base import BaseModel, get_beijing_time
import enum


class NotificationType(str, enum.Enum):
    TASK = "task"
    APPROVAL = "approval"
    CHAT = "chat"
    CALENDAR = "calendar"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"


class Notification(BaseModel):
    """通知表"""
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="接收人ID")
    type = Column(Enum(NotificationType), nullable=False, comment="通知类型")
    title = Column(String(255), nullable=False, comment="通知标题")
    content = Column(Text, nullable=True, comment="通知内容")
    related_type = Column(String(50), nullable=True, comment="关联对象类型")
    related_id = Column(Integer, nullable=True, comment="关联对象ID")
    is_read = Column(Boolean, default=False, comment="是否已读")
    read_at = Column(DateTime, nullable=True, comment="阅读时间")

    user = relationship("User", foreign_keys=[user_id], backref="notifications")


class NotificationSetting(BaseModel):
    """通知偏好设置 — 每种通知类型的开关"""
    __tablename__ = "notification_settings"
    __table_args__ = {'extend_existing': True}

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    notification_type = Column(String(50), nullable=False, comment="通知类型")
    in_app = Column(Boolean, default=True, comment="站内通知")
    push = Column(Boolean, default=False, comment="Push推送")
    email = Column(Boolean, default=False, comment="邮件通知")

    user = relationship("User", foreign_keys=[user_id], backref="notification_settings")
