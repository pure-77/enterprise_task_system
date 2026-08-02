"""日程日历模块 — 数据模型"""
from sqlalchemy import Column, String, Text, Integer, Integer, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel, get_beijing_time


class EventType(str, enum.Enum):
    NORMAL = "normal"
    MEETING = "meeting"
    REMINDER = "reminder"
    TASK_DEADLINE = "task_deadline"


class AttendeeStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    PENDING = "pending"


class ReminderMethod(str, enum.Enum):
    NOTIFICATION = "notification"
    EMAIL = "email"
    BOTH = "both"


class Event(BaseModel):
    """日程事件"""
    __tablename__ = "events"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, comment="NULL=个人日程")
    title = Column(String(255), nullable=False, comment="事件标题")
    description = Column(Text, nullable=True, comment="描述")
    location = Column(String(255), nullable=True, comment="地点")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, nullable=False, comment="结束时间")
    is_all_day = Column(Boolean, default=False, comment="全天事件")
    color = Column(String(7), nullable=True, comment="#RRGGBB")
    type = Column(Enum(EventType), default=EventType.NORMAL)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, comment="关联任务ID")
    recurrence_rule = Column(String(255), nullable=True, comment="RFC 5545 重复规则")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    creator = relationship("User", foreign_keys=[created_by], backref="created_events")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")
    reminders = relationship("EventReminder", back_populates="event", cascade="all, delete-orphan")


class EventAttendee(BaseModel):
    """事件参与人"""
    __tablename__ = "event_attendees"
    __table_args__ = {'extend_existing': True}

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(AttendeeStatus), default=AttendeeStatus.PENDING)

    event = relationship("Event", back_populates="attendees")
    user = relationship("User", foreign_keys=[user_id])


class EventReminder(BaseModel):
    """事件提醒"""
    __tablename__ = "event_reminders"
    __table_args__ = {'extend_existing': True}

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    remind_at = Column(DateTime, nullable=False, comment="提醒时间")
    method = Column(Enum(ReminderMethod), default=ReminderMethod.NOTIFICATION)
    is_sent = Column(Boolean, default=False)

    event = relationship("Event", back_populates="reminders")
